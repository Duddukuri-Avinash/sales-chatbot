import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

load_dotenv()  # reads DATABASE_URL from a local .env file, if present

# Schemas/tables that are internal to the database engine, not user data —
# skip these when auto-detecting the schema so the AI isn't shown noise.
_IGNORED_SCHEMAS = {
    "information_schema", "pg_catalog", "sys", "mysql",
    "performance_schema", "INFORMATION_SCHEMA", "guest",
}

DIALECT_NOTES = {
    "postgresql": "This is PostgreSQL. Use LIMIT N for row limits.",
    "mysql": "This is MySQL. Use LIMIT N for row limits.",
    "mssql": (
        "This is Microsoft SQL Server. Use TOP N instead of LIMIT "
        "(e.g. SELECT TOP 5 * FROM table), placed right after SELECT."
    ),
    "sqlite": "This is SQLite. Use LIMIT N for row limits.",
    "oracle": "This is Oracle. Use FETCH FIRST N ROWS ONLY instead of LIMIT.",
}


def _get_default_database_url() -> str:
    """The app's built-in database (used when no custom database is connected)."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st
        return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    raise RuntimeError(
        "DATABASE_URL is not set. Locally: add it to a .env file. "
        "On Streamlit Cloud: add it under App settings -> Secrets."
    )


def get_default_engine() -> Engine:
    return create_engine(_get_default_database_url())


def create_engine_from_url(connection_url: str) -> Engine:
    """
    Builds an engine from a user-supplied connection string.
    Expected formats (SQLAlchemy-style URIs):
      postgresql://user:password@host:port/dbname
      mysql+pymysql://user:password@host:port/dbname
      mssql+pyodbc://user:password@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server
      sqlite:///path/to/file.db
    """
    connection_url = connection_url.strip()
    engine = create_engine(connection_url, pool_pre_ping=True)
    # Fail fast with a clear error if the connection is actually bad,
    # rather than surfacing a confusing error later on first query.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


def get_dialect_name(engine: Engine) -> str:
    return engine.dialect.name  # e.g. "postgresql", "mysql", "mssql", "sqlite"


def get_dialect_note(engine: Engine) -> str:
    return DIALECT_NOTES.get(
        get_dialect_name(engine),
        "Use standard SQL row-limiting syntax appropriate for this database.",
    )


def introspect_schema(engine: Engine, max_tables: int = 40, max_columns: int = 40) -> str:
    """
    Reads the real table/column structure from a connected database and
    returns a plain-text description suitable for feeding to the AI.
    """
    insp = inspect(engine)
    lines = []
    table_count = 0

    try:
        schema_names = insp.get_schema_names()
    except Exception:
        schema_names = [None]  # some dialects (e.g. sqlite) don't have schemas

    for schema in schema_names:
        if schema in _IGNORED_SCHEMAS:
            continue
        try:
            tables = insp.get_table_names(schema=schema)
        except Exception:
            continue

        for table in tables:
            if table_count >= max_tables:
                lines.append(f"...and more tables not shown (limit {max_tables} reached).")
                return "\n\n".join(lines)

            try:
                columns = insp.get_columns(table, schema=schema)
            except Exception:
                continue

            qualified_name = f"{schema}.{table}" if schema else table
            col_lines = [
                f"    {c['name']} ({c['type']})" for c in columns[:max_columns]
            ]
            lines.append(qualified_name + "\n" + "\n".join(col_lines))
            table_count += 1

    if not lines:
        return "(No user tables were found in this database.)"

    return "\n\n".join(lines)


def run_query(sql_query: str, engine: Engine) -> pd.DataFrame:
    """
    Runs a SQL query safely against the given engine and returns a DataFrame.
    Only SELECT statements are allowed — this blocks anything that could
    modify or delete data.
    """
    cleaned = sql_query.strip().rstrip(";")
    lowered = cleaned.lower()

    if ";" in cleaned:
        raise ValueError("Query blocked: multiple statements are not allowed.")

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT queries (including WITH/CTE queries) are allowed for safety.")

    forbidden_keywords = [
        "insert", "update", "delete", "drop", "alter", "truncate", "exec",
        "execute", "merge", "grant", "revoke", "create", "sp_", "xp_",
    ]
    for word in forbidden_keywords:
        if word in lowered:
            raise ValueError(f"Query blocked: contains forbidden keyword '{word}'.")

    with engine.connect() as conn:
        df = pd.read_sql(text(cleaned), conn)

    return df


if __name__ == "__main__":
    eng = get_default_engine()
    test_df = run_query("SELECT * FROM gold.fact_sales LIMIT 5", eng)
    print(test_df)
