import hashlib
import secrets
from datetime import date, timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.booking_service import BookingService, aware, booking_data
from app.config import Settings
from app.contracts import AssistantResponse, DomainError, MessageRequest, ProviderError
from app.db import make_engine, make_session_factory
from app.groq_client import GroqInterpreter
from app.models import Operation, Patient, PatientSession, utcnow
from app.workflow import Workflow

DEMO_PATIENT_ID = UUID("00000000-0000-0000-0000-000000000001")
bearer = HTTPBearer(auto_error=False)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_app(settings=None, session_factory=None, interpreter=None, clock=utcnow):
    settings = settings or Settings()
    factory = session_factory or make_session_factory(make_engine(settings))
    interpreter = interpreter or GroqInterpreter(settings)
    api = FastAPI(
        title="Patient Booking Backend",
        version="0.1.0",
        description="Groq interprets requests; Python validates and executes confirmed booking actions.",
    )
    api.state.session_factory = factory

    def database():
        with factory() as db:
            yield db

    def patient_session(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(database)
    ):
        if credentials is None:
            raise HTTPException(401, "A patient session token is required.")
        session = db.scalar(
            select(PatientSession).where(
                PatientSession.token_hash == token_hash(credentials.credentials)
            )
        )
        if session is None or aware(session.expires_at) <= clock():
            raise HTTPException(401, "The patient session is invalid or expired.")
        return session

    @api.exception_handler(SQLAlchemyError)
    async def db_error_handler(request, exc):
        return JSONResponse(
            status_code=503,
            content={
                "code": "database_unavailable",
                "message": "The database could not be reached. Please try again.",
            },
        )

    @api.exception_handler(DomainError)
    async def domain_error_handler(request, exc):
        return JSONResponse(status_code=400, content={"code": exc.code, "message": exc.message})

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/ready")
    def ready(db=Depends(database)):
        db.execute(text("SELECT 1"))
        return {
            "database": "reachable",
            "groq_configured": bool(settings.groq_api_key.get_secret_value()),
        }

    @api.post("/demo/session", status_code=201)
    def demo_session(db=Depends(database)):
        if not settings.demo_enabled:
            raise HTTPException(404, "Not found")
        if db.get(Patient, DEMO_PATIENT_ID) is None:
            raise HTTPException(503, "Load the synthetic demo seed first.")
        token = secrets.token_urlsafe(32)
        session = PatientSession(
            patient_id=DEMO_PATIENT_ID,
            token_hash=token_hash(token),
            expires_at=clock() + timedelta(hours=settings.session_hours),
            state={},
        )
        db.add(session)
        db.commit()
        return {"access_token": token, "token_type": "bearer", "expires_at": session.expires_at}

    @api.get("/doctors")
    def doctors(
        query: str | None = Query(default=None, max_length=120),
        specialty: str | None = Query(default=None, max_length=100),
        session=Depends(patient_session),
        db=Depends(database),
    ):
        service = BookingService(db, settings, session.patient_id, clock())
        return {
            "doctors": [
                {
                    "doctor_id": str(d.doctor_id),
                    "doctor_name": d.doctor_name,
                    "specialties": [s for s in [d.specialty_1, d.specialty_2, d.specialty_3] if s],
                }
                for d in service.doctors(query, specialty)
            ]
        }

    @api.get("/availability")
    def availability(
        doctor_id: UUID,
        start: date | None = None,
        end: date | None = None,
        exclude_booking_id: UUID | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        session=Depends(patient_session),
        db=Depends(database),
    ):
        service = BookingService(db, settings, session.patient_id, clock())
        return {
            "timezone": settings.clinic_timezone,
            "slots": [
                c.model_dump(mode="json")
                for c in service.availability(doctor_id, start, end, exclude_booking_id, limit)
            ],
        }

    @api.get("/appointments")
    def appointments(session=Depends(patient_session), db=Depends(database)):
        return {
            "appointments": [
                booking_data(b)
                for b in BookingService(db, settings, session.patient_id, clock()).appointments()
            ]
        }

    @api.get("/appointments/{booking_id}")
    def appointment(booking_id: UUID, session=Depends(patient_session), db=Depends(database)):
        return booking_data(
            BookingService(db, settings, session.patient_id, clock()).lookup(booking_id)
        )

    @api.post("/assistant/message", response_model=AssistantResponse)
    def message(body: MessageRequest, session=Depends(patient_session), db=Depends(database)):
        fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        previous = db.get(Operation, (session.session_id, body.request_id))
        if previous:
            if previous.request_hash != fingerprint:
                raise HTTPException(409, "This request_id was already used with different input.")
            return AssistantResponse.model_validate(previous.response)
        try:
            service = BookingService(db, settings, session.patient_id, clock())
            result = Workflow(service, session, interpreter).handle(body)
            db.add(
                Operation(
                    session_id=session.session_id,
                    request_id=body.request_id,
                    request_hash=fingerprint,
                    response=result.model_dump(mode="json"),
                )
            )
            db.commit()
            return result
        except ProviderError as exc:
            db.rollback()
            result = AssistantResponse(
                request_id=body.request_id,
                status="error",
                message="I could not interpret your request right now. No appointment action was taken. Please try again.",
                data={"code": exc.code},
            )
            headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
            return JSONResponse(
                status_code=503, content=result.model_dump(mode="json"), headers=headers
            )
        except SQLAlchemyError:
            db.rollback()
            # A commit failure can mean its acknowledgement was lost. Never claim failure/success.
            result = AssistantResponse(
                request_id=body.request_id,
                status="outcome_unknown",
                message="The request outcome could not be verified. Retry the identical request with the same request_id before starting another change.",
                data={"code": "database_outcome_unknown"},
            )
            return JSONResponse(status_code=503, content=result.model_dump(mode="json"))

    return api


app = create_app()
