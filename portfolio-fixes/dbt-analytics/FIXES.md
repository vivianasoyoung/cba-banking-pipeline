# cba-dbt-analytics — fix plan

Apply in this order.

---

## 1. Clean up scaffolding garbage

**Problem.** `logs/dbt.log` is committed. `tests/`, `macros/`, `snapshots/` are all just `.gitkeep` — the directory layout of `dbt init` with nothing inside.

**Fix.**
```bash
git rm logs/dbt.log
# Either fill these dirs with real content (see #6) or delete them:
git rm -r cba_dbt_analytics/{tests,macros,snapshots}  # if leaving empty looks bad
```

Drop in the `.gitignore` from this folder.

---

## 2. Add `packages.yml`

**Problem.** No dbt packages. Real analytics engineering uses `dbt_utils` constantly.

**Fix.** Drop in `packages.yml` from this folder, then:
```bash
cd cba_dbt_analytics && dbt deps
```
Add `dbt_packages/` to `.gitignore`.

---

## 3. Add `profiles.example.yml`

**Problem.** README tells users to create `~/.dbt/profiles.yml` but never shows what it should look like.

**Fix.** Drop in `profiles.example.yml` from this folder at the repo root. README:
```bash
cp profiles.example.yml ~/.dbt/profiles.yml
# edit credentials
```

---

## 4. Add `_models.yml` schema files

**Problem.** No column docs, no model-level tests, no descriptions anywhere. This is dbt's signature feature and you're not using it.

**Fix.** Drop in three schema files from this folder:
- `models/staging/_stg__models.yml`
- `models/intermediate/_int__models.yml`
- `models/marts/_marts__models.yml`

These add: column descriptions, `not_null`, `unique`, `accepted_values`, and `relationships` tests. Single biggest credibility upgrade for this repo.

Run `dbt test` to verify they pass.

---

## 5. Fix the broken segmentation logic

**Problem.** In `mart_customer_segments.sql`:
```sql
avg(total_spend) as avg_monthly_spend
```
This averages `total_spend` across the *active* months of the input grain. But `int_customer_monthly_spend` is grouped by `(account_id, customer_id, account_type, transaction_month, merchant_category)` — so it's customer-month-CATEGORY grain. You're averaging across categories AND months. A customer with one big $5k Groceries spend looks like "Premium."

**Fix.** Drop in `mart_customer_segments.sql` from this folder. It:
- Aggregates to (account_id, transaction_month) first, then averages months.
- Divides by a fixed window (last 12 observed months) rather than active months only.
- Uses `coalesce(..., 0)` so dormant months count as zero.

---

## 6. Fix `int_customer_monthly_spend` naming

**Problem.** The model is grouped by merchant_category but called "monthly spend" — the name lies about the grain.

**Fix.** Rename to `int_customer_monthly_category_spend` (matches grain). Add a second intermediate `int_customer_monthly_spend` that rolls categories up. Both files in this folder.

Update `mart_customer_segments.sql` and `mart_monthly_summary.sql` to ref the correct one.

---

## 7. Fix `avg(avg_spend)` in `mart_category_trends`

**Problem.** Averaging averages is meaningless.

**Fix.** Replace with weighted: `sum(total_spend) / nullif(sum(transaction_count), 0)`. See `mart_category_trends.sql` in this folder.

---

## 8. Add a real snapshot (optional but high-signal)

**Problem.** Empty `snapshots/` dir.

**Fix.** Drop in `snapshots/accounts_snapshot.sql` — an SCD2 snapshot of `raw.accounts` keyed by `account_id` with `check` strategy on `balance` + `credit_limit`. Shows you know dbt snapshots exist.

---

## 9. Add a real generic test

**Problem.** Empty `tests/` dir.

**Fix.** Drop in `tests/assert_mart_segments_partition.sql` — a singular test that asserts every account in `mart_customer_segments` is in exactly one segment.

---

## 10. Add CI

Drop in `.github/workflows/dbt.yml` (in this folder). Spins up Postgres in services, seeds fake data, runs `dbt deps && dbt build`.

---

## 11. README softening

- "Production-style analytics engineering" → "Demonstrates the three-layer pattern (staging / intermediate / marts) with tests, docs, and snapshots."
- Add: "Requires `cba-banking-pipeline` to have loaded raw data first" with a link.
- Add: "Run `dbt docs generate && dbt docs serve` to view the documentation site."

---

## Files in this folder

- `.gitignore`
- `packages.yml`
- `profiles.example.yml`
- `models/staging/_stg__models.yml`
- `models/intermediate/_int__models.yml`
- `models/marts/_marts__models.yml`
- `models/marts/mart_customer_segments.sql` (fixed)
- `models/marts/mart_category_trends.sql` (fixed)
- `models/intermediate/int_customer_monthly_category_spend.sql` (renamed)
- `models/intermediate/int_customer_monthly_spend.sql` (new, correct grain)
- `snapshots/accounts_snapshot.sql`
- `tests/assert_mart_segments_partition.sql`
- `.github/workflows/dbt.yml`
