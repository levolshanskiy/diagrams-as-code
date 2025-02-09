import logging
from logging.config import fileConfig
from typing import Optional

from flask import current_app
from alembic import context
from sqlalchemy.engine import Engine

# Get Alembic configuration
config = context.config

# Configure logging if a config file is specified
if config.config_file_name:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")


def get_engine() -> Optional[Engine]:
    """Returns the database engine."""
    try:
        migrate_ext = current_app.extensions.get("migrate")
        if not migrate_ext or not hasattr(migrate_ext, "db"):
            logger.error("Flask-Migrate extension not found.")
            return None
        return migrate_ext.db.get_engine()
    except (AttributeError, KeyError, TypeError) as e:
        logger.error(f"Error retrieving the database engine: {e}")
        return None


def get_engine_url() -> str:
    """Returns the database URL."""
    engine = get_engine()
    if not engine:
        raise RuntimeError("Failed to retrieve the database engine.")

    try:
        return engine.url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(engine.url).replace("%", "%%")


# Set the database URL for Alembic
config.set_main_option("sqlalchemy.url", get_engine_url())

# Retrieve the database object
target_db = current_app.extensions["migrate"].db


def get_metadata():
    """Returns the database metadata for autogeneration."""
    return getattr(target_db, "metadatas", {}).get(None, target_db.metadata)


def run_migrations_offline():
    """Runs migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("Database URL is not set.")

    context.configure(url=url, target_metadata=get_metadata(), literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Runs migrations in online mode."""

    def process_revision_directives(context, revision, directives):
        """Prevents empty migrations from being generated."""
        cmd_opts = getattr(config, "cmd_opts", None)
        if cmd_opts and getattr(cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No schema changes detected. Migration not created.")

    # Retrieve Alembic configuration arguments
    conf_args = getattr(current_app.extensions["migrate"], "configure_args", {})
    conf_args.setdefault("process_revision_directives", process_revision_directives)

    # Get the database engine
    connectable = get_engine()
    if not connectable:
        raise RuntimeError("Failed to connect to the database.")

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=get_metadata(), **conf_args)

        with context.begin_transaction():
            context.run_migrations()


# Determine the migration mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
