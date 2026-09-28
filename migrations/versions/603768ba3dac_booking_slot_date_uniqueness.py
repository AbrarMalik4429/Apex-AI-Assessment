"""Persist slot identity and prevent duplicate confirmed slot/date bookings."""

from alembic import op

revision = "603768ba3dac"
down_revision = "0ad7141776a3"
branch_labels = None
depends_on = None

# Scalar backfill deliberately fails on ambiguous matches; the check rejects missing
# matches. Never guess a slot or discard existing appointments during migration.
UPGRADE_SQL = (
    "ALTER TABLE booking.bookings ADD COLUMN slot_id UUID REFERENCES booking.slot(slot_id)",
    """UPDATE booking.bookings b SET slot_id = (
        SELECT s.slot_id FROM booking.slot s
        WHERE s.doctor_id = b.doctor_id AND s.day_of_week = b.booked_day_of_week
          AND s.start_time = b.booked_start_time AND s.end_time = b.booked_end_time
    ) WHERE b.appointment_date IS NOT NULL""",
    """ALTER TABLE booking.bookings ADD CONSTRAINT booking_slot_time CHECK (
        (slot_id IS NULL AND appointment_date IS NULL) OR
        (slot_id IS NOT NULL AND appointment_date IS NOT NULL))""",
    "CREATE INDEX ix_bookings_slot ON booking.bookings(slot_id)",
    """CREATE UNIQUE INDEX uq_bookings_confirmed_slot_date
        ON booking.bookings(slot_id, appointment_date) WHERE status = 'confirmed'""",
)


def upgrade():
    for statement in UPGRADE_SQL:
        op.execute(statement)


def downgrade():
    op.execute("DROP INDEX booking.uq_bookings_confirmed_slot_date")
    op.execute("DROP INDEX booking.ix_bookings_slot")
    op.execute("ALTER TABLE booking.bookings DROP CONSTRAINT booking_slot_time")
    op.execute("ALTER TABLE booking.bookings DROP COLUMN slot_id")
