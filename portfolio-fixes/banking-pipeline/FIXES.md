# cba-banking-pipeline — fix plan

Apply in this order. Each item lists: **the problem**, **the fix**, and **the file** to drop in.

---

## 1. Delete the duplicate root SQL files

**Problem.** `stg_transactions.sql` and `mart_daily_category_spend.sql` sit at the repo root and are *more feature-complete* than the dbt versions in `dbt/models/`. Two sources of truth.

**Fix.**
```bash
# Port the window functions (spend_rank_for_day, cumulative_monthly_spend)
# into dbt/models/marts/mart_daily_category_spend.sql first,
# then delete the root copies.
git rm stg_transactions.sql mart_daily_category_spend.sql
```

The corrected dbt mart is in `dbt-mart_daily_category_spend.sql` in this folder.

---

## 2. Resolve the overlap with `cba-dbt-analytics`

**Problem.** Both repos define `stg_transactions` against the same `cba_pipeline.raw` source. Reviewer cannot tell which is authoritative.

**Recommended fix.** Delete `dbt/` from THIS repo entirely. This repo becomes pure ingestion (Airflow + Postgres). `cba-dbt-analytics` owns all transformations.

```bash
git rm -r dbt/
```

Then update the README to say "downstream transformations live in cba-dbt-analytics" and link to it.

If you'd rather keep dbt here, delete the dbt project in `cba-dbt-analytics` instead. **Pick one.**

---

## 3. Make the DAG actually call dbt

**Problem.** The DAG docstring claims it "Runs dbt transformations" but there is no dbt task.

**Fix.** Drop in `transaction_pipeline_dag.py` from this folder. Changes:
- Adds a `BashOperator` task `dbt_run_and_test` after `load_transactions`.
- Uses `PostgresHook` instead of hardcoded credentials.
- Reads connection from Airflow Connection `cba_postgres` (set via UI or env var).
- Uses `cur.rowcount` correctly (no `len(records)` fallback).
- Adds `event_time` vs `processed_at` semantics in the audit table.
- Marks the run `FAILED` if quality checks raised issues, not always `SUCCESS`.

If you go with #2's recommendation (delete dbt here), the BashOperator should clone or path-mount `cba-dbt-analytics` instead — pick the approach that fits your deploy story.

---

## 4. Replace hardcoded credentials

**Problem.** `airflow/dags/transaction_pipeline_dag.py:28-30` hardcodes `"password": "airflow"`.

**Fix.** Use `PostgresHook` (in the drop-in DAG below). For local dev, set the connection via env var in `docker-compose.yml`:

```yaml
AIRFLOW_CONN_CBA_POSTGRES: postgres://airflow:${POSTGRES_PASSWORD:-airflow}@postgres:5432/cba_pipeline
```

Add a `.env.example` (in this folder) and document `cp .env.example .env` in the README.

---

## 5. Use a real Dockerfile for Airflow, not `_PIP_ADDITIONAL_REQUIREMENTS`

**Problem.** Compose uses `_PIP_ADDITIONAL_REQUIREMENTS` which Airflow's own docs say is "for development only, NEVER use in production."

**Fix.** Drop in `docker/Dockerfile.airflow` and `requirements.txt` from this folder. Update `docker-compose.yml` Airflow services to `build:` instead of `image:`.

---

## 6. Fix incremental load semantics

**Problem.** `load_transactions` filters by `run_date` only. A missed day silently drops rows; a backfill of N days only loads day N.

**Fix.** The drop-in DAG uses a high-water-mark pattern: query `MAX(transaction_date)` from `raw.transactions` and load everything strictly greater than that. Idempotent via the existing `ON CONFLICT (transaction_id) DO NOTHING`.

---

## 7. Audit log status reflects reality

**Problem.** `log_pipeline_run` always writes `status='SUCCESS'` even when quality checks found issues.

**Fix.** Drop-in DAG pulls the quality issue list from XCom and writes `SUCCESS` / `SUCCESS_WITH_WARNINGS` / `FAILED` accordingly.

---

## 8. Add `.gitignore` entries

Add to `.gitignore`:
```
data/raw/*.csv
.env
__pycache__/
*.pyc
airflow/logs/
```

Commit a tiny `data/raw/.gitkeep` and document `python scripts/generate_transactions.py` as the regeneration command.

---

## 9. Add CI

Drop in `.github/workflows/ci.yml` from `portfolio-fixes/_shared/ci-python.yml`. Tweaks needed:
- Lint with `ruff`.
- Import-check the DAG (catches syntax errors without booting Airflow):
  ```yaml
  - run: python -c "import sys; sys.path.insert(0, 'airflow/dags'); import transaction_pipeline_dag"
  ```

---

## 10. README updates

Add to README:
- "How this connects to the other repos" section (see `_shared/portfolio-overview.md`).
- A Mermaid architecture diagram (in `_shared/architecture.mmd`).
- Soften "production-style" claims to "demonstrates the pattern."
- Document the `cba_postgres` Airflow Connection setup.

---

## Files in this folder

- `transaction_pipeline_dag.py` — drop-in replacement for `airflow/dags/transaction_pipeline_dag.py`
- `dbt-mart_daily_category_spend.sql` — port of root SQL's window functions into the dbt mart
- `Dockerfile.airflow` — proper Airflow image build
- `requirements.txt` — pinned Python deps
- `.env.example` — env var template
- `docker-compose.diff` — patch notes for compose
