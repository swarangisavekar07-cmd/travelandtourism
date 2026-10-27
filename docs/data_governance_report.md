# TravelWise — Data Governance & Architecture Report

> **Platform:** TravelWise — India Tourism & Travel Analytics Platform  
> **Reporting Date:** October 2026  
> **Status:** Fully Implemented & Production-Verified  
> **Core Pipeline:** Preserved PySpark ETL & Relational SQL Store

---

## 1. Executive Summary

### 1.1 Purpose of TravelWise
TravelWise is an enterprise Data Engineering and Tourism Analytics platform designed to evaluate macro-level footfall, track longitudinal trajectories, and optimize travel analytics across India. It processes official, multi-year state-wise tourism statistics published by the **Ministry of Tourism, Government of India** (covering calendar years 2018 through 2022) to enable data-driven decision-making for tourism planners, researchers, and travellers.

### 1.2 Architectural Rationale

1. **Why Tourism Data is Processed Through PySpark:**
   - **Distributed Processing & Resilient Transformations:** The raw state-level statistics arrive in wide format (annual observation columns) requiring restructuring into a standardized long format. PySpark executes wide-to-long matrix unpivoting across distributed partitions while enforcing strict typing.
   - **Analytical Windowing:** PySpark's window functions (`Window.partitionBy("state", "category").orderBy("year")`) compute longitudinal Year-over-Year (YoY) growth rates accurately without data-leakage across disparate administrative entities or categories.
   - **Data Quality Assertions:** PySpark provides declarative schema enforcement, preventing malformed records, duplicate natural keys, or invalid categories from entering the lake.

2. **Why SQL is Used to Store Curated Records:**
   - **ACID Transactions & Idempotency:** Relational databases (PostgreSQL 18 in production, with seamless SQLite storage for offline evaluation) provide row-level ACID guarantees.
   - **Constraint & Unique Key Enforcement:** Relational schema constraints (`UNIQUE(state, category, year)`) guarantee that repeat ingestion runs update existing records via upsert rather than duplicating footfall volumes.
   - **High-Performance Querying:** Streamlit dashboard components execute optimized SQL queries with indexes on `state`, `category`, and `year`, ensuring sub-second response times.

3. **How Streamlit Presents Analytics:**
   - Streamlit provides an executive interactive dashboard that queries SQL data with caching (`@st.cache_data`).
   - Visual analytics are rendered via Plotly Express and Plotly Graph Objects with interactive tooltips, legends, and dynamic state-level filters.

### 1.3 Complete Data Flow

```text
┌────────────────────────────────┐
│   Raw Tourism CSV Dataset      │  india_tourism_statewise_2018_2022.csv
│ (Ministry of Tourism, Govt IN) │  [74 rows × 7 columns, Wide Format]
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│      PySpark ETL Engine        │  src/pipeline/tourism_pipeline.py
│  • Schema & Column Validation  │  • Wide-to-Long Unpivot (5x Expansion)
│  • Historical Null Guarding    │  • Aggregate & Estimate Flagging
│  • YoY Window Function Math    │  • Quality Assertions & Anomaly Checks
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│      Curated Parquet Lake      │  data/processed/tourism/
│  Snappy Columnar Compression   │  india_tourism_statewise_normalized.parquet
│  Verified Zero Duplicates      │  [370 rows × 9 columns, Long Format]
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│    Relational SQL Database     │  PostgreSQL 18 / SQLite Store
│  Table: tourism_statewise_     │  Idempotent Upsert (ON CONFLICT DO UPDATE)
│         annual                 │  [370 rows × 12 columns, Indexed Constraints]
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Streamlit Web Application    │  app/main.py
│  • India Tourism Overview      │  • State Explorer (Single-State Deep-Dive)
│  • Detailed State Analytics    │  • Data Quality & Governance Portal
└────────────────────────────────┘
```

### 1.4 Supported Scope vs. Operational Limitations

| Dimension | Implemented & Verified Capabilities | Operational Limitations & Boundaries |
| :--- | :--- | :--- |
| **Temporal Coverage** | 5 complete historical calendar years: 2018, 2019, 2020, 2021, 2022. | Post-2022 data is not part of this historical series; annual granularity only (no daily/monthly granularity). |
| **Geographic Coverage** | 36 distinct administrative entities (28 States + 8 Union Territories) + 1 National aggregate row (`Total India`). | State-level reporting only; destination/city-level statistics are not fabricated from state totals. |
| **Visitor Categories** | Domestic Tourist Visits (DTV) and Foreign Tourist Visits (FTV). | Measures *recorded visits* (tourist arrivals at accommodations/monuments), not unique individual heads. |
| **Database Architecture** | Dual-engine support: PostgreSQL 18 with automatic, seamless fallback to local SQLite (`data/travelwise.db`). | In offline demonstration mode without a live PostgreSQL service, queries execute against SQLite. |
| **Weather Status** | **Excluded from active product workflow** per scope specification. Focus is 100% on India Tourism. | Weather client code remains safely preserved for testing, but is completely removed from the dashboard. |

---

## 2. Complete Technology Stack

The table below reflects the exact, verified versions installed in the project virtual environment (`D:\Travel and tourism\venv`):

| Technology | Verified Version | Architectural Role | Actual Component / File Path |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11.9 (64-bit)` | Core programming runtime | Virtual environment `venv/` |
| **PySpark** | `3.5.1` | Distributed ETL processing, schema validation, wide-to-long unpivoting, YoY windowing | [`src/pipeline/tourism_pipeline.py`](file:///d:/Travel%20and%20tourism/src/pipeline/tourism_pipeline.py), [`src/pipeline/spark_session.py`](file:///d:/Travel%20and%20tourism/src/pipeline/spark_session.py) |
| **Java / JDK** | `Java SE 21.0.12 LTS` | Java Virtual Machine (JVM) executing PySpark worker & driver runtimes | System JDK Runtime (64-bit Server VM) |
| **Pandas** | `2.2.1` | In-memory data manipulation, Streamlit caching, audit scripting | [`app/data_loader.py`](file:///d:/Travel%20and%20tourism/app/data_loader.py), [`scripts/generate_governance_reports.py`](file:///d:/Travel%20and%20tourism/scripts/generate_governance_reports.py) |
| **PyArrow** | `15.0.1` | High-performance columnar Parquet read/write engine | Curated Lake reader in [`app/data_loader.py`](file:///d:/Travel%20and%20tourism/app/data_loader.py) |
| **SQLAlchemy** | `2.0.28` | Object-Relational Mapping (ORM), connection pooling, schema generation, SQL loading | [`src/database/models.py`](file:///d:/Travel%20and%20tourism/src/database/models.py), [`src/database/connection.py`](file:///d:/Travel%20and%20tourism/src/database/connection.py), [`src/database/loader.py`](file:///d:/Travel%20and%20tourism/src/database/loader.py) |
| **PostgreSQL** | `18 Ready` *(psycopg2 2.9.9)* | Primary relational RDBMS for production environments | Production database configured in [`.env`](file:///d:/Travel%20and%20tourism/.env) |
| **SQLite** | `3.x (Standard Library)` | Zero-configuration local relational database store | [`data/travelwise.db`](file:///d:/Travel%20and%20tourism/data/travelwise.db) |
| **Streamlit** | `1.32.2` | Interactive web dashboard framework and UI components | [`app/main.py`](file:///d:/Travel%20and%20tourism/app/main.py), [`app/components/`](file:///d:/Travel%20and%20tourism/app/components/) |
| **Plotly** | `5.20.0` | Interactive charts, multi-line trajectories, ranking bars, and composition donuts | [`app/components/overview.py`](file:///d:/Travel%20and%20tourism/app/components/overview.py), [`app/components/state_explorer.py`](file:///d:/Travel%20and%20tourism/app/components/state_explorer.py) |
| **python-dotenv** | `1.0.1` | Environment variable parsing and `.env` configuration | [`src/database/config.py`](file:///d:/Travel%20and%20tourism/src/database/config.py) |
| **pytest & pytest-cov** | `8.1.1` *(cov 4.1.0)* | Automated unit and integration testing suite | [`tests/`](file:///d:/Travel%20and%20tourism/tests/) (47 passing tests) |
| **Git** | `2.x` | Source code version control and change management | Workspace root repository (`.git/`) |

---

## 3. Data Governance Framework

### 3.1 Data Provenance & Authoritative Lineage
- **Originating Authority:** Market Research Division, **Ministry of Tourism, Government of India**.
- **Official Source Portals:**
  - Research & Analytics Portal: `https://data.tourism.gov.in/rawdata`
  - Official Publications Portal: `https://data.tourism.gov.in/tourismdata`
- **Official Publications Compiled:**
  1. *Tourism Statistics for Year 2019* (Table 5.1.2: State/UT-wise Tourist Visits 2018–19)
  2. *Tourism Statistics for Year 2020* (Table 5.1.2: State/UT-wise Tourist Visits 2019–20)
  3. *Tourism Statistics for Year 2021* (Table 5.1.2: State/UT-wise Tourist Visits 2020–21)
  4. *India Tourism Statistics 2023* (Table 5.1.2: State/UT-wise Tourist Visits 2021–22)
  5. *India Tourism Data Compendium 2024* (Table 4.1.2: State/UT-wise Tourist Visits 2022–23)
- **Local Primary Raw File:** [`data/raw/tourism/india_tourism_statewise_2018_2022.csv`](file:///d:/Travel%20and%20tourism/data/raw/tourism/india_tourism_statewise_2018_2022.csv)
- **Machine-Readable Metadata:** [`data/raw/tourism/metadata_india_tourism_statewise_2018_2022.json`](file:///d:/Travel%20and%20tourism/data/raw/tourism/metadata_india_tourism_statewise_2018_2022.json)
- **Archived Government Source Reports:** Stored locally in [`data/raw/tourism/`](file:///d:/Travel%20and%20tourism/data/raw/tourism/) (`India_Tourism_Statistics_2023.pdf`, `India_Tourism_Data_Compendium_2024.pdf`, and annual `.doc` tables).

### 3.2 Data Ownership & Stewardship (Proposed Roles)

| Role | Proposed Responsibilities | Assigned Individual / Team |
| :--- | :--- | :--- |
| **Data Owner** | Strategic oversight of tourism data validity, compliance with Ministry guidelines, licensing, and usage policies. | Academic Project Lead / TravelWise Platform Author |
| **Data Steward** | Verification of schema standards, metadata maintenance, audit verification, and approval of updates. | Data Engineering Lead |
| **Technical Maintainer** | Pipeline code maintenance, PySpark tuning, database migrations, CI test suite execution, and bug fixes. | Data Platform Engineer |
| **Dashboard Operator** | Presentation layer monitoring, UI accessibility, Streamlit runtime maintenance, and user feedback intake. | Full-Stack BI Developer |

### 3.3 Data Definitions & Analytical Taxonomy

- **Domestic Tourist Visit (DTV):** The recorded arrival of an Indian resident in a State or Union Territory other than their normal place of residence, or within their home state for recreational, cultural, or business purposes, recorded at registered accommodation establishments or designated state entry checkpoints.
- **Foreign Tourist Visit (FTV):** The recorded arrival of a foreign national / international traveller in a specific Indian State or Union Territory during the calendar year.
- **Critical Distinction: Visits vs. Unique Visitors:** The dataset reports **total visit counts (footfall volume)**, not unique individual humans. A single individual visiting three different states in one calendar year generates three distinct visit records.
- **State / Union Territory:** One of the 36 constitutional administrative entities of the Republic of India (28 States and 8 Union Territories).
- **Total India Aggregate Record:** A consolidated national summary row published officially by the Ministry of Tourism. It represents the national sum and is strictly flagged with `is_aggregate = True` to isolate it from state-level summations.
- **Estimated Record:** Certain figures (specifically 2022 figures for Maharashtra and Delhi) were officially estimated by the Ministry of Tourism by applying national growth rates to their 2019 base data. These records are explicitly flagged with `is_estimated = True`.
- **Historical Null Record:** A record where data is genuinely absent due to constitutional reorganization (specifically Ladakh in 2018, before its establishment under the Jammu and Kashmir Reorganisation Act, 2019). It is strictly stored as `NULL` and distinguished from 0.

### 3.4 Data Integrity & Enforcement

1. **Natural Key Constraint:** The triple `(state, category, year)` uniquely identifies each historical observation. Verified: **0 duplicate records** across raw, curated, and SQL stores.
2. **Type Enforcement:** Visit counts are stored as `BigInteger` (or `BIGINT`), preventing precision loss from integer overflow. Years are constrained to `INTEGER`.
3. **Domain Sanity Checks:** All recorded visits must satisfy `visit_count >= 0` or be strictly `NULL`. Verified: **0 negative records**.
4. **Aggregate Isolation Policy:** To prevent 2x double counting, all analytical aggregation queries in the platform strictly enforce:
   ```sql
   WHERE is_aggregate = FALSE
   ```
   National totals are retrieved either by filtering `WHERE is_aggregate = TRUE` or summing state rows directly.

### 3.5 Security & Credential Management

- **Zero Hardcoded Secrets:** No database passwords, tokens, or private credentials are hardcoded in application logic or checked into version control.
- **Environment Separation:** Database credentials are read dynamically via `python-dotenv` from local `.env` files ([`.env.example`](file:///d:/Travel%20and%20tourism/.env.example) serves as a template).
- **Git Safeguards:** [`.gitignore`](file:///d:/Travel%20and%20tourism/.gitignore) actively excludes:
  - `.env` files
  - `venv/` virtual environment
  - `__pycache__/` and `.pytest_cache/`
  - Temporary files and runtime logs
- **Local Fallback Security:** When PostgreSQL is not configured, the platform safely initializes a local, file-based SQLite database at `data/travelwise.db`, avoiding exposure of unauthenticated network endpoints.

### 3.6 Data Retention & Reproducibility

- **Curated Lake Immutability:** Curated Parquet files are generated deterministically by the PySpark pipeline. Rerunning `python -m src.pipeline.run_tourism_pipeline` will re-process raw files and output identical Parquet lakes.
- **Quality Audit Tracking:** Quality metrics and reconciliation logs are saved alongside datasets in [`data/processed/tourism/quality_report.json`](file:///d:/Travel%20and%20tourism/data/processed/tourism/quality_report.json) and [`docs/data_quality_report.md`](file:///d:/Travel%20and%20tourism/docs/data_quality_report.md).
- **Audit Verification Command:** The governance and quality audit can be executed at any time using:
  ```powershell
  python scripts/generate_governance_reports.py
  ```
