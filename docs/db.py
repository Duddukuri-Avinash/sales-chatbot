import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()  # reads DATABASE_URL from a local .env file, if present


def _get_database_url() -> str:
    """
    Works both locally (.env file) and on Streamlit Community Cloud
    (secrets set in the app dashboard, available via st.secrets).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Fall back to Streamlit secrets when running on Streamlit Cloud
    try:
        import streamlit as st
        return st.secrets["DATABASE_URL"]
    except Exception:
        pass

    raise RuntimeError(
        "DATABASE_URL is not set. Locally: add it to a .env file. "
        "On Streamlit Cloud: add it under App settings -> Secrets."
    )


DATABASE_URL = _get_database_url()

# SQLAlchemy + psycopg2 driver for Postgres
engine = create_engine(DATABASE_URL)


def run_query(sql_query: str) -> pd.DataFrame:
    """
    Runs a SQL query safely and returns the results as a pandas DataFrame.
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
    test_df = run_query("SELECT * FROM gold.fact_sales LIMIT 5")
    print(test_df)
