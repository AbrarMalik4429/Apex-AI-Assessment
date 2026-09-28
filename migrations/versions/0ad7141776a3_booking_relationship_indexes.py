"""booking relationship indexes"""

from alembic import op

revision = "0ad7141776a3"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_bookings_parent", "bookings", ["dependent_on_booking_id"], schema="booking")
    op.create_index(
        "ix_bookings_replacement", "bookings", ["superseded_by_booking_id"], schema="booking"
    )
    op.create_index(
        "ix_patient_session_patient", "patient_session", ["patient_id"], schema="booking"
    )


def downgrade():
    op.drop_index("ix_patient_session_patient", table_name="patient_session", schema="booking")
    op.drop_index("ix_bookings_replacement", table_name="bookings", schema="booking")
    op.drop_index("ix_bookings_parent", table_name="bookings", schema="booking")
