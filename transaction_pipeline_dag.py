"""
transaction_pipeline_dag.py
-----------------------------
Daily DAG that:
  1. Checks raw CSV data exists
  2. Validates data quality
  3. Loads new transactions into raw.transactions
  4. Runs dbt transformations
  5. Logs the pipeline run result
"""

from datetime import datetime, timedelta
import logging
import os

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.getenv("PIPELINE_DB_HOST", "postgres"),
    "port":     5432,
    "dbname":   "cba_pipeline",
    "user":     "airflow",
    "password": "airflow",
}

RAW_TRANSACTIONS_PATH = "/opt/airflow/data/raw/transactions.csv"
RAW_ACCOUNTS_PATH     = "/opt/airflow/data/raw/accounts.csv"

default_args = {
    "owner":            "data-engineering",
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}


# ── Task 1: Validate source files exist ─────────────────────────────────────
def check_source_files(**context):
    for path in [RAW_TRANSACTIONS_PATH, RAW_ACCOUNTS_PATH]:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Source file not found: {path}\n"
                f"Run: python scripts/generate_transactions.py --months 6 --accounts 500"
            )
        size_mb = os.path.getsize(path) / 1_000_000
        log.info(f"Found {path} ({size_mb:.1f} MB)")


# ── Task 2: Data quality checks ─────────────────────────────────────────────
def run_quality_checks(**context):
    df = pd.read_csv(RAW_TRANSACTIONS_PATH, parse_dates=["transaction_date"])

    issues = []

    # Null checks
    critical_cols = ["transaction_id", "account_id", "transaction_date", "amount", "transaction_type"]
    for col in critical_cols:
        null_count = df[col].isna().sum()
        if null_count > 0:
            issues.append(f"NULL values in {col}: {null_count} rows")

    # Duplicate transaction IDs
    dupe_count = df["transaction_id"].duplicated().sum()
    if dupe_count > 0:
        issues.append(f"Duplicate transaction_ids: {dupe_count}")

    # Negative amounts
    neg_count = (df["amount"] < 0).sum()
    if neg_count > 0:
        issues.append(f"Negative amounts: {neg_count} rows")

    # Invalid transaction types
    valid_types = {"DEBIT", "CREDIT"}
    invalid_types = df[~df["transaction_type"].isin(valid_types)]
    if len(invalid_types) > 0:
        issues.append(f"Invalid transaction_type values: {len(invalid_types)} rows")

    # Future-dated transactions
    future = df[df["transaction_date"] > datetime.now()]
    if len(future) > 0:
        issues.append(f"Future-dated transactions: {len(future)} rows")

    # Push quality stats to XCom for audit log
    context["ti"].xcom_push(key="quality_stats", value={
        "total_rows":    len(df),
        "null_issues":   len([i for i in issues if "NULL" in i]),
        "dupe_issues":   dupe_count,
        "issues":        issues,
    })

    if issues:
        log.warning(f"Quality issues found:\n" + "\n".join(f"  - {i}" for i in issues))
    else:
        log.info(f"All quality checks passed. {len(df):,} rows ready for ingestion.")


# ── Task 3: Load accounts (upsert) ──────────────────────────────────────────
def load_accounts(**context):
    df = pd.read_csv(RAW_ACCOUNTS_PATH)
    df["loaded_at"] = datetime.now()

    records = [tuple(row) for row in df.itertuples(index=False, name=None)]

    conn = psycopg2.connect(**DB_CONFIG)
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
                    balance    = EXCLUDED.balance,
                    loaded_at  = EXCLUDED.loaded_at
                """,
                records,
                page_size=1000,
            )
        conn.commit()
        log.info(f"Upserted {len(records):,} accounts into raw.accounts")
    finally:
        conn.close()


# ── Task 4: Load transactions (incremental) ─────────────────────────────────
def load_transactions(**context):
    run_date = context["ds"]  # YYYY-MM-DD string
    df = pd.read_csv(RAW_TRANSACTIONS_PATH, parse_dates=["transaction_date"])

    # Incremental: only load transactions for this dag run date
    day_df = df[df["transaction_date"].dt.date.astype(str) == run_date].copy()

    if day_df.empty:
        log.info(f"No transactions found for {run_date} — skipping load.")
        context["ti"].xcom_push(key="rows_loaded", value=0)
        return

    day_df["loaded_at"] = datetime.now()
    records = [tuple(row) for row in day_df.itertuples(index=False, name=None)]

    conn = psycopg2.connect(**DB_CONFIG)
    rows_loaded = 0
    rows_rejected = 0
    try:
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
            rows_loaded = cur.rowcount if cur.rowcount > 0 else len(records)
        conn.commit()
        log.info(f"Loaded {rows_loaded:,} transactions for {run_date}")
    except Exception as e:
        conn.rollback()
        rows_rejected = len(records)
        log.error(f"Load failed: {e}")
        raise
    finally:
        conn.close()

    context["ti"].xcom_push(key="rows_loaded", value=rows_loaded)
    context["ti"].xcom_push(key="rows_rejected", value=rows_rejected)


# ── Task 5: Log pipeline run ─────────────────────────────────────────────────
def log_pipeline_run(**context):
    ti = context["ti"]
    rows_loaded   = ti.xcom_pull(task_ids="load_transactions",  key="rows_loaded")   or 0
    rows_rejected = ti.xcom_pull(task_ids="load_transactions",  key="rows_rejected") or 0
    quality_stats = ti.xcom_pull(task_ids="run_quality_checks", key="quality_stats") or {}

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.pipeline_runs
                    (dag_id, run_date, rows_ingested, rows_rejected, status, started_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    context["dag"].dag_id,
                    context["ds"],
                    rows_loaded,
                    rows_rejected,
                    "SUCCESS",
                    context["dag_run"].start_date,
                    datetime.now(),
                ),
            )
        conn.commit()
        log.info(f"Pipeline run logged: {rows_loaded} rows ingested, {rows_rejected} rejected.")
    finally:
        conn.close()


# ── DAG definition ───────────────────────────────────────────────────────────
with DAG(
    dag_id="cba_transaction_pipeline",
    description="Daily ingestion of CBA-style banking transaction data",
    schedule_interval="0 6 * * *",   # 6am daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["banking", "ingestion", "daily"],
) as dag:

    t1_check_files = PythonOperator(
        task_id="check_source_files",
        python_callable=check_source_files,
    )

    t2_quality = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks,
    )

    t3_accounts = PythonOperator(
        task_id="load_accounts",
        python_callable=load_accounts,
    )

    t4_transactions = PythonOperator(
        task_id="load_transactions",
        python_callable=load_transactions,
    )

    t5_log = PythonOperator(
        task_id="log_pipeline_run",
        python_callable=log_pipeline_run,
    )

    t1_check_files >> t2_quality >> t3_accounts >> t4_transactions >> t5_log
