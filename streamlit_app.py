import json
import os
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.cloud import bigquery
from google import genai

load_dotenv()

MODEL_API_KEY = os.getenv("MODEL_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
BQ_PROJECT_ID = os.getenv("BQ_PROJECT_ID")
TABLE_NAME = os.getenv("TABLE_NAME")

if not MODEL_API_KEY:
    raise ValueError("Missing MODEL_API_KEY in .env")

if not TABLE_NAME:
    raise ValueError("Missing TABLE_NAME in .env")

client = genai.Client(api_key=MODEL_API_KEY)
bq_client = bigquery.Client(project=BQ_PROJECT_ID)

def fix_sql(user_question: str, schema: str, failed_sql: str, error_message: str) -> str:
    prompt = f"""
You are an expert data analyst fixing BigQuery SQL.

The user question was:
{user_question}

The available schema is:
{schema}

The previous SQL failed:
{failed_sql}

BigQuery returned this error:
{error_message}

Instructions:
1. Fix the SQL based on the error.
2. Return ONLY valid BigQuery SQL.
3. Do NOT include markdown fences.
4. Do NOT explain anything.
5. Use ONLY the table and columns in the provided schema.
6. Always fully qualify the table name as `{TABLE_NAME}`.
7. Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or MERGE.

Return the corrected SQL only.
""".strip()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return clean_sql(response.text)

def clean_sql(sql: str) -> str:
    return sql.replace("```sql", "").replace("```", "").strip()


def get_table_schema(table_name: str) -> str:
    table = bq_client.get_table(table_name)
    lines = [f"Table: {table_name}", "", "Columns:"]
    for field in table.schema:
        lines.append(f"- {field.name} ({field.field_type})")
    return "\n".join(lines)

def fix_sql(user_question: str, schema: str, failed_sql: str, error_message: str) -> str:
    prompt = f"""
You are an expert data analyst fixing BigQuery SQL.

The user question was:
{user_question}

The available schema is:
{schema}

The previous SQL failed:
{failed_sql}

BigQuery returned this error:
{error_message}

Instructions:
1. Fix the SQL based on the error.
2. Return ONLY valid BigQuery SQL.
3. Do NOT include markdown fences.
4. Do NOT explain anything.
5. Use ONLY the table and columns in the provided schema.
6. Always fully qualify the table name as `{TABLE_NAME}`.
7. Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or MERGE.

Return the corrected SQL only.
""".strip()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return clean_sql(response.text)

def should_retry_bq_error(error_message: str) -> bool:
    msg = error_message.lower()

    non_retryable_patterns = [
        "access denied",
        "permission",
        "not authorized",
        "quota exceeded",
        "billing",
        "credentials",
        "authentication",
        "not found: dataset",
    ]

    for pattern in non_retryable_patterns:
        if pattern in msg:
            return False

    return True

def generate_sql(user_question: str, schema: str) -> str:
    prompt = f"""
You are an expert data analyst writing BigQuery SQL.

Use ONLY the table and columns provided below.

{schema}

Rules:
1. Return ONLY valid BigQuery SQL.
2. Do NOT include markdown fences.
3. Do NOT explain anything.
4. Use ONLY the columns listed above.
5. Always fully qualify the table name as `{TABLE_NAME}`. Make sure you include "`" for the table name.
6. Limit results to 100 rows unless the question asks for a single aggregate.
7. If the question is ambiguous, make the most reasonable assumption.
8. If the question mentions age group, create age buckets using CASE.
9. If the question defines a metric like engagement score, calculate it explicitly.
10. If the question asks for top N, use ROW_NUMBER() or RANK() and filter correctly.
11. If churned is boolean or categorical, convert it safely using CASE instead of direct CAST.

User question:
{user_question}
""".strip()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return clean_sql(response.text)

def execute_with_retries(user_question: str, schema: str, max_attempts: int = 4):
    sql = generate_sql(user_question, schema)
    attempts_log = []
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            validate_sql(sql)
            results = run_query(sql)
            attempts_log.append({
                "attempt": attempt,
                "sql": sql,
                "status": "success",
                "error": None
            })
            return sql, results, attempts_log

        except Exception as e:
            error_message = str(e)
            last_error = error_message
            attempts_log.append({
                "attempt": attempt,
                "sql": sql,
                "status": "failed",
                "error": error_message
            })

            if attempt == max_attempts or not should_retry_bq_error(error_message):
                break

            sql = fix_sql(user_question, schema, sql, error_message)

    raise RuntimeError(
        f"Query failed after {max_attempts} attempts. Last error: {last_error}\n"
        f"Attempts log: {attempts_log}"
    )

def validate_sql(sql: str) -> None:
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "MERGE"]
    upper_sql = sql.upper()

    for word in forbidden:
        if word in upper_sql:
            raise ValueError(f"Unsafe SQL detected: {word}")

    if TABLE_NAME not in sql:
        raise ValueError("SQL does not reference the expected table.")


def run_query(sql: str) -> list[dict[str, Any]]:
    query_job = bq_client.query(sql)
    rows = query_job.result()
    return [dict(row.items()) for row in rows]


def summarize_results(user_question: str, results: list[dict[str, Any]]) -> str:
    prompt = f"""
You are a helpful data assistant.

A user asked:
{user_question}

The SQL query returned this JSON result:
{json.dumps(results[:20], default=str)}

Write a concise, clear answer in plain English.
If the result is empty, say no matching data was found.
""".strip()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text.strip()


st.set_page_config(page_title="Chat with Your Data", layout="wide")

st.title("Chat with Your Data")
st.write("Ask natural language questions about your Netflix user behavior dataset.")

question = st.text_area(
    "Enter your question",
    placeholder="Example: For each country, find the top 3 genres by total watch duration."
)

if st.button("Run Query"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Fetching schema..."):
                schema = get_table_schema(TABLE_NAME)

            with st.spinner("Generating and executing SQL..."):
                sql, results, attempts_log  = execute_with_retries(question, schema, max_attempts=4)

            st.subheader("Generated SQL")
            st.code(sql, language="sql")

            with st.expander("Retry details"):
                for entry in attempts_log:
                    st.write(f"Attempt {entry['attempt']} - {entry['status']}")
                    st.code(entry["sql"], language="sql")
                    if entry["error"]:
                        st.error(entry["error"])

            validate_sql(sql)

            with st.spinner("Running query on BigQuery..."):
                results = run_query(sql)

            st.subheader("Query Results")
            if results:
                st.dataframe(pd.DataFrame(results))
            else:
                st.info("No matching data found.")

            with st.spinner("Summarizing results..."):
                answer = summarize_results(question, results)

            st.subheader("Summary")
            st.write(answer)

        except Exception as e:
            st.error(f"Error: {e}")