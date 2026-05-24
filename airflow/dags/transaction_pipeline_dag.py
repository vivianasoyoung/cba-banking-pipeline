"""
transaction_pipeline_dag.py
-----------------------------
Daily DAG (ingestion only):
  1. Verifies raw CSV data exists
  2. Validates data quality (NULLs, dupes, invalid types, future dates)
  3. Loads accounts (upsert) and transactions (incremental via high-water mark)
  4. Logs the run outcome to raw.pipeline_runs

Downstream transformations live in the cba-dbt-analytics repo and are
scheduled independently. Credentials come from the Airflow Connection
`cba_postgres` — no secrets in code.
"""

from datetime import datetime, timedelta
import logging
import os

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2.extras import execute_values

log = logging.getLogger(__name__)

POSTGRES_CONN_ID      = "cba_postgres"
RAW_TRANSACTIONS_PATH = "/opt/airflow/data/raw/transactions.csv"
RAW_ACCOUNTS_PATH     = "/opt/airflow/data/raw/accounts.csv"

default_args = {
    "owner":            "data-engineering",
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}


def _get_conn():
    return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID).get_conn()


def check_source_files(**_):
    for path in (RAW_TRANSACTIONS_PATH, RAW_ACCOUNTS_PATH):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Source file not found: {path}. "
                "Run: python scripts/generate_transactions.py --months 6 --accounts 500"
            )
        log.info("Found %s (%.1f MB)", path, os.path.getsize(path) / 1_000_000)


def run_quality_checks(**context):
    df = pd.read_csv(RAW_TRANSACTIONS_PATH, parse_dates=["transaction_date"])
    issues: list[str] = []

    for col in ("transaction_id", "account_id", "transaction_date", "amount", "transaction_type"):
        n = int(df[col].isna().sum())
        if n:
            issues.append(f"NULL values in {col}: {n} rows")

    n_dupe = int(df["transaction_id"].duplicated().sum())
    if n_dupe:
        issues.append(f"Duplicate transaction_ids: {n_dupe}")

    n_neg = int((df["amount"] < 0).sum())
    if n_neg:
        issues.append(f"Negative amounts: {n_neg} rows")

    n_invalid = int((~df["transaction_type"].isin({"DEBIT", "CREDIT"})).sum())
    if n_invalid:
        issues.append(f"Invalid transaction_type values: {n_invalid} rows")

    n_future = int((df["transaction_date"] > datetime.now()).sum())
    if n_future:
        issues.append(f"Future-dated transactions: {n_future} rows")

    context["ti"].xcom_push(key="quality_issues", value=issues)
    context["ti"].xcom_push(key="quality_total_rows", value=int(len(df)))

    if issues:
        log.warning("Quality issues:\n%s", "\n".join(f"  - {i}" for i in issues))
    else:
        log.info("All quality checks passed. %s rows.", f"{len(df):,}")


def load_accounts(**_):
    df = pd.read_csv(RAW_ACCOUNTS_PATH)
    df["loaded_at"] = datetime.now()
    records = list(df.itertuples(index=False, name=None))

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO raw.accounts (
                    account_id, customer_id, bsb, account_number,
                    account_type, open_date, balance, credit_limit, loaded_at
                ) VALUES %s
                ON CONFLICT (account_id) DO UPDATE SET
                    balance   = EXCLUDED.balance,
                    loaded_at = EXCLUDED.loaded_at
                """,
                records,
                page_size=1000,
            )
            inserted_or_updated = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    log.info("Upserted %s accounts.", f"{inserted_or_updated:,}")


def load_transactions(**context):
    df = pd.read_csv(RAW_TRANSACTIONS_PATH, parse_dates=["transaction_date"])

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(transaction_date), '1970-01-01'::timestamp) FROM raw.transactions")
            high_water = cur.fetchone()[0]
        log.info("High-water mark: %s", high_water)

        new_df = df[df["transaction_date"] > high_water].copy()
        if new_df.empty:
            log.info("No new transactions since high-water mark; nothing to load.")
            context["ti"].xcom_push(key="rows_loaded", value=0)
            return

        new_df["loaded_at"] = datetime.now()
        records = list(new_df.itertuples(index=False, name=None))

        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO raw.transactions (
                    transaction_id, account_id, bsb, account_number,
                    transaction_date, amount, transaction_type,
                    merchant_name, merchant_category, merchant_state,
                    description, balance_after, channel, status, loaded_at
                ) VALUES %s
                ON CONFLICT (transaction_id) DO NOTHING
                """,
                records,
                page_size=500,
            )
            rows_loaded = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    log.info("Loaded %s transactions.", f"{rows_loaded:,}")
    context["ti"].xcom_push(key="rows_loaded", value=int(rows_loaded))


def log_pipeline_run(**context):
    ti = context["ti"]
    rows_loaded = ti.xcom_pull(task_ids="load_transactions", key="rows_loaded") or 0
    issues      = ti.xcom_pull(task_ids="run_quality_checks", key="quality_issues") or []

    status = "SUCCESS" if not issues else "SUCCESS_WITH_WARNINGS"

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.pipeline_runs
                    (dag_id, run_date, rows_ingested, rows_rejected,
                     status, quality_issues, started_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    context["dag"].dag_id,
                    context["ds"],
                    rows_loaded,
                    0,
                    status,
                    "\n".join(issues) if issues else None,
                    context["dag_run"].start_date,
                    datetime.now(),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    log.info("Audit logged: status=%s rows=%s", status, rows_loaded)


with DAG(
    dag_id="cba_transaction_pipeline",
    description="Daily ingestion of CBA-style banking transactions",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["banking", "ingestion", "daily"],
) as dag:

    t1 = PythonOperator(task_id="check_source_files",  python_callable=check_source_files)
    t2 = PythonOperator(task_id="run_quality_checks",  python_callable=run_quality_checks)
    t3 = PythonOperator(task_id="load_accounts",       python_callable=load_accounts)
    t4 = PythonOperator(task_id="load_transactions",   python_callable=load_transactions)
    t5 = PythonOperator(task_id="log_pipeline_run",    python_callable=log_pipeline_run, trigger_rule="all_done")

    t1 >> t2 >> t3 >> t4 >> t5
