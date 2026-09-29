import random
import re
import secrets
from datetime import date, datetime, time, timedelta
from uuid import UUID

from app.booking_service import BookingService, booking_data
from app.contracts import AssistantResponse, Candidate, DomainError, Interpretation, MessageRequest
from app.date_windows import add_months, default_window_end
from app.groq_client import Interpreter
from app.models import PatientSession

CONFIRM_WORDS = {"yes", "confirm", "yes confirm", "Ù†Ø¹Ù…", "ØªØ£ÙƒÙŠØ¯"}


class Workflow:
    def __init__(self, service: BookingService, session: PatientSession, interpreter: Interpreter):
        self.service, self.session, self.interpreter = service, session, interpreter

    def response(
        self,
        request: MessageRequest,
        status: str,
        message: str,
        data: dict | None = None,
        token: str | None = None,
    ) -> AssistantResponse:
        return AssistantResponse(
            request_id=request.request_id,
            status=status,
            message=message,
            data=data or {},
            confirmation_token=token,
        )

    def handle(
        self, request: MessageRequest, structured: Interpretation | None = None
    ) -> AssistantResponse:
        try:
            return self._handle(request, structured)
        except DomainError as exc:
            self.session.state = {}
            return self.response(request, exc.status, exc.message, {"code": exc.code})
        except (ValueError, TypeError):
            self.session.state = {}
            return self.response(
                request,
                "clarification",
                "Please provide a valid appointment ID, date (YYYY-MM-DD), or time (HH:MM).",
                {"code": "invalid_interpretation"},
            )

    def _handle(
        self, request: MessageRequest, structured: Interpretation | None = None
    ) -> AssistantResponse:
        text = request.message.strip().casefold().rstrip(".!ØŸ")
        if text in {"reset", "start over", "stop", "never mind"}:
            self.session.state = {}
            return self.response(
                request,
                "clarification",
                "The current request was cleared. What would you like to do?",
            )
        state = {} if structured is not None else dict(self.session.state or {})
        if request.confirmation_token is not None:
            return self.confirm(request, state, text)
        if text in CONFIRM_WORDS:
            return self.response(
                request,
                "clarification",
                "Please confirm using the confirmation token from the proposed appointment change. No change was made.",
            )

        # Only operational state and public scheduling details go to the model.
        # Never send session tokens, patient records, phone numbers or notes.
        context = {
            "clinic_now": self.service.now.astimezone(self.service.zone).isoformat(),
            "timezone": self.service.settings.clinic_timezone,
            "current_action": state.get("action"),
            "stage": state.get("stage"),
            "doctor_query": state.get("doctor_query"),
            "appointment_date": state.get("appointment_date"),
            "date_from": state.get("date_from"),
            "date_to": state.get("date_to"),
            "options": [
                {
                    k: v
                    for k, v in o.items()
                    if k
                    in {
                        "doctor_name",
                        "appointment_date",
                        "start_time",
                        "end_time",
                        "type",
                        "status",
                    }
                }
                for o in state.get("options", [])
            ],
        }
        # Exact numbered replies refer to server-stored options. Resolve these
        # deterministically so the model cannot copy option fields and invalidate
        # the selection, and avoid a needless provider call for button clicks.
        numbered = re.fullmatch(r"(?:book\s+)?(?:option\s+)?(\d+)", text)
        if structured is None and numbered and state.get("options"):
            fields = {field: None for field in Interpretation.model_fields}
            fields.update(intent="continue", option_number=int(numbered.group(1)))
            parsed = Interpretation(**fields)
        else:
            parsed = (
                structured
                if structured is not None
                else self.interpreter.interpret(request.message, context)
            )
        today = self.service.now.astimezone(self.service.zone).date()
        if parsed.months_after is not None:
            start = add_months(today, parsed.months_after)
            parsed = parsed.model_copy(
                update={
                    "appointment_date": None,
                    "date_from": start.isoformat(),
                    "date_to": default_window_end(
                        start, today, self.service.settings.booking_horizon_days
                    ).isoformat(),
                }
            )
        if parsed.intent == "unknown":
            self.session.state = {}
            return self.response(
                request,
                "clarification",
                "I can help with availability, bookings, rescheduling, cancellation, appointment lookup, and existing follow-ups. Which do you need?",
            )
        if parsed.intent == "appointments":
            self.session.state = {}
            bookings = (
                [self.service.lookup(UUID(parsed.booking_id))]
                if parsed.booking_id
                else self.service.appointments()
            )
            return self.response(
                request,
                "success",
                "Here are your appointments.",
                {"appointments": [booking_data(b) for b in bookings]},
            )

        action = state.get("action") if parsed.intent == "continue" else parsed.intent
        if action not in {"book", "availability", "reschedule", "cancel", "follow_up"}:
            return self.response(
                request,
                "clarification",
                "Would you like to book, check availability, reschedule, cancel, or schedule a follow-up?",
            )
        # Choosing an availability result starts booking without losing its options.
        if (
            state.get("action") == "availability"
            and action == "book"
            and state.get("stage") == "slot"
            and parsed.option_number is not None
        ):
            state["action"] = "book"
        if state.get("action") != action:
            state = {}
        # A fresh message invalidates any previous confirmation even if fields stay the same.
        state.pop("proposal", None)
        state.pop("confirmation_token", None)
        state.pop("expires_at", None)
        state["action"] = action
        # A new date criterion replaces the previous exact date or range.
        if parsed.appointment_date is not None:
            state.pop("date_from", None)
            state.pop("date_to", None)
        elif parsed.date_from is not None or parsed.date_to is not None:
            state.pop("appointment_date", None)
            state.pop("date_from", None)
            state.pop("date_to", None)
            if parsed.start_time is None:
                state.pop("start_time", None)
        changed_selection = False
        for field in (
            "doctor_query",
            "specialty",
            "appointment_date",
            "date_from",
            "date_to",
            "start_time",
            "booking_id",
            "appointment_type",
            "time_preference",
        ):
            value = getattr(parsed, field)
            if value is not None:
                if isinstance(value, str) and (not value.strip() or len(value) > 120):
                    raise ValueError("invalid field length")
                if state.get(field) != value:
                    changed_selection = True
                state[field] = value
        if parsed.doctor_query is not None or parsed.specialty is not None:
            state.pop("doctor_id", None)
        if parsed.doctor_query is not None and parsed.specialty is None:
            state.pop("specialty", None)
        if parsed.specialty is not None and parsed.doctor_query is None:
            state.pop("doctor_query", None)
        if parsed.appointment_date is not None and parsed.start_time is None:
            state.pop("start_time", None)
        if parsed.start_time is not None and parsed.time_preference is None:
            state.pop("time_preference", None)
        if parsed.time_preference is not None and parsed.start_time is None:
            state.pop("start_time", None)

        selected_slot = None
        if parsed.option_number is not None:
            # Do not resolve a stale option against newly changed criteria.
            if changed_selection:
                state.pop("options", None)
            options = state.get("options", [])
            index = parsed.option_number - 1
            if index < 0 or index >= len(options):
                raise DomainError(
                    "invalid_option",
                    "Please choose one of the displayed options, or request new times.",
                    "clarification",
                )
            option = options[index]
            stage = state.get("stage")
            if stage == "doctor":
                state["doctor_id"] = option["doctor_id"]
            elif stage == "appointment":
                state["booking_id"] = option["booking_id"]
            elif stage == "slot":
                selected_slot = Candidate.model_validate(option)
            else:
                raise DomainError(
                    "invalid_option", "Please request appointment options first.", "clarification"
                )
        state.pop("options", None)

        if action in {"reschedule", "cancel", "follow_up"}:
            if not state.get("booking_id"):
                wanted_status = "pending_scheduling" if action == "follow_up" else "confirmed"
                matches = [b for b in self.service.appointments() if b.status == wanted_status]
                if action == "follow_up":
                    matches = [b for b in matches if b.dependent_on_booking_id]
                if not matches:
                    self.session.state = {}
                    return self.response(
                        request, "unavailable", "No matching appointments were found."
                    )
                return self.options(
                    request,
                    state,
                    "appointment",
                    [booking_data(b) for b in matches],
                    "Which appointment do you mean? Choose its option number or provide its booking ID.",
                )
            booking = self.service.lookup(UUID(state["booking_id"]))
            if action == "cancel" and booking.status == "cancelled":
                self.session.state = {}
                return self.response(
                    request,
                    "success",
                    "This appointment is already cancelled.",
                    {"booking": booking_data(booking)},
                )
            if action in {"cancel", "reschedule"}:
                self.service.check_change(booking, action)
            elif booking.status != "pending_scheduling" or not booking.dependent_on_booking_id:
                raise DomainError("invalid_follow_up", "Choose an existing unscheduled follow-up.")
            if action == "cancel":
                return self.propose(
                    request,
                    state,
                    {"action": action, "booking_id": str(booking.booking_id)},
                    "Cancel this appointment?",
                    {"booking": booking_data(booking)},
                )
            state["doctor_id"] = str(booking.doctor_id)
            state["appointment_type"] = booking.type
        if not state.get("doctor_id"):
            doctors = self.service.doctors(state.get("doctor_query"), state.get("specialty"))
            if not doctors:
                self.session.state = {}
                return self.response(
                    request,
                    "clarification",
                    "No matching doctor was found. Please provide a doctor name or specialty.",
                )
            if len(doctors) != 1 or not (state.get("doctor_query") or state.get("specialty")):
                return self.options(
                    request,
                    state,
                    "doctor",
                    [
                        {
                            "doctor_id": str(d.doctor_id),
                            "doctor_name": d.doctor_name,
                            "specialty": d.specialty_1,
                        }
                        for d in doctors
                    ],
                    "Choose a doctor by option number, name, or specialty.",
                )
            state["doctor_id"] = str(doctors[0].doctor_id)

        day = (
            date.fromisoformat(state["appointment_date"]) if state.get("appointment_date") else None
        )
        range_start = date.fromisoformat(state["date_from"]) if state.get("date_from") else None
        range_end = date.fromisoformat(state["date_to"]) if state.get("date_to") else None
        is_range = range_start is not None or range_end is not None
        if is_range:
            range_start = range_start or today
            range_end = range_end or default_window_end(
                range_start, today, self.service.settings.booking_horizon_days
            )
        requested_time = (
            time.fromisoformat(state["start_time"]) if state.get("start_time") else None
        )
        if requested_time and requested_time.tzinfo:
            raise ValueError("use local time")
        exclude = UUID(state["booking_id"]) if action == "reschedule" else None
        if action == "reschedule" and day and requested_time:
            if day == booking.appointment_date and requested_time == booking.booked_start_time:
                raise DomainError(
                    "same_appointment_time",
                    "This is already your appointment time. Please choose a different date or time.",
                    "clarification",
                )
        if selected_slot is None:
            candidates = self.service.availability(
                UUID(state["doctor_id"]),
                range_start if is_range else day,
                range_end if is_range else day,
                exclude,
                limit=None if is_range or requested_time or state.get("time_preference") else 20,
            )
            period = state.get("time_preference")
            if period:
                low, high = {"morning": (0, 12), "afternoon": (12, 17), "evening": (17, 24)}[period]
                candidates = [c for c in candidates if low <= c.start_time.hour < high]
            if requested_time:
                candidates = [c for c in candidates if c.start_time == requested_time]
            if is_range and len(candidates) > 20:
                candidates = random.SystemRandom().sample(candidates, 20)
                candidates.sort(key=lambda c: (c.appointment_date, c.start_time, str(c.slot_id)))
            else:
                candidates = candidates[:20]
            if not candidates:
                self.session.state = state
                return self.response(
                    request,
                    "unavailable",
                    "No available times match that request. Please try another date or doctor.",
                )
            if action == "availability" or not (day and requested_time and len(candidates) == 1):
                return self.options(
                    request,
                    state,
                    "slot",
                    [c.model_dump(mode="json") for c in candidates],
                    (
                        f"Here is a selection of available times from {range_start} to {range_end}. "
                        "These do not overlap your appointments. Choose an option number to continue."
                    )
                    if is_range
                    else "These times are available and do not overlap your appointments. Choose an option number to continue.",
                )
            selected_slot = candidates[0]
        if selected_slot.doctor_id != UUID(state["doctor_id"]):
            raise DomainError(
                "stale_options",
                "Please choose a time for the currently selected doctor.",
                "clarification",
            )
        if action == "availability":
            state["action"] = action = "book"
        if action == "reschedule":
            self.service.check_reschedule_target(booking, selected_slot)
        self.service.revalidate(selected_slot, exclude)
        appointment_type = state.get("appointment_type", "consultation")
        if len(appointment_type) > 100:
            raise ValueError("appointment type too long")
        proposal = {
            "action": action,
            "candidate": selected_slot.model_dump(mode="json"),
            "appointment_type": appointment_type,
            "booking_id": state.get("booking_id"),
        }
        return self.propose(
            request,
            state,
            proposal,
            f"Please confirm {action.replace('_', ' ')} with {selected_slot.doctor_name} on {selected_slot.appointment_date} at {selected_slot.start_time.strftime('%H:%M')} ({self.service.settings.clinic_timezone}).",
            {
                "candidate": selected_slot.model_dump(mode="json"),
                "appointment_type": appointment_type,
            },
        )

    def options(self, request, state, stage, options, message):
        state.update(stage=stage, options=options)
        self.session.state = state
        return self.response(request, "options", message, {"kind": stage, "options": options})

    def propose(self, request, state, proposal, message, data):
        token = secrets.token_urlsafe(24)
        expires = self.service.now + timedelta(minutes=self.service.settings.confirmation_minutes)
        state.update(
            stage="confirmation",
            proposal=proposal,
            confirmation_token=token,
            expires_at=expires.isoformat(),
        )
        self.session.state = state
        return self.response(
            request,
            "confirmation_required",
            message,
            {**data, "action": proposal["action"], "expires_at": expires.isoformat()},
            token,
        )

    def confirm(self, request, state, text):
        if text not in CONFIRM_WORDS:
            raise DomainError(
                "confirmation_text",
                "Send 'confirm' with the current confirmation token, or send your changes without that token.",
                "clarification",
            )
        expected = state.get("confirmation_token", "")
        if not expected or not secrets.compare_digest(expected, request.confirmation_token):
            raise DomainError(
                "invalid_confirmation",
                "That confirmation is no longer valid. Please request the appointment change again.",
                "clarification",
            )
        if datetime.fromisoformat(state["expires_at"]) <= self.service.now:
            raise DomainError(
                "confirmation_expired",
                "The confirmation expired. Please request fresh options.",
                "clarification",
            )
        proposal = state["proposal"]
        action = proposal["action"]
        if action == "cancel":
            booking = self.service.cancel(UUID(proposal["booking_id"]))
            message = "Your appointment has been cancelled."
        else:
            candidate = Candidate.model_validate(proposal["candidate"])
            if action == "book":
                booking = self.service.book(candidate, proposal["appointment_type"])
                message = "Your appointment has been booked."
            elif action == "reschedule":
                booking = self.service.reschedule(UUID(proposal["booking_id"]), candidate)
                message = "Your appointment has been rescheduled."
            elif action == "follow_up":
                booking = self.service.schedule_follow_up(UUID(proposal["booking_id"]), candidate)
                message = "Your follow-up has been scheduled."
            else:
                raise DomainError("invalid_action", "Please start a new booking request.")
        self.session.state = {}
        # Caller commits the booking AND this response before returning success.
        return self.response(request, "success", message, {"booking": booking_data(booking)})
