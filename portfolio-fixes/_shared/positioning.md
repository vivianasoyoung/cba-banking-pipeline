# Positioning: Data Engineer (primary) + ML Engineering (AI angle)

Reusable narrative for LinkedIn, GitHub profile README, resume summary, and
interview intros. Keep the story identical everywhere — consistency reads as
clarity of direction.

---

## The core narrative (memorise this arc)

> Insight Analyst who lived downstream of data pipelines — felt the pain of
> stale data, broken dashboards, undocumented tables — and is now an engineer
> who builds the reliable pipelines that serve people like me. Backing it with
> a Master of Computer Science (AI), which lets me bridge data engineering and
> machine learning.

Three beats:
1. **Where I came from** — analyst, SQL/Python, banking domain (consumer of data)
2. **Where I'm going** — data engineer (builder of data systems)
3. **My edge** — AI master's + an end-to-end project that spans ingestion → transformation → streaming → ML serving

---

## LinkedIn headline (pick/adapt one)

- "Insight Analyst → Data Engineer | SQL · Python · dbt · Airflow · Kafka | MSc Computer Science (AI)"
- "Data Engineer in the making | building reliable data + ML pipelines | analyst background, AI master's"

## LinkedIn / resume summary (3-4 lines)

> Data professional transitioning from insight analytics into data engineering.
> 1.5 years turning data into decisions at one of Australia's largest banks; now
> building the pipelines and infrastructure that make that data reliable. Recently
> built an end-to-end banking data platform (Airflow, dbt, Kafka, Feast, MLflow,
> FastAPI) with tests and CI across four repositories. Completing a Master of
> Computer Science (AI), bridging data engineering and machine learning.

## GitHub profile README (short)

> 👋 Insight Analyst → Data Engineer. I build reliable data + ML pipelines.
> Currently: MSc Computer Science (AI). Background: analytics in banking.
> Featured project: an end-to-end banking data platform — see the four repos below.

---

## How each repo maps to the DE + ML story

Use this when someone asks "walk me through your project."

| Repo | Primary signal | Angle |
| --- | --- | --- |
| cba-banking-pipeline | Batch ingestion, orchestration, data quality | **Core DE** |
| cba-dbt-analytics | Transformation, testing, modelling, cloud warehouse (BigQuery) | **Core DE / Analytics Engineering** |
| cba-fraud-streaming | Real-time streaming, event processing | **Core DE** |
| cba-feature-store | Feature store, model training, serving | **The AI/MLE bridge** ← lead with this for ML-leaning roles |

For **DE roles**: lead with the pipeline + dbt + streaming repos; mention the
feature store as "I also handle the data layer that ML sits on."

For **ML Engineer roles**: lead with the feature store + the labels-from-streaming
design decision; frame the other three as "the data foundation I built it on."

Same portfolio, two emphases. Read the job description and lead accordingly.

---

## Interview talking points (your strongest, most-defensible material)

1. **The transition story** (why DE): "As an analyst I was the customer of bad
   data. I learned to build the systems that prevent those failures — with
   engineering practices like testing, CI, and idempotency."

2. **The design decision** (depth): "I source ML labels from my streaming fraud
   engine, not from the same features the model trains on — because deriving the
   label from the features causes target leakage. My first version scored AUC 1.00,
   which was the tell. I fixed it and wrote a regression test so it can't come back."

3. **Engineering rigor** (what analysts usually lack): "Every repo has CI. My dbt
   project runs 43 data tests against a real warehouse on every push. CI caught
   four real bugs I'd missed."

4. **The AI angle** (your differentiator): "My master's is in AI, so I'm
   comfortable on both sides of the ML/data boundary — the feature store repo is
   where those meet."

5. **Production judgment** (seniority signal): "I documented what I'd change at
   scale — Redis-backed velocity tracking, a schema registry, exactly-once
   semantics. I know the difference between a demo and production."

---

## Where to apply this angle (Australia / CBA context)

- **Internal CBA data engineering teams** — you know the domain, data, and stack.
  Often the lowest-friction path. Worth a direct conversation.
- **External DE roles** — lead with DE framing, AI as a bonus.
- **ML Engineer / MLOps roles** — lead with the feature store + AI master's; less
  saturated than junior Data Scientist, and rewards the engineering rigor you show.
- **Avoid** framing yourself as a junior Data Scientist — that market is
  oversaturated and your strengths (engineering + data + domain) are wasted there.
