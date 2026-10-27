# TravelWise — India Tourism Analytics Platform

TravelWise is an enterprise Data Engineering and Tourism Analytics platform designed to evaluate and visualize tourism patterns across India. It processes official state-wise tourism statistics published by the **Ministry of Tourism, Government of India** (2018–2022) through a robust PySpark ETL pipeline, stores normalized records in a relational database, and presents multi-dimensional insights through an executive Streamlit dashboard.

---

## Architecture & Data Flow

```text
Raw Tourism CSV Dataset (Ministry of Tourism)
                  │
                  ▼
   PySpark Longitudinal ETL Pipeline
 (Unpivot, Schema Constraints, YoY Windowing)
                  │
                  ▼
       Curated Parquet Lake
(india_tourism_statewise_normalized.parquet)
                  │
                  ▼
      Relational SQL Database
   (PostgreSQL 18 / SQLite Store)
                  │
                  ▼
  Streamlit Executive Analytics Platform
(India Overview, State Explorer, Governance)
```

---

## 📚 Governance & Quality Documentation Suite

Comprehensive audit trails, architecture diagrams, data dictionaries, and execution reports are maintained in the [`docs/`](docs/) directory:

1. **[Data Governance Report](docs/data_governance_report.md):** Provenance, data ownership, taxonomy, schema integrity, and security policies.
2. **[Data Quality Report](docs/data_quality_report.md):** Multi-dimensional quality matrix (Completeness, Validity, Uniqueness, Consistency, Accuracy, Timeliness, Referential Integrity, Transformation Integrity) with live query evidence.
3. **[ETL Execution & Reconciliation Report](docs/etl_execution_report.md):** Detailed stage-by-stage execution sequence (Extract, Transform, Curated Lake, SQL Load, Streamlit), row-count reconciliation, and repeat-run idempotency logs.
4. **[End-to-End Data Lineage](docs/data_lineage.md):** Full Mermaid visual lineage mapping data journey from Ministry publications to dashboard views.

---

## Technologies Used

- **Python 3.11.9 (64-bit)**: Core programming language runtime.
- **Streamlit 1.32.2**: Interactive analytics dashboard and user interface.
- **Plotly Express & Graph Objects 5.20.0**: Interactive time-series trajectories, multi-state benchmarks, and distribution charts.
- **PySpark 3.5.1**: Scalable ETL transformations, wide-to-long normalization, window functions, and schema validation.
- **Java / JDK 21.0.12 LTS**: Java Virtual Machine (JVM) executing PySpark driver and worker routines.
- **Pandas 2.2.1 & PyArrow 15.0.1**: Columnar Parquet lake reading and analytical transformations.
- **PostgreSQL 18 & SQLAlchemy 2.0.28**: Relational database storage with schema constraints, indexing, and upsert logic.
- **SQLite 3.x**: Local relational database engine for zero-configuration SQL execution.
- **pytest & pytest-cov 8.1.1**: Automated testing suite (100% passing tests).

---

## Project Structure

```text
TravelWise/
|-- app/                      # Streamlit dashboard application
|   |-- components/           # UI components
|   |   |-- overview.py       # Feature One: India Tourism Overview
|   |   |-- state_explorer.py # Feature Two: State Explorer (Single-state deep-dive)
|   |   |-- tourism.py        # Detailed State Analytics & Rankings
|   |   `-- data_quality.py   # Data Quality & Governance Audit
|   |-- data_loader.py        # Direct SQL loading, Parquet fallback & analytics helpers
|   `-- main.py               # Streamlit application entry point
|-- docs/                     # Governance, Quality & Architecture Documentation
|   |-- data_governance_report.md # Provenance, ownership, taxonomy, security
|   |-- data_quality_report.md    # Multi-dimensional quality audit & data dictionary
|   |-- etl_execution_report.md   # Step-by-step ETL execution & row reconciliation
|   `-- data_lineage.md           # Visual Mermaid data lineage diagram
|-- scripts/                  # Automation & Audit Verification Scripts
|   `-- generate_governance_reports.py # Automated reconciliation & quality audit CLI
|-- src/                      # Backend & data engineering modules
|   |-- ingestion/            # Raw tourism data ingestion clients
|   |-- pipeline/             # PySpark ETL transformations & data validation
|   |   |-- spark_session.py  # SparkSession factory & JVM configuration
|   |   |-- tourism_pipeline.py# PySpark wide-to-long ETL & YoY growth windowing
|   |   `-- run_tourism_pipeline.py # CLI execution script for tourism ETL
|   `-- database/             # Relational database logic
|       |-- config.py         # Environment parsing & credential management
|       |-- connection.py     # SQLAlchemy engine & session factory
|       |-- models.py         # TourismStatewiseAnnual ORM table schema
|       |-- loader.py         # Idempotent upsert & verification queries
|       `-- init_db.py        # CLI database management & verification tool
|-- data/                     # Data storage
|   |-- raw/tourism/          # Official Ministry of Tourism CSVs & metadata
|   `-- processed/tourism/    # Curated Parquet lake & quality audit reports
|-- tests/                    # Automated pytest suite
|-- .streamlit/               # Streamlit theme configuration (Dark Mode)
|-- .env.example              # Template for environment variables
|-- requirements.txt          # Python dependencies
`-- README.md                 # Project documentation
```

---

## Dashboard Features

### 🇮🇳 Feature One: India Tourism Overview
- **Executive KPI Cards**: Real-time aggregated Domestic Tourist Visits (DTV), Foreign Tourist Visits (FTV), and Total Reported Visits with national visitor shares.
- **Strict Aggregation Rules**: Zero double-counting guaranteed by isolating official `Total India` aggregate records from individual state aggregations.
- **Longitudinal Trajectories**: Dual-category annual footfall charts (2018–2022) with pre-pandemic, COVID-19 lockdown drop (-74%), and post-pandemic recovery (+155%) dynamics.
- **Top State Rankings**: Interactive ranking of top visiting States & Union Territories (Top 5 to 36).
- **Verified Data Coverage**: Transparent summary of temporal periods, 36 administrative entities, and database record metrics.

### 🏛️ Feature Two: State Explorer (Dedicated Single-State Analysis)
- **Verified State Search**: Searchable dropdown containing strictly the 36 verified States/UTs present in the official dataset.
- **Dynamic Filtering**: Filter by specific year (2018–2022) or analyze cumulative 5-year totals.
- **Core State KPIs**: Domestic visits, Foreign visits, Total visits (with incomplete indicator), domestic/foreign visitor share (%), and All-India State Rank.
- **Automated Data-Driven Narrative**: Algorithmic summary paragraph generated purely from calculated metrics (identifies peak years, contraction points, visitor profile, and official footnotes).
- **Side-by-Side State Benchmark**: Direct comparative table and trajectory chart comparing the chosen state against any secondary benchmark state.
- **Historical Null Distinction**: Explicitly displays `N/A (Unrecorded)` for Ladakh in 2018 rather than distorting historical statistics with 0.

### 📊 Detailed State Analytics
- Multi-dimensional filtering by year, tourist category, and specific states.
- Interactive distribution and YoY growth bar charts.

### 🛡️ Data Quality & Governance
- Transparent audit metrics produced by the PySpark ETL pipeline.
- Schema constraints, natural key uniqueness, negative value checks, and official estimation tracking (Maharashtra & Delhi 2022).

### 🏗️ Architecture & ETL Engineering
- Interactive end-to-end architecture view in the dashboard.
- Complete verified technology stack table with exact versions and roles.
- Step-by-step visual state transitions after each ETL stage (Wide raw CSV -> Pre-validation -> PySpark Unpivot -> Type Casts & Null Guarding -> YoY Windowing -> Curated Parquet Lake -> SQL Database -> Dashboard).

---

## How to Run the Platform

### 1. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Launch the Streamlit Dashboard
```powershell
streamlit run app/main.py
```
Open your browser at `http://localhost:8501`.

### 3. Run Automated Governance & Quality Audit Verification
To reconcile row counts across CSV, Parquet, and SQL stores and verify idempotency:
```powershell
python scripts/generate_governance_reports.py
```

### 4. Run the Automated Test Suite
```powershell
pytest
```
*All 47 tests execute and pass without requiring external services.*