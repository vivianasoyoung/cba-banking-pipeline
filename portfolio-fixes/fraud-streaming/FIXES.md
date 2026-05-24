# cba-fraud-streaming — fix plan

Apply in this order.

---

## 1. Fix the broken producer docstring (CRITICAL)

**Problem.** `producer/transaction_producer.py` line 1 starts with `transaction_producer.py` — there is **no opening `"""`**. The file is syntactically wrong and `python -c "import producer.transaction_producer"` will throw `NameError`.

**Fix.** Drop in `transaction_producer.py` from this folder. Adds the missing `"""`, plus:
- UTC timestamps (`datetime.now(timezone.utc)`)
- Keys Kafka messages by `account_id` so all txns for an account land on one partition (essential for the velocity rule to be correct under multiple consumers)
- Configurable broker via env var
- Real rapid-fire bursts (no sleep between rapid-fire messages)
- JSON Schema validation before send

---

## 2. Add idempotency to the consumer

**Problem.** A retry on `save_flagged_transaction` duplicates rows. There's no UNIQUE constraint on `transaction_id`.

**Fix.**
1. Update `docker/init.sql` (in this folder) to add `UNIQUE(transaction_id)` and a `processed_at` column.
2. Update the consumer's INSERT to use `ON CONFLICT (transaction_id) DO NOTHING`.

---

## 3. Manual offset commits + dead-letter topic

**Problem.** Default auto-commit can mark a message consumed *before* the DB write succeeds — silent data loss on crash. One malformed JSON message crashes the entire loop.

**Fix.** Drop in `consumer/fraud_consumer.py`. Changes:
- `enable_auto_commit=False`, commit explicitly after DB success
- Try/except around every message; failures go to `transactions.dlq`
- Connection pool (psycopg2.pool.SimpleConnectionPool) instead of connect-per-write
- Schema validation via Pydantic
- Persists `event_time` (from txn) AND `processed_at` (from now)

---

## 4. Containerize the Python services

**Problem.** Producer and consumer run on the host. Compose only boots Kafka/Postgres. Not portable.

**Fix.** Drop in:
- `Dockerfile.producer`
- `Dockerfile.consumer`
- `requirements.txt`
- Updated `docker-compose.yml` (additions noted in `docker-compose.diff`)

Now `docker compose up` boots the entire pipeline end-to-end.

---

## 5. Remove dead code

**Problem.** `fraud.transaction_velocity` table is created in `init.sql` but never written to. Misleads readers.

**Fix.** Either implement persistent velocity tracking (out of scope here) or delete the table from `init.sql`. The drop-in `init.sql` deletes it.

---

## 6. Refactor the risk score into a rules table

**Problem.** Detection rules and scoring weights are scattered across `detect_fraud` and `calculate_risk_score`. Adding a rule requires editing two places.

**Fix.** Drop-in consumer has a single `RULES` list of `(predicate, label, points)` tuples. One place to add rules, one place to read scoring weights.

---

## 7. Add a smoke test + CI

**Problem.** No tests. No CI.

**Fix.** Drop in:
- `tests/test_rules.py` — pure-Python unit tests for each fraud rule (no Kafka, no Postgres)
- `.github/workflows/ci.yml` — runs ruff + pytest

The unit tests would catch the missing docstring bug for free.

---

## 8. README updates

- Note: "Run `docker compose up` to start the entire pipeline including producer + consumer."
- Add the cross-repo overview section (see `_shared/portfolio-overview.md`).
- Be explicit: "In-memory velocity tracking is for demo only; production would use Redis or Kafka Streams. See REAL_WORLD_NOTES.md."
- Add `REAL_WORLD_NOTES.md` (in this folder) — shows you know what would be different in prod. This is a high-signal artifact for interviews.

---

## Files in this folder

- `transaction_producer.py` (fixed)
- `fraud_consumer.py` (fixed)
- `docker/init.sql` (UNIQUE + processed_at, drops dead velocity table)
- `requirements.txt`
- `Dockerfile.producer`
- `Dockerfile.consumer`
- `docker-compose.diff`
- `tests/test_rules.py`
- `ci.yml`
- `REAL_WORLD_NOTES.md`
