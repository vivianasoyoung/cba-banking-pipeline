# CBA Transaction Pipeline

An end-to-end batch data pipeline simulating a banking transaction ingestion and analytics system, modelled on Commonwealth Bank of Australia's transaction data structures.

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
   ├── Data quality checks
   ├── Load raw.accounts (upsert)
   ├── Load raw.transactions (incremental)
   └── Pipeline audit logging
        │
        ▼
   PostgreSQL (raw schema)
        │
        ▼
   dbt transformations
   ├── staging.stg_transactions (cleaned view)
   └── marts.mart_daily_category_spend (analytics table)
```

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.8 |
| Storage | PostgreSQL 15 |
| Transformation | dbt-postgres |
| Containerisation | Docker + Docker Compose |
| Data Generation | Python (Faker, pandas) |

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.10+

### 1. Clone and generate data

```bash
git clone https://github.com/yourusername/cba-transaction-pipeline
cd cba-transaction-pipeline

pip install faker pandas
python scripts/generate_transactions.py --months 6 --accounts 500
```

This generates:
- `data/raw/accounts.csv` — 500 synthetic accounts with Australian BSBs
- `data/raw/transactions.csv` — ~200k transactions across 6 months

### 2. Start the stack

```bash
docker-compose up -d
```

Services:
| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin |
| pgAdmin | http://localhost:5050 | admin@admin.com / admin |

### 3. Trigger the pipeline

In Airflow UI:
1. Enable the `cba_transaction_pipeline` DAG
2. Trigger a manual run
3. Watch tasks execute: file check → quality → accounts → transactions → audit log

### 4. Run dbt models

```bash
cd dbt
dbt run
dbt test
dbt docs generate && dbt docs serve
```

## Data Model

### Raw Layer (`raw` schema)
| Table | Description |
|---|---|
| `raw.transactions` | All ingested transactions (incremental) |
| `raw.accounts` | Account master data (upsert) |
| `raw.pipeline_runs` | Audit log of every DAG run |

### Staging Layer (`staging` schema)
| Model | Description |
|---|---|
| `stg_transactions` | Cleaned, typed, standardised transactions |

### Marts Layer (`marts` schema)
| Model | Description |
|---|---|
| `mart_daily_category_spend` | Daily spend by merchant category with rankings and cumulative totals |

## Data Quality Checks

The pipeline validates:
- No null values in critical fields (transaction_id, account_id, amount)
- No duplicate transaction IDs
- No negative amounts
- Valid transaction types (DEBIT / CREDIT only)
- No future-dated transactions

## Australian Banking Context

- BSB numbers follow real state-based Australian formats
- Merchant categories reflect Australian spending patterns (Woolworths, Coles, Opal Card, BPAY etc.)
- Account types: SAVINGS, TRANSACTION, OFFSET
- Channels: EFTPOS, ATM, ONLINE, BPAY

## Project Structure

```
cba-transaction-pipeline/
├── airflow/
│   └── dags/
│       └── transaction_pipeline_dag.py
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_transactions.sql
│   │   └── marts/
│   │       └── mart_daily_category_spend.sql
│   └── dbt_project.yml
├── docker/
│   └── init.sql
├── scripts/
│   └── generate_transactions.py
├── data/
│   └── raw/           # generated — gitignored
├── docker-compose.yml
└── README.md
```

## Next Steps

- [ ] Add Great Expectations data quality suite
- [ ] Add `mart_account_monthly_summary` model
- [ ] Add fraud signal detection mart
- [ ] Connect to Metabase or Streamlit for dashboarding
