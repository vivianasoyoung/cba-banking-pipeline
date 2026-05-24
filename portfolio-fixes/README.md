# Portfolio fixes

Drafts to copy into the four CBA repos. Organized by destination repo.

| Folder | Target repo | What's in it |
| --- | --- | --- |
| `feature-store/` | `cba-feature-store` | Leakage fix + Feast/MLflow serving fix |
| `fraud-streaming/` | `cba-fraud-streaming` | Producer fix, requirements, Dockerfile, idempotent writes |
| `dbt-analytics/` | `cba-dbt-analytics` | `_models.yml` schema files, `packages.yml`, `profiles.example.yml`, `.gitignore` |
| `banking-pipeline/` | `cba-banking-pipeline` | DAG that actually calls dbt + uses PostgresHook |
| `_shared/` | all four repos | Reusable CI workflow + cross-repo README section + Mermaid diagram |

## Priority order

1. **`feature-store/`** — kills the target-leakage bug (single biggest credibility issue).
2. **`fraud-streaming/transaction_producer.py`** — fixes the missing docstring opener (`"""`).
3. **`_shared/portfolio-overview.md`** — turns four repos into one project narrative.
4. **`dbt-analytics/`** — `_models.yml` + `.gitignore` jump the dbt repo a full grade.
5. **`banking-pipeline/`** — resolves the "DAG claims to run dbt but doesn't" gap.
6. **`_shared/ci.yml`** — drop into `.github/workflows/` of each repo, customize per stack.
