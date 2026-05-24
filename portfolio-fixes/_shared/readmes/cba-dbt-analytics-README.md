# CBA dbt Analytics Layer

Analytics engineering project built on Australian banking transaction data. Implements a three-layer dbt architecture — staging, intermediate, and marts — with column-level documentation, tests, and snapshots.

## How this fits with the rest of the project

This is one of four repos that together form an end-to-end banking data platform:

| Repo | Stack | Role |
| --- | --- | --- |
| [`cba-banking-pipeline`](https://github.com/vivianasoyoung/cba-banking-pipeline) | Airflow, Postgres, Docker | Foundation: synthetic data generation + batch ingestion |
| **[`cba-dbt-analytics`](https://github.com/vivianasoyoung/cba-dbt-analytics)** *(You are here)* | dbt-postgres, dbt_utils | Staging → intermediate → marts transformations |
| [`cba-fraud-streaming`](https://github.com/vivianasoyoung/cba-fraud-streaming) | Kafka, Python, Postgres | Real-time rule-based fraud detection |
| [`cba-feature-store`](https://github.com/vivianasoyoung/cba-feature-store) | Feast, MLflow, FastAPI | ML feature store + model serving |

This repo owns all transformations. Reads from `cba_pipeline.raw.*` (populated by `cba-banking-pipeline`).

---

## Architecture

```
raw.transactions (PostgreSQL)
raw.accounts (PostgreSQL)
        │
        ▼
Staging Layer (views)
   ├── stg_transactions   — cleaned, typed, standardised transactions
   └── stg_accounts       — cleaned account master data
        │
        ▼
Intermediate Layer (views)
   ├── int_customer_monthly_category_spend  — grain: account × month × category
   └── int_customer_monthly_spend           — grain: account × month (rolled up)
        │
        ▼
Marts Layer (tables)
   ├── mart_customer_segments       — customer segmentation by 12-month avg spend
   ├── mart_category_trends         — weighted monthly spend trends by category
   ├── mart_monthly_summary         — portfolio-level monthly summary
   └── mart_daily_category_spend    — daily category spend with rankings & cumulative totals
```

## Tech Stack

| Layer | Tool |
|---|---|
| Transformation | dbt-postgres 1.7 |
| Packages | dbt_utils, dbt_expectations |
| Storage | PostgreSQL 15 |
| Source data | cba-banking-pipeline (95k transactions, 500 accounts) |

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL running with `cba_pipeline` database populated
- See [cba-banking-pipeline](https://github.com/vivianasoyoung/cba-banking-pipeline) to set up the source data

### 1. Install dbt + packages

```bash
pip install dbt-postgres==1.7.9
cd cba_dbt_analytics
dbt deps
```

### 2. Configure connection

```bash
cp profiles.example.yml ~/.dbt/profiles.yml
export POSTGRES_PASSWORD=<your_password>
```

The `profiles.example.yml` reads connection details from environment variables.

### 3. Build and test

```bash
dbt build       # runs models, then tests
```

### 4. Generate docs

```bash
dbt docs generate
dbt docs serve --port 8081
```

Open http://localhost:8081 to see the full lineage graph.

## Models

### Staging
| Model | Materialisation | Description |
|---|---|---|
| `stg_transactions` | view | Cleaned transactions — standardised columns, declined filtered out |
| `stg_accounts` | view | Cleaned account master data |

### Intermediate
| Model | Materialisation | Description |
|---|---|---|
| `int_customer_monthly_category_spend` | view | Monthly spend per account per merchant category |
| `int_customer_monthly_spend` | view | Monthly spend per account (categories rolled up) |

### Marts
| Model | Materialisation | Description |
|---|---|---|
| `mart_customer_segments` | table | Accounts segmented by 12-month average monthly spend (dormant months count as zero) |
| `mart_category_trends` | table | Monthly spend trends by merchant category, weighted averages |
| `mart_monthly_summary` | table | Portfolio-level monthly summary |
| `mart_daily_category_spend` | table | Daily category spend with spend rank and cumulative monthly spend |

## Customer Segments

| Segment | Criteria |
|---|---|
| Premium | 12-month avg monthly spend ≥ $5,000 |
| High Value | 12-month avg monthly spend ≥ $2,000 |
| Regular | 12-month avg monthly spend ≥ $500 |
| Low Activity | 12-month avg monthly spend < $500 |

## Data Tests

Every model has column-level tests defined in `_*_models.yml`:
- `unique` + `not_null` on primary keys
- `not_null` on critical columns
- `accepted_values` on enums (`transaction_type`, `channel`, `account_type`, `customer_segment`)
- `relationships` between staging models (transactions → accounts)
- `dbt_utils.expression_is_true` for numeric constraints (e.g. amounts ≥ 0)
- `dbt_utils.unique_combination_of_columns` for composite keys in marts

Run with `dbt test`.

## Project Structure

```
cba-dbt-analytics/
├── profiles.example.yml
├── packages.yml
└── cba_dbt_analytics/
    ├── dbt_project.yml
    ├── models/
    │   ├── staging/
    │   │   ├── sources.yml
    │   │   ├── _stg__models.yml
    │   │   ├── stg_transactions.sql
    │   │   └── stg_accounts.sql
    │   ├── intermediate/
    │   │   ├── _int__models.yml
    │   │   ├── int_customer_monthly_category_spend.sql
    │   │   └── int_customer_monthly_spend.sql
    │   └── marts/
    │       ├── _marts__models.yml
    │       ├── mart_customer_segments.sql
    │       ├── mart_category_trends.sql
    │       ├── mart_monthly_summary.sql
    │       └── mart_daily_category_spend.sql
    ├── snapshots/
    └── tests/
```
