# cba-feature-store — fix plan

This repo has the most consequential issues. Apply ALL of these before
showing this to anyone — the leakage bug + AUC=1.00 claim is the single
biggest credibility risk in the whole portfolio.

---

## 1. Kill the target leakage (CRITICAL)

**Problem.** `is_high_risk` is computed in `compute_features.py` as a
deterministic rule on `max_transaction_value`, `night_transaction_ratio`,
`online_transaction_ratio`. Then `train_model.py` uses those same columns
as input features to predict `is_high_risk`. The model is being asked to
re-derive a rule it was handed. That's why AUC = 1.00.

**Fix.** Drop in `compute_features.py` from this folder. Changes:
- Labels now come from an EXTERNAL signal: the `fraud.flagged_transactions`
  table populated by `cba-fraud-streaming`. Any account with ≥1 flagged
  txn in the window is positive.
- Connects the streaming repo and the ML repo into one story. This is the
  same fix that turns four disconnected repos into one project.

Expected outcome: realistic AUC in 0.7–0.9 range.

---

## 2. Fix the misnamed `_7d` features

**Problem.** `transaction_count_7d` and `total_spend_7d` aggregate the
*entire* dataset, not 7 days.

**Fix.** Drop-in `compute_features.py` filters to `max_date - 7 days` first.
The names now match reality.

---

## 3. Fix `avg_daily_spend` denominator

**Problem.** Hardcoded `/ 180`.

**Fix.** Drop-in uses `total_spend / observed_days_per_account` (computed
per account from min/max transaction_date).

---

## 4. Fix `event_timestamp` (Feast point-in-time correctness)

**Problem.** All rows get `datetime.now()`. Kills Feast's whole point.

**Fix.** Drop-in sets `event_timestamp = last_transaction_date_per_account`.
Now point-in-time joins are correct: at training time, you only see features
known *as of* that account's last observed activity.

---

## 5. Remove the hardcoded absolute path

**Problem.** `/Users/vivianayou/projects/cba-banking-pipeline/...` is in the
committed code. Nobody else can run it.

**Fix.** Drop-in takes `--transactions`, `--flagged`, `--out` as CLI args.

---

## 6. Make serving actually use Feast + MLflow

**Problem.** `fraud_api.py` says "using Feast feature store" but actually
reads the parquet directly. Also: trains an ML model in `train_model.py`,
logs it to MLflow, then ignores it at serving time and applies hand-coded
rules.

**Fix.** Drop in `fraud_api.py` from this folder. Now:
- Loads features via `store.get_online_features(...)` (real Feast)
- Loads the registered MLflow model at startup via model URI
- Returns a model probability, not a rule-based score
- Falls back to a "Unknown account" branch with a clearly-labeled baseline

This single change is what makes the repo a "feature store + ML serving
demo" instead of "two unrelated scripts in the same repo."

---

## 7. Register the model in MLflow Model Registry

**Problem.** `train_model.py` logs the model as an artifact, never registers
it. Serving can't pin a specific version.

**Fix.** Drop in `train_model.py`. Changes:
- Registers the model under name `cba_fraud_model`
- Transitions the new version to "Staging" automatically
- Includes a baseline LogisticRegression for comparison
- 5-fold CV instead of single split
- `class_weight='balanced'`

---

## 8. Flatten `feature_repo/feature_repo/`

**Problem.** Nested duplicate path is a `feast init` artifact.

**Fix.** Restructure to:
```
feature_repo/
  feature_store.yaml
  feature_definitions.py
  data/
```

Update import paths in serving + training accordingly. Update
`feature_definitions.py` to add a `FeatureService` (in this folder) so the
model has a versioned contract on its inputs.

---

## 9. Tests + CI

**Fix.** Drop in:
- `tests/test_compute_features.py` — verifies no leakage (asserts label
  column doesn't predict label perfectly when only using non-leakage
  features) and that all the windowing math is correct on a tiny fixture.
- `.github/workflows/ci.yml` — ruff + pytest + a smoke test that boots the
  FastAPI app against fixture features and hits `/score`.

---

## 10. README rewrite

**Problem.** README claims **AUC = 1.00** and "night ratio = 76% importance"
— both are direct artifacts of the leakage bug. Any reviewer who knows ML
will spot this in 30 seconds. The biggest specific change you need to make.

**Fix.** Drop in `README.md` from this folder. Honest framing:
- "Demonstrates the Feast + MLflow + FastAPI pattern end-to-end"
- Reports realistic metrics from the fixed pipeline
- Explicitly calls out: "Labels come from the streaming fraud engine in
  cba-fraud-streaming. This decouples feature definition from label
  definition and is what makes the model trainable."

---

## Files in this folder

- `compute_features.py` (fixed — already drafted)
- `fraud_api.py` (uses Feast + MLflow)
- `train_model.py` (CV + Registry + baseline)
- `feature_definitions.py` (adds FeatureService)
- `tests/test_compute_features.py`
- `ci.yml`
- `README.md`
