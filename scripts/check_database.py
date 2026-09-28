"""Read-only database check. Prints no credentials or patient data."""

import json

from sqlalchemy import text

from app.config import Settings
from app.db import make_engine


def main():
    engine = make_engine(Settings())
    try:
        with engine.connect() as connection:
            row = (
                connection.execute(
                    text("""
                SELECT current_user AS role,
                    (SELECT count(*) FROM booking.doctor) AS doctors,
                    (SELECT count(*) FROM booking.slot) AS weekly_slots,
                    has_table_privilege(current_user, 'booking.slot', 'INSERT') AS can_insert_slots,
                    has_table_privilege(current_user, 'booking.bookings', 'DELETE') AS can_delete_bookings,
                    (SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user) AS bypasses_rls
            """)
                )
                .mappings()
                .one()
            )
            print(json.dumps(dict(row), indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
