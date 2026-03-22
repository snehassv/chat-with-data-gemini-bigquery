import json
import os
from typing import Any

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

def get_table_schema(table_name: str) -> str:
    table = bq_client.get_table(table_name)
    lines = [f"Table: {table_name}", "", "Columns:"]
    for field in table.schema:
        lines.append(f"- {field.name} ({field.field_type})")
    return "\n".join(lines)

def generate_sql(user_question: str, schema) -> str:
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

User question:
{user_question}
""".strip()

    response = client.models.generate_content(
        model = MODEL_NAME,
        contents=prompt)
    sql = response.text.strip()
    return sql


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
        model = MODEL_NAME,
        contents = prompt)

    return response.text.strip()

def main() -> None:

    print("Chat with Your Data")
    question = input("Ask a question about the Netflix data: ").strip()

    print("Getting table schema...........")
    schema = get_table_schema(TABLE_NAME)
    sql = generate_sql(question, schema)
    print("\nGenerated SQL:\n")
    print(sql)

    validate_sql(sql)

    results = run_query(sql)
    print("\nRaw Results:\n")
    print(json.dumps(results[:10], indent=2, default=str))

    answer = summarize_results(question, results)
    print("\nFinal Answer:\n")
    print(answer)


if __name__ == "__main__":
    main()