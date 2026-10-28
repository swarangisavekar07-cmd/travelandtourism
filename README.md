# TravelWise — India Tourism & Monument Analytics Platform

TravelWise is an enterprise Data Engineering and Tourism Analytics platform designed to evaluate and visualize multi-dimensional tourism and heritage visitation patterns across India. It ingests and validates two independent official government datasets:

1. **State-wise Annual Tourism Dataset (CSV)**: Official state and union territory footfall figures published by the **Ministry of Tourism, Government of India** (2018–2022).
2. **Centrally Protected Ticketed ASI Monuments Dataset (JSON)**: Official domestic and international ticketing records for **145 Centrally Protected Monuments** across 33 Archaeological Survey of India (ASI) circles for Financial Years 2022-23 and 2023-24, sourced from the **Ministry of Tourism & Archaeological Survey of India** (*India Tourism Data Compendium 2024*, Table 4.2.3).

Both datasets are processed through dedicated **Apache PySpark ETL pipelines**, stored with schema constraints and natural key uniqueness in a relational database (**PostgreSQL / SQLite**), and presented through an executive **Streamlit BI Dashboard**.

---

## Architecture & Data Flow

```text
┌───────────────────────────────────────┐       ┌──────────────────────────────────────────────┐
│  Raw Tourism CSV (Ministry of Tourism)│       │  Raw ASI Monuments JSON (Ministry & ASI)     │
│  (State/UT Footfalls, 2018–2022 Wide) │       │  (145 Protected Sites, FY 2022-23 & 2023-24) │
└───────────────────┬───────────────────┘       └──────────────────────┬───────────────────────┘
                    │                                                  │
                    ▼                                                  ▼
┌───────────────────────────────────────┐       ┌──────────────────────────────────────────────┐
│   PySpark Tourism ETL Pipeline        │       │   PySpark Monument ETL Pipeline              │
│   - Schema Validation                 │       │   - JSON Validation & Schema Checks          │
│   - Wide-to-Long Unpivot              │       │   - Type Normalization & Footfall Casts      │
│   - YoY Growth Window Partitioning    │       │   - Longitudinal YoY Growth Windowing        │
│   - Historical Null Preservation      │       │   - Foreign Footfall Share Computation       │
└───────────────────┬───────────────────┘       └──────────────────────┬───────────────────────┘
                    │                                                  │
                    ▼                                                  ▼
┌───────────────────────────────────────┐       ┌──────────────────────────────────────────────┐
│   Curated Tourism Parquet Lake        │       │   Curated Monument Parquet Lake              │
│   (india_tourism_statewise_normalized)│       │   (asi_monument_visitors_normalized.parquet) │
└───────────────────┬───────────────────┘       └──────────────────────┬───────────────────────┘
                    │                                                  │
                    ▼                                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                  Relational Database Storage (PostgreSQL 18 / SQLite Store)                  │
│                                                                                              │
│   Table: tourism_statewise_annual             Table: asi_monument_visitors                   │
│   - Primary Key: (state, category, year)      - Primary Key: (monument_name, financial_year) │
│   - Idempotent Upsert Logic                   - Idempotent Upsert Logic                      │
│   - 370 Normalized Records                    - 290 Normalized Records (145 sites x 2 FYs)   │
└───────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                             Streamlit Executive Analytics Platform                           │
│                                                                                              │
│   🇮🇳 India Tourism Overview       🏛️ Monument Visitor Analysis    🏗️ Platform Architecture   │
│   🗺️ State Explorer Deep-Dive     📊 Detailed State Analytics     🛡️ Data Quality & Audit    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Governance & Quality Documentation Suite

Comprehensive audit trails, architecture diagrams, data dictionaries, and execution reports are maintained in the [`docs/`](docs/) directory:

1. **[Data Governance Report](docs/data_governance_report.md):** Provenance, data ownership, taxonomy, schema integrity, and security policies.
2. **[Data Quality Report](docs/data_quality_report.md):** Multi-dimensional quality matrix (Completeness, Validity, Uniqueness, Consistency, Accuracy, Timeliness, Referential Integrity, Transformation Integrity) with live query evidence.
3. **[ETL Execution & Reconciliation Report](docs/etl_execution_report.md):** Detailed stage-by-stage execution sequence (Extract, Transform, Curated Lake, SQL Load, Streamlit), row-count reconciliation, and repeat-run idempotency logs.
4. **[End-to-End Data Lineage](docs/data_lineage.md):** Visual Mermaid data lineage mapping data journey from Ministry publications to dashboard views.

---

## Technologies Used

- **Python 3.11.9 (64-bit)**: Core programming language runtime.
- **Streamlit 1.32.2**: Interactive executive analytics dashboard and user interface.
- **Plotly Express & Graph Objects 5.20.0**: Interactive footfall rankings, trajectory comparisons, and circle distributions.
- **PySpark 3.5.1**: Scalable ETL transformations, wide-to-long unpivoting, multi-year lag window functions, and schema validation.
- **Java / JDK 21.0.12 LTS**: Java Virtual Machine (JVM) executing PySpark driver and worker routines.
- **Pandas 2.2.1 & PyArrow 15.0.1**: Columnar Parquet lake reading and analytical transformations.
- **PostgreSQL 18 & SQLAlchemy 2.0.28**: Relational database storage with schema constraints, indexing, and idempotent upsert logic.
- **SQLite 3.x**: Local relational database engine for zero-configuration SQL execution and automated testing.
- **pytest & pytest-cov 8.1.1**: Comprehensive automated testing suite (100% passing tests).

---

## Project Structure

```text
TravelWise/
|-- app/                            # Streamlit dashboard application
|   |-- components/                 # UI components
|   |   |-- overview.py             # Feature One: India Tourism Overview
|   |   |-- state_explorer.py       # Feature Two: State Explorer (Single-state deep-dive)
|   |   |-- tourism.py              # Detailed State Analytics & Rankings
|   |   |-- monument_analysis.py    # Feature Three: Centrally Protected Ticketed Monuments
|   |   |-- architecture.py         # Architecture & ETL Engineering Flow
|   |   `-- data_quality.py         # Data Quality & Governance Audit
|   |-- data_loader.py              # Direct SQL loading, Parquet fallback & analytics helpers
|   `-- main.py                     # Streamlit application entry point
|-- docs/                           # Governance, Quality & Architecture Documentation
|   |-- data_governance_report.md   # Provenance, ownership, taxonomy, security
|   |-- data_quality_report.md      # Multi-dimensional quality audit & data dictionary
|   |-- etl_execution_report.md     # Step-by-step ETL execution & row reconciliation
|   `-- data_lineage.md             # Visual Mermaid data lineage diagram
|-- scripts/                        # Automation & Audit Verification Scripts
|   `-- generate_governance_reports.py # Automated reconciliation & quality audit CLI
|-- src/                            # Backend & data engineering modules
|   |-- ingestion/                  # Raw data ingestion clients
|   |   |-- tourism_client.py       # Ministry of Tourism CSV client
|   |   |-- monument_client.py      # ASI Monument JSON client
|   |   |-- weather_client.py       # Open-Meteo weather client
|   |   |-- run_tourism_ingestion.py # CLI runner for tourism CSV
|   |   `-- run_monument_ingestion.py# CLI runner for monument JSON
|   |-- pipeline/                   # PySpark ETL transformations & data validation
|   |   |-- spark_session.py        # SparkSession factory & JVM configuration
|   |   |-- tourism_pipeline.py     # PySpark wide-to-long ETL & YoY growth windowing
|   |   |-- monument_pipeline.py    # PySpark JSON ETL, growth lag & foreign share
|   |   |-- weather_pipeline.py     # PySpark daily weather aggregation
|   |   `-- run_pipelines.py        # Unified CLI execution script for all pipelines
|   `-- database/                   # Relational database logic
|       |-- config.py               # Environment parsing & credential management
|       |-- connection.py           # SQLAlchemy engine & session factory
|       |-- models.py               # SQLAlchemy ORM models (Tourism, Monuments, Weather)
|       |-- loader.py               # Idempotent upsert & verification queries
|       `-- init_db.py              # CLI database management & verification tool
|-- data/                           # Data storage
|   |-- raw/
|   |   |-- tourism/                # Official Ministry of Tourism CSVs & metadata
|   |   `-- monuments/              # Official ASI Monument JSON & metadata
|   |-- processed/
|   |   |-- tourism/                # Curated Tourism Parquet lake & quality reports
|   |   `-- monuments/              # Curated Monument Parquet lake & quality reports
|   `-- travelwise.db               # Local zero-configuration SQLite database
|-- tests/                          # Automated pytest suite (72 tests)
|   |-- test_basic.py
|   |-- test_dashboard_data.py
|   |-- test_dashboard_monuments.py
|   |-- test_database.py
|   |-- test_monument_database.py
|   |-- test_monument_ingestion.py
|   |-- test_pipeline_monument.py
|   |-- test_pipeline_tourism.py
|   |-- test_pipeline_weather.py
|   |-- test_tourism_ingestion.py
|   `-- test_weather_ingestion.py
|-- .streamlit/                     # Streamlit theme configuration (Dark Mode)
|-- .env.example                    # Template for environment variables
|-- requirements.txt                # Python dependencies
`-- README.md                       # Project documentation
```

---

## Dataset Provenance & Official Reconciliation

### 1. State-wise Annual Tourism Dataset (CSV)
- **Source**: Ministry of Tourism, Government of India (*India Tourism Statistics 2023*).
- **Format & Scope**: CSV format, wide-structure (2018–2022). Covers 36 administrative entities (28 States + 8 Union Territories) plus official national aggregate.
- **Normalization**: Unpivoted via PySpark from 74 wide rows to 370 normalized long records (360 state-level + 10 Total India records).
- **Historical Nulls**: Preserves unrecorded 2018 statistics for the Union Territory of Ladakh (established October 2019) as legitimate `null`.

### 2. Centrally Protected Ticketed ASI Monuments Dataset (JSON)
- **Source**: Archaeological Survey of India (ASI) & Ministry of Tourism, Government of India (*India Tourism Data Compendium 2024*, Chapter 4, Table 4.2.3: "Number of Visitors to Centrally Protected Ticketed Monuments, 2022-23 & 2023-24").
- **Format & Scope**: JSON format. Covers all **145 centrally protected ticketed heritage monuments** across **33 ASI administrative circles** in 21 States/UTs.
- **Observation Count**: 145 monuments × 2 Financial Years = **290 annual observation records**.
- **Official Footfall Reconciliation**:
  - **FY 2022-23**: Domestic = **47,901,021** | Foreign = **1,445,363** | Total = **49,346,384** (Exact 0 diff match)
  - **FY 2023-24**: Domestic = **53,090,007** | Foreign = **2,314,641** | Total = **55,404,648** (Exact 0 diff match)
  - **Combined Footfall**: **104,751,032** ticketed visits tracked across the two financial years.

---

## Dashboard Features

### 🇮🇳 Feature One: India Tourism Overview
- **Executive KPI Cards**: Real-time aggregated Domestic Tourist Visits (DTV), Foreign Tourist Visits (FTV), and Total Reported Visits with national visitor shares.
- **Strict Aggregation Rules**: Zero double-counting guaranteed by isolating official `Total India` aggregate records from individual state aggregations.
- **Longitudinal Trajectories**: Dual-category annual footfall charts (2018–2022) capturing pandemic disruptions and subsequent rebound.

### 🏛️ Feature Two: Centrally Protected Ticketed Monuments Analytics
- **Executive Monument KPIs**: Total footfall, domestic visitors, foreign visitors, foreign visitor footfall share (%), and most-visited heritage site.
- **National Rankings**: Top N monuments ranking (Top 5 to 30) with dual-category stacked footfall bars comparing domestic traffic against international pull.
- **YoY Recovery Dynamics**: Direct comparison of FY 2022-23 vs FY 2023-24 highlighting the remarkable **+60.1% surge** in international visitation.
- **Regional & Circle Distribution**: Interactive footfall aggregation across all 33 ASI circles (e.g. Agra Circle leading with 10.2M footfall, Delhi Circle with 8.1M footfall).
- **Single-Monument Inspector**: Deep-dive selector covering every individual monument (e.g., Taj Mahal, Sun Temple Konark, Red Fort, Qutub Minar, Agra Fort).

### 🏛️ Feature Three: State Explorer
- **Verified State Search**: Searchable dropdown containing strictly the 36 verified States/UTs.
- **Side-by-Side Benchmarking**: Direct comparative table and trajectory chart comparing chosen state against secondary benchmark states.

### 📊 Detailed State Analytics & 🛡️ Data Quality Audit
- Interactive distribution and YoY growth bar charts.
- Transparent PySpark ETL data quality audit reports with zero-null conversions and duplicate natural key tracking.

---

## How to Run the Platform

### 1. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Execute PySpark ETL Pipelines
To execute the ETL pipelines using Apache PySpark:
```powershell
# Run the ASI Monument JSON pipeline:
python -m src.pipeline.run_pipelines --pipeline monuments

# Run the Tourism CSV pipeline:
python -m src.pipeline.run_pipelines --pipeline tourism

# Run all pipelines (Tourism CSV + Monument JSON + Weather feed):
python -m src.pipeline.run_pipelines --pipeline all
```

### 3. Initialize & Populate the SQL Database
To create tables, load curated datasets with idempotent upsert, and verify counts:
```powershell
# Ingest into local SQLite store (zero-configuration):
python -m src.database.init_db --sqlite --all

# Or ingest into local PostgreSQL (when PostgreSQL service is running):
python -m src.database.init_db --all
```

### 4. Launch the Streamlit Dashboard
```powershell
streamlit run app/main.py
```
Open your browser at `http://localhost:8501`.

### 5. Run the Automated Test Suite
```powershell
pytest
```
*All 72 tests execute and pass without requiring external services.*