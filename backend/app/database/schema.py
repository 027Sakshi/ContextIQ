from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def _columns(engine: Engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def ensure_schema_compatibility(engine: Engine) -> None:
    """Small compatibility bridge for hackathon/dev databases."""
    tables = set(inspect(engine).get_table_names())

    if "emails" in tables:
        columns = _columns(engine, "emails")
        additions = {
            "gmail_message_id": "VARCHAR(255)",
            "gmail_thread_id": "VARCHAR(255)",
        }
        for name, sql_type in additions.items():
            if name not in columns:
                with engine.begin() as connection:
                    connection.exec_driver_sql(f"ALTER TABLE emails ADD COLUMN {name} {sql_type}")

    if "calendar_events" in tables:
        columns = _columns(engine, "calendar_events")
        additions = {
            "external_event_id": "VARCHAR(255)",
            "external_html_link": "VARCHAR(1000)",
        }
        for name, sql_type in additions.items():
            if name not in columns:
                with engine.begin() as connection:
                    connection.exec_driver_sql(f"ALTER TABLE calendar_events ADD COLUMN {name} {sql_type}")
