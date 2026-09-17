# 🌍 Global News Intelligence Lakehouse

End-to-end Databricks lakehouse for global news-event analytics, anomaly detection, and retrieval-augmented intelligence using GDELT data.

## Overview

This project ingests GDELT global event data into a governed Bronze/Silver/Gold lakehouse, engineers country-level temporal features, detects unusual event-volume behavior with an Isolation Forest model, and exposes results through a Databricks App.

A separate RAG path indexes extracted news-document chunks with Databricks AI Search and uses retrieved context with Meta Llama 3.3 70B Instruct to answer questions about indexed news content.

## Architecture

```mermaid
flowchart TD
    A[GDELT Event Data] --> B[Bronze]
    B --> C[Silver validation + deduplication]
    C --> D[Gold refined analytics]
    D --> E[Country-day ML features]
    E --> F[Isolation Forest]
    F --> G[MLflow Tracking]
    G --> H[Unity Catalog Model Registry]
    H --> I[Databricks Model Serving]
    F --> J[Anomaly Results]
    J --> K[Databricks App - Anomaly Monitor]

    L[News URLs / Documents] --> M[Text extraction]
    M --> N[Chunking]
    N --> O[workspace.gold.news_chunks]
    O --> P[Databricks AI Search]
    P --> Q[Top-K retrieved chunks]
    Q --> R[Meta Llama 3.3 70B Instruct via ai_query()]
    R --> S[Databricks App - News Intelligence RAG]

    T[Lakeflow Job] --> B
    T --> C
    T --> D
    T --> E
    T --> F
    U[Declarative Automation Bundle] --> T
```

## Databricks Components

- Unity Catalog
- Delta Lake
- Lakeflow Jobs
- Databricks Declarative Automation Bundles
- MLflow Tracking
- Unity Catalog Model Registry
- Databricks Model Serving
- Databricks AI Search
- Databricks Apps
- Serverless SQL / compute

## Data Engineering

### Bronze
Raw GDELT Event Database files are ingested into Delta tables while preserving source fidelity.

### Silver
Records are validated and cleaned, including duplicate-event handling, tolerant numeric parsing, geographic validation, and date checks.

### Gold
Curated event data is aggregated into country/day analytics and ML-ready features.

Verified prototype metrics:
- **1,217,961 clean GDELT event records**
- **0 duplicate GlobalEventID values after cleanup**
- **2,640 country/day ML feature rows**

## Machine Learning

An unsupervised `IsolationForest` detects unusual country-level event-volume behavior using engineered temporal and activity features.

Verified test results:
- **427 test observations**
- **24 anomalies**
- **5.62% anomaly rate**

Registered model:

`workspace.gold.gdelt_isolation_forest`

The model was tracked with MLflow, registered in Unity Catalog, deployed through Databricks Model Serving, and successfully invoked through its REST endpoint.

## Retrieval-Augmented Generation

A separate RAG path processes news documents into chunks and indexes them with Databricks AI Search.

AI Search configuration:
- Index: `workspace.gold.news_chunks_index`
- Source table: `workspace.gold.news_chunks`
- Index type: Delta Sync
- Search mode: Hybrid
- Embedding model: `databricks-gte-large-en`
- Indexed chunks: **765**

RAG flow:
1. User submits a question.
2. Databricks AI Search retrieves relevant chunks.
3. Retrieved chunks are assembled into grounded context.
4. `system.ai.meta-llama-3-3-70b-instruct` generates the answer through `ai_query()`.
5. The answer is displayed in the Databricks App.

## Databricks App

The deployed app contains two working views:

- **🔎 Anomaly Monitor** — displays anomalous country/day news activity.
- **💬 News Intelligence RAG** — answers questions over indexed news-document chunks.

## Orchestration

The core workflow is orchestrated as a Lakeflow Job:

```text
bronze_ingestion
      ↓
silver_validation
      ↓
gold_refined
      ↓
gold_features
      ↓
anomaly_model
```

Verified runs:
- Manual Lakeflow run: **3m 59s**
- Bundle-managed run: **6m 57s**
- All five tasks completed successfully on serverless compute.

## Deployment as Code

The repository contains a `databricks.yml` Declarative Automation Bundle defining the Lakeflow Job and task dependencies.

```bash
databricks bundle validate
databricks bundle deploy
databricks bundle run gdelt_news_intelligence_pipeline
```

## Repository Structure

```text
global-news-intelligence-lakehouse/
├── app/
│   ├── app.py
│   ├── app.yaml
│   └── requirements.txt
├── notebooks/
│   ├── 01_gdelt_bronze_ingestion.ipynb
│   ├── 02_gdelt_silver_validation.ipynb
│   ├── 03_gdelt_gold_refinedData.ipynb
│   ├── 03_gdelt_gold_features(acc to gpt).ipynb
│   ├── 04_gdelt_anomaly_model.ipynb
│   └── ...
├── docs/img/..
└── databricks.yml
```

## Screenshots to Include

Add these under `docs/images/`:
1. `lakeflow-job-success.png`
2. `anomaly-monitor.png`
3. `rag-assistant.png`
4. You can add more to make it more credible..

Then embed the strongest three:

```markdown
![Lakeflow Job](docs/images/lakeflow-job-success.png)
![Anomaly Monitor](docs/images/anomaly-monitor.png)
![RAG Assistant](docs/images/rag-assistant.png)
```

## Tech Stack

Python · PySpark · SQL · Delta Lake · Databricks · Unity Catalog · Lakeflow Jobs · MLflow · scikit-learn · Isolation Forest · Databricks Model Serving · Databricks AI Search · Vector Search · RAG · Meta Llama 3.3 70B Instruct · Streamlit · GitHub
