"""Initial private booking schema. SQL is a frozen snapshot, not live ORM metadata."""

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).with_name("0001_initial.sql").read_text(encoding="utf-8")
    # This migration contains only plain DDL, with no semicolons inside literals/functions.
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for table in [
        "operation",
        "patient_session",
        "bookings",
        "doctor_leave",
        "slot",
        "doctor",
        "patient",
    ]:
        op.execute(f'DROP TABLE booking."{table}"')
    op.execute("DROP SCHEMA booking")
