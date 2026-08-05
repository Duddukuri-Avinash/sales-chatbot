import pandas as pd
import streamlit as st

from db import run_query
from nl_to_sql import generate_sql

st.set_page_config(page_title="Sales NL-to-SQL Chatbot", page_icon="📊", layout="wide")

st.title("📊 Sales NL-to-SQL Chatbot")
st.caption(
    "Ask questions about the sales data warehouse in plain English. "
    "Your question is turned into SQL by Gemini, run against a Postgres "
    "database (Supabase), and returned as a table + chart."
)

SAMPLE_QUESTIONS = [
    "What were the total sales by country?",
    "Who are the top 5 customers by total sales amount?",
    "What are the top 5 best-selling products by quantity?",
    "What is the monthly sales trend for the last year?",
    "What is the average order value by product category?",
]

# ---- SIDEBAR ----
with st.sidebar:
    st.header("Try a sample question")
    for q in SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            st.session_state["pending_question"] = q

    st.divider()
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state["history"] = []
        st.rerun()

    st.divider()
    st.caption(
        "**About this project**\n\n"
        "This chatbot translates natural-language questions into SQL "
        "queries against a Sales Data Warehouse (bronze/silver/gold "
        "architecture), using Google's Gemini API. Only SELECT queries "
        "are permitted — a safety guardrail blocks any query that could "
        "modify or delete data."
    )

# ---- SESSION STATE ----
if "history" not in st.session_state:
    st.session_state["history"] = []


def is_probably_categorical(series: pd.Series) -> bool:
    return series.dtype == object or pd.api.types.is_bool_dtype(series)


def is_probably_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def is_probably_datelike(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    name = str(series.name).lower()
    return any(token in name for token in ["date", "month", "year", "day"])


def render_chart(df: pd.DataFrame):
    """Best-effort auto chart: only draws one if the shape clearly suggests it."""
    if df.empty or len(df.columns) < 2:
        return

    numeric_cols = [c for c in df.columns if is_probably_numeric(df[c])]
    date_cols = [c for c in df.columns if is_probably_datelike(df[c])]
    categorical_cols = [
        c for c in df.columns if is_probably_categorical(df[c]) and c not in date_cols
    ]

    if not numeric_cols:
        return  # nothing measurable to plot

    value_col = numeric_cols[0]

    if date_cols:
        x_col = date_cols[0]
        chart_df = df[[x_col, value_col]].set_index(x_col)
        st.line_chart(chart_df)
    elif categorical_cols and df.shape[0] <= 30:
        x_col = categorical_cols[0]
        chart_df = df[[x_col, value_col]].set_index(x_col)
        st.bar_chart(chart_df)
    # otherwise: skip charting silently, table is enough


def handle_question(question: str):
    entry = {"question": question, "sql": None, "df": None, "error": None}
    try:
        sql = generate_sql(question)
        entry["sql"] = sql
        df = run_query(sql)
        entry["df"] = df
    except Exception as e:
        entry["error"] = str(e)
    st.session_state["history"].append(entry)


# ---- RENDER CHAT HISTORY ----
for entry in st.session_state["history"]:
    with st.chat_message("user"):
        st.write(entry["question"])

    with st.chat_message("assistant"):
        if entry["error"]:
            st.error(f"Something went wrong: {entry['error']}")
        else:
            df = entry["df"]
            if df is None or df.empty:
                st.info("The query ran successfully but returned no rows.")
            else:
                st.dataframe(df, use_container_width=True)
                render_chart(df)

        if entry["sql"]:
            with st.expander("View generated SQL"):
                st.code(entry["sql"], language="sql")

# ---- HANDLE SAMPLE QUESTION CLICK ----
if "pending_question" in st.session_state:
    q = st.session_state.pop("pending_question")
    handle_question(q)
    st.rerun()

# ---- CHAT INPUT ----
user_question = st.chat_input("Ask a question about the sales data...")
if user_question:
    handle_question(user_question)
    st.rerun()
