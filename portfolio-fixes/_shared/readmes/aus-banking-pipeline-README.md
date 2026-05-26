# Australian Banking Transaction Pipeline

An end-to-end batch data pipeline simulating a retail banking transaction ingestion system, modelled on Australian banking transaction data structures.

> **Disclaimer:** Personal learning project built with entirely synthetic, programmatically generated data. Not affiliated with, endorsed by, or using systems, schemas, or data from any financial institution. "Australian banking" refers to generic retail-banking data structures (e.g. BSB formats, common merchant categories), not any specific bank.

## How this fits with the rest of the project

This is one of four repos that together form an end-to-end banking data platform:

| Repo | Stack | Role |
| --- | --- | --- |
| **[`aus-banking-pipeline`](https://github.com/vivianasoyoung/aus-banking-pipeline)** *(You are here)* | Airflow, Postgres, Docker | Foundation: synthetic data generation + batch ingestion |
| [`aus-dbt-analytics`](https://github.com/vivianasoyoung/aus-dbt-analytics) | dbt-postgres, dbt_utils | Staging → intermediate → marts transformations |
| [`aus-fraud-streaming`](https://github.com/vivianasoyoung/aus-fraud-streaming) | Kafka, Python, Postgres | Real-time rule-based fraud detection |
| [`aus-feature-store`](https://github.com/vivianasoyoung/aus-feature-store) | Feast, MLflow, FastAPI | ML feature store + model serving |

This repo is **ingestion-only**. Downstream transformations live in `aus-dbt-analytics` and are scheduled independently.

---

## Architecture

```
Synthetic Data Generator
        │
        ▼
   Raw CSV Files
        │
        ▼
  Apache Airflow DAG (daily @ 6am)
   ├── Source file validation
   ├── Data quality checks (NULLs, dupes, invalid types, future dates)
   ├── Load raw.accounts (upsert)
   ├── Load raw.transactions (incremental via high-water mark)
   └── Pipeline audit logging
        │
        ▼
   PostgreSQL (raw schema)
        │
        ▼
   Consumed downstream by aus-dbt-analytics
```

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.8 |
| Storage | PostgreSQL 15 |
| Containerisation | Docker + Docker Compose |
| Data Generation | Python (Faker, pandas) |

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.10+

### 1. Generate synthetic data

```bash
pip install faker pandas
python scripts/generate_transactions.py --months 6 --accounts 500
```

Generates ~200,000 synthetic transactions across 500 accounts over six months, using Australian Bank State Branch (BSB) code formats.

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD
```

### 3. Start the stack

```bash
docker-compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin |
| pgAdmin | http://localhost:5050 | admin@admin.com / admin |

### 4. Trigger the pipeline

In the Airflow UI: configure the Postgres Airflow Connection (host `postgres`, schema `raw`, credentials from `.env`), enable the `transaction_pipeline` DAG, and trigger a run.

## Data Model

| Table | Description |
|---|---|
| `raw.transactions` | Ingested transactions (incremental, idempotent via `ON CONFLICT DO NOTHING`) |
| `raw.accounts` | Account master data (upsert) |
| `raw.pipeline_runs` | Audit log of every DAG run, including any data-quality issues found |

## Data Quality Checks

Each ingestion batch is validated for: NULLs in critical columns, duplicate `transaction_id`s, negative amounts, invalid `transaction_type` values (`DEBIT`/`CREDIT`), and future-dated transactions. Issues are logged to `raw.pipeline_runs` and the run is marked `SUCCESS_WITH_WARNINGS`.

## Australian Banking Context

- BSB numbers follow regional Australian formatting conventions
- Merchant categories mirror common Australian retail/service patterns
- Account types: SAVINGS, TRANSACTION, OFFSET
- Channels: EFTPOS, ATM, ONLINE, BPAY

## Project Structure

```
aus-banking-pipeline/
├── airflow/dags/transaction_pipeline_dag.py
├── docker/init.sql
├── scripts/generate_transactions.py
├── data/raw/                    # gitignored — regenerated locally
├── docker-compose.yml
├── .env.example
└── README.md
```
