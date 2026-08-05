import os
from google import genai
from dotenv import load_dotenv

load_dotenv()  # reads GEMINI_API_KEY from a local .env file, if present


def _get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Locally: add it to a .env file. "
        "On Streamlit Cloud: add it under App settings -> Secrets."
    )


client = genai.Client(api_key=_get_gemini_api_key())

# Fallback schema for the app's built-in database (used when no custom
# database is connected). Matches what's actually in Supabase (gold schema).
DEFAULT_SCHEMA_DESCRIPTION = """
gold.dim_customers
    customer_key (int, primary key)
    customer_id (int)
    customer_number (varchar)
    first_name (varchar)
    last_name (varchar)
    country (varchar)
    marital_status (varchar)
    gender (varchar)
    birthdate (date)
    create_date (date)

gold.dim_products
    product_key (int, primary key)
    product_id (int)
    product_number (varchar)
    product_name (varchar)
    category_id (varchar)
    category (varchar)
    subcategory (varchar)
    maintenance (varchar)
    cost (numeric)
    product_line (varchar)
    start_date (date)

gold.fact_sales
    order_number (varchar)
    product_key (int, foreign key -> gold.dim_products.product_key)
    customer_key (int, foreign key -> gold.dim_customers.customer_key)
    order_date (date)
    shipping_date (date)
    due_date (date)
    sales_amount (numeric)
    quantity (int)
    price (numeric)
""".strip()

DEFAULT_DIALECT_NOTE = "This is PostgreSQL. Use LIMIT N for row limits."


def build_prompt(schema_description: str, dialect_note: str, question: str) -> str:
    return f"""You are a SQL expert. You have access to a database with this schema:

{schema_description}

{dialect_note}

Rules:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Always use table aliases and fully qualify column names.
- Join tables when the question needs data spread across more than one.
- Only reference tables and columns that actually appear in the schema above —
  never invent table or column names.
- Return ONLY the raw SQL query. No explanation, no markdown, no backticks.

Question: {question}

SQL query:"""


def generate_sql(
    question: str,
    schema_description: str = DEFAULT_SCHEMA_DESCRIPTION,
    dialect_note: str = DEFAULT_DIALECT_NOTE,
) -> str:
    """Takes an English question plus a schema description and returns a SQL query string."""
    prompt = build_prompt(schema_description, dialect_note, question)
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


if __name__ == "__main__":
    test_question = "What were the total sales by country?"
    print(generate_sql(test_question))
