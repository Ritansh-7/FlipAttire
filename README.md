# FlipAttire

An open-source fashion recommendation and experimentation platform. FlipAttire uses H&M-format catalog data for its local demo.

## First milestone

- Deterministic customer-level A/B assignment
- Popularity baseline recommendations
- Personalized recommendations using popularity, department affinity, weighted recent shopper actions, color affinity, and similar-item signals
- Eligibility and diversity policies
- Recommendation exposure logging
- FastAPI service with health, recommendation, and event endpoints

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn hm_recommender.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API explorer.

## API examples

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/v1/recommendations?customer_id=C001&surface=homepage&limit=5"
Invoke-RestMethod -Method Post -ContentType "application/json" -Body '{"event_type":"click","customer_id":"C001","article_id":"A001","surface":"homepage"}' -Uri "http://127.0.0.1:8000/v1/events"
```

The built-in fallback data is intentionally small and synthetic. The repository also includes a local H&M-format Parquet ingestion and model-artifact workflow. Online API state is still primarily in memory; PostgreSQL and ClickHouse schemas are starting points, not yet the API's backing stores. The serving process keeps customer top-department profiles in a compact, sorted columnar index and looks them up without copying the 1.3M-customer pool into Python dictionaries/lists. Hybrid ranking scores use log-scaled signals so high-volume popularity counts do not automatically swamp a shopper's recent interests, with stronger and more recent actions receiving more weight. The control arm remains popularity-only. The updated treatment runs as `hybrid_v2` in a new experiment ID so results from the earlier algorithm are not combined with it; customer assignment remains stable within each experiment. The experimental bandit selector is diagnostic-only and does not route live recommendation traffic.

## Ingest the provided H&M files

```powershell
spark-submit scripts/spark_ingest_hm.py `
  --transactions "C:\Users\ritan\OneDrive\Desktop\New folder\Downloads\transactions_train.csv.zip" `
  --customers "C:\Users\ritan\OneDrive\Desktop\New folder\Downloads\customers.csv.zip" `
  --articles "C:\Users\ritan\OneDrive\Desktop\New folder\Downloads\articles.csv.zip"
```

The ZIP is staged, then Spark reads, casts, partitions, and writes the tables under `data/bronze/`. For a cluster, replace `--master local[*]` with the Spark cluster master URL.

## Build serving artifacts and evaluate the popularity baseline

```powershell
spark-submit --conf spark.driver.memory=4g scripts/spark_train.py
spark-submit --conf spark.driver.memory=4g scripts/spark_evaluate.py
```

`spark_train.py` builds serving snapshots from all available transaction history. `spark_evaluate.py` separately uses an earlier training window and a recent time-based holdout to measure the global-popularity baseline; it reports macro Recall@K, Precision@K, and hit rate for customers' novel purchases. This evaluator does not yet compare the personalized hybrid model, so `hybrid_v2` is an improved ranking hypothesis, not a proven offline or online uplift. The API does not present online event logs as offline ranking metrics because they are not a leakage-safe holdout.

`train_baseline.py` and `evaluate_baseline.py` remain as lightweight Polars utilities for local artifact inspection. The authoritative ingestion, training, and evaluation path is PySpark.

For a containerized Spark batch runner, build `Dockerfile.spark`; it includes Java 17 and the PySpark runtime. The API image intentionally does not install Spark because serving and distributed batch processing are separate production workloads.

### Windows D-drive Spark environment

```powershell
. .\scripts\set_spark_env.ps1
spark-submit.cmd --master local[*] --conf spark.driver.memory=4g scripts/spark_ingest_hm.py ...
spark-submit.cmd --master local[*] --conf spark.driver.memory=4g scripts/spark_train.py
spark-submit.cmd --master local[*] --conf spark.driver.memory=4g scripts/spark_evaluate.py
```

The source ZIPs can remain read-only on C:. All installation, staging, temporary Spark files, Parquet outputs, and model artifacts are on D:.

## Start the local production-like infrastructure

```powershell
docker compose up -d
```

The default stack starts only the recommender API and Kafka. Kafka UI, the unconnected data-service prototypes (PostgreSQL, ClickHouse, Redis, Qdrant, MinIO, and MLflow), and Prometheus/Grafana are opt-in so a normal local run uses fewer containers and less memory.

Start optional services only when you need them:

```powershell
docker compose --profile event-streaming-ui --profile observability up -d
docker compose --profile data-services up -d
```

The application remains independently deployable; Feast, KServe, Airflow, and GrowthBook are future integrations, not requirements for the local app.

For Kafka publishing, install the production extra and set `KAFKA_BOOTSTRAP_SERVERS`. Without Kafka configured, the API uses a no-op bus for local tests while retaining the same event interface. The A/B report attributes clicks, cart additions, and purchases to the same customer/product impression and variant within a seven-day window. Its two-arm significance test excludes customers exposed to multiple variants and is suppressed for multi-treatment experiments. This remains a local prototype report and is not a substitute for durable, audited production experiment analytics.

In Docker Compose, containers connect to Kafka at `kafka:9092`; host processes connect at `localhost:9094`. The Compose recommender is configured to load the `hm_spark_v1` artifacts produced by the Spark scripts.

## Two live Streamlit applications

Run the customer storefront and operations console in separate terminals:

```powershell
.\run_user_streamlit.ps1   # http://localhost:8501
.\run_admin_streamlit.ps1  # http://localhost:8502
```

The user app provides category browsing, local product visuals, recommendations, impressions, clicks, cart, purchase and return events. The admin app reads the shared durable event log at `data/events/events.jsonl` and displays live events, A/B metrics, model evaluation status, Kafka UI, Prometheus and Grafana links.

Start the technical services with:

```powershell
docker compose --profile event-streaming-ui --profile observability up -d kafka kafka-ui prometheus grafana
```

The launchers force Streamlit, Python, Spark and pip temporary/cache paths to `D:\gt`; they also disable usage-stat collection and cap BLAS threads to prevent C: drive growth and OpenBLAS memory exhaustion.

## Native Windows observability stack (no Docker)

```powershell
.\start_native_stack.ps1
```

This starts Kafka/KRaft, Redpanda Console, Prometheus, Grafana, and the FastAPI metrics endpoint using only binaries under `D:\gt\tools` and data under `D:\gt\data`:

- Kafka UI: `http://localhost:8080`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `hmadmin`)
- API metrics: `http://localhost:8000/metrics`

Stop everything with `.\stop_native_stack.ps1`. The first Kafka start formats a single-node KRaft data directory under `D:\gt\data\kafka-logs`.
