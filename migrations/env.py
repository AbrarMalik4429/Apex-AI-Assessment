from alembic import context

from app.config import Settings
from app.db import make_engine
from app.models import Base

if context.is_offline_mode():
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=Base.metadata,
        literal_binds=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(Settings())
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, include_schemas=True
        )
        with context.begin_transaction():
            context.run_migrations()
