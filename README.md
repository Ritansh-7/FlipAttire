# FlipAttire

### Fashion discovery, personalized recommendations, and experimentation — in one platform.

[![CI](https://github.com/Ritansh-7/FlipAttire/actions/workflows/ci.yml/badge.svg)](https://github.com/Ritansh-7/FlipAttire/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

FlipAttire is a production-minded fashion recommendation and experimentation platform for a realistic retail workflow. It combines a FastAPI recommendation service, Next.js storefront, Streamlit apps, event tracking, A/B experimentation, Spark pipelines, and observability tooling.

> **The idea:** every shopper should see a more relevant, more diverse, and more measurable product experience.

---

## Why FlipAttire stands out

| Capability | What it delivers |
| --- | --- |
| **Personalized ranking** | Blends popularity, department affinity, recent actions, colour affinity, and similar-item signals. |
| **Experiment-ready by design** | Stable customer-level A/B assignment keeps control and treatment comparisons trustworthy. |
| **Production-style event loop** | Captures impressions, views, clicks, carts, purchases, and returns through one event interface. |
| **Fast serving** | FastAPI endpoints with compact columnar customer profiles and local serving. |
| **Retail analytics** | Seven-day attribution windows and exposure-aware conversion reporting. |
| **Full-stack demo** | Storefront, operations console, REST API, Spark, Kafka, Prometheus, and Grafana. |
| **Practical engineering** | Docker Compose, Windows launchers, automated tests, and GitHub Actions CI. |

## Product flow

1. A shopper browses the storefront.
2. The recommender assigns a stable experiment variant.
3. Products are ranked using the baseline or personalized strategy.
4. Impressions and downstream actions are recorded.
5. The operations console exposes live activity and experiment results.
6. New ranking ideas can be evaluated with time-based holdouts.

## Architecture

```text
                         +----------------------+
                         |  Next.js storefront  |
                         +----------+-----------+
                                    |
                         +----------v-----------+
                         | FastAPI recommender  |
                         | ranking + experiments|
                         +----+------------+----+
                              |            |
                     events   |            | metrics
                              v            v
                    +---------+--+   +-----+---------+
                    | Kafka / log |   | Prometheus    |
                    +------------+   | + Grafana     |
                                     +---------------+

        H&M-format data -> Spark ingest -> artifacts -> serving snapshots
        Streamlit customer app + Streamlit operations console
```

## Recommendation engine highlights

- **Control arm:** popularity-ranked recommendations for an interpretable baseline.
- **`hybrid_v2` treatment:** combines popularity with recent shopper feedback, department affinity, colour affinity, and similar-item signals.
- **Diversity and eligibility rules:** avoids unavailable or already-purchased items and reduces repetitive results.
- **Stable assignment:** the same customer remains in the same experiment variant.
- **Exposure-aware attribution:** actions count only after a matching customer/product exposure within seven days.
- **Leakage-aware evaluation:** offline evaluation uses an earlier training window and a later time-based holdout.

## Quick start: API

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
uvicorn hm_recommender.api:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive API explorer.

Try a recommendation:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/v1/recommendations?customer_id=C001&surface=homepage&limit=5"
```

Record an event:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"event_type":"click","customer_id":"C001","article_id":"A001","surface":"homepage"}' `
  -Uri "http://127.0.0.1:8000/v1/events"
```

## Run the Streamlit applications

Install UI dependencies:

```powershell
python -m pip install -e ".[ui]"
```

Run in separate terminals:

```powershell
.\run_user_streamlit.ps1   # customer experience: http://localhost:8501
.\run_admin_streamlit.ps1  # operations console: http://localhost:8502
```

The customer app supports browsing, recommendations, impressions, clicks, carts, purchases, and returns. The operations console shows live events, A/B metrics, evaluation status, Kafka UI, Prometheus, and Grafana links.

## Run the Next.js storefront

The storefront lives in [`my-clothing-store/`](my-clothing-store/).

```powershell
cd my-clothing-store
Copy-Item .env.template .env.local
corepack enable
yarn install
yarn dev
```

The storefront expects a running Medusa backend. Configure `.env.local`; never commit that file or API keys.

## Data and model pipeline

FlipAttire supports H&M-format catalog files and a Spark workflow:

```powershell
spark-submit scripts/spark_ingest_hm.py `
  --transactions "C:\path\to\transactions_train.csv.zip" `
  --customers "C:\path\to\customers.csv.zip" `
  --articles "C:\path\to\articles.csv.zip"

spark-submit --conf spark.driver.memory=4g scripts/spark_train.py
spark-submit --conf spark.driver.memory=4g scripts/spark_evaluate.py
```

The evaluator reports macro Recall@K, Precision@K, and hit rate on a time-based holdout. The personalized strategy remains a ranking hypothesis until validated against a leakage-safe comparison.

For Windows D-drive setups:

```powershell
. .\scripts\set_spark_env.ps1
```

## Local infrastructure

```powershell
docker compose up -d
```

Optional services:

```powershell
docker compose --profile event-streaming-ui --profile observability up -d
docker compose --profile data-services up -d
```

Native Windows observability is available without Docker:

```powershell
.\start_native_stack.ps1
```

| Service | URL |
| --- | --- |
| API docs | `http://localhost:8000/docs` |
| API metrics | `http://localhost:8000/metrics` |
| Kafka UI | `http://localhost:8080` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

Stop the native stack with `.\stop_native_stack.ps1`.

## Quality gates

GitHub Actions runs on pushes to `main` and on pull requests:

- Python package installation and `pytest` suite
- Next.js dependency installation
- TypeScript type-checking

Run the core checks locally:

```powershell
python -m pytest -q tests
cd my-clothing-store
corepack yarn tsc --noEmit
```

The full Next.js production build requires a reachable Medusa backend because some pages fetch catalog data during static generation.

## Project structure

```text
FlipAttire/
├── src/hm_recommender/       # recommendation, experiments, events, API
├── tests/                    # automated Python tests
├── my-clothing-store/       # Next.js storefront
├── app_pages/                # Streamlit pages
├── scripts/                  # ingestion, training, evaluation
├── infra/                    # Kafka, Prometheus, Grafana, SQL
├── docker-compose.yml        # local production-like stack
└── .github/workflows/        # CI automation
```

## Current scope

FlipAttire is a strong local prototype and experimentation foundation. The API currently serves primarily from memory; PostgreSQL and ClickHouse schemas are integration starting points. Durable event storage, production feature serving, orchestration, and automated deployment are natural next steps.

## Security note

Secrets, generated service data, caches, build output, downloads, and user/account data are intentionally excluded from Git. Use environment variables or a secrets manager for API keys and credentials.

## License

This project is released under the [MIT License](LICENSE).

