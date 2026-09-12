from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply tiny compatibility fixes for pre-migration prototype databases.

    ContextIQ will move to versioned migrations before production. This helper
    only protects existing hackathon/dev databases created by older prototypes.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "emails" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("emails")}

    if "gmail_message_id" not in columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE emails ADD COLUMN gmail_message_id VARCHAR(255)"
            )

    if "gmail_thread_id" not in columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE emails ADD COLUMN gmail_thread_id VARCHAR(255)"
            )
