import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ensure src/ is on the path so app.database and app.models can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

load_dotenv()

import app.models  # noqa: F401 — registers all models against Base.metadata
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")
target_metadata = Base.metadata

# Alembic runs synchronously — use psycopg2 here even though the app uses asyncpg
# Prefer DATABASE_URL if set (Railway injects this automatically for linked Postgres services),
# otherwise fall back to individual DB_* vars for local dev
_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "In Railway, link the Postgres service and set DATABASE_URL=${{Postgres.DATABASE_URL}} "
        "(replace 'Postgres' with the exact name of your Postgres service in Railway)."
    )
# Alembic needs psycopg2 driver — swap scheme if needed
SYNC_DATABASE_URL = (
    _db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    .replace("postgresql://", "postgresql+psycopg2://", 1)
    .replace("postgres://", "postgresql+psycopg2://", 1)
)
print(
    f"[booking-api] Connecting to DB host: {SYNC_DATABASE_URL.split('@')[-1].split('/')[0]}",
    flush=True,
)
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
