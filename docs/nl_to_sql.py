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

# ---- SCHEMA DESCRIPTION ----
# This tells the AI exactly what tables/columns exist, so it writes correct SQL.
# Column names/types below match what's actually in Supabase (gold schema).
SCHEMA_DESCRIPTION = """
You are a PostgreSQL expert. You have access to these tables:

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

Rules:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Always use table aliases and fully qualify column names.
- Join fact_sales to dim_customers and dim_products when the question needs
  customer or product details.
- This is PostgreSQL, not SQL Server: use LIMIT instead of TOP, and do not
  use SQL Server-only syntax (no square-bracket identifiers, no GETDATE(),
  no TOP N — use LIMIT N instead, typically at the end of the query).
- Return ONLY the raw SQL query. No explanation, no markdown, no backticks.
"""


def generate_sql(question: str) -> str:
    """Takes an English question and returns a SQL query string."""
    prompt = f"{SCHEMA_DESCRIPTION}\n\nQuestion: {question}\n\nSQL query:"
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
