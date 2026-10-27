# TravelWise — End-to-End Data Lineage & Provenance Architecture

> **Platform:** TravelWise Data Engineering Platform  
> **Documentation Scope:** Full Data Lineage from Government Sources to Interactive Streamlit Dashboards

---

## 1. Visual Data Lineage Architecture (Mermaid Diagram)

```mermaid
graph TD
    classDef sourceStyle fill:#1e293b,stroke:#475569,stroke-width:2px,color:#f8fafc;
    classDef processStyle fill:#0f172a,stroke:#0284c7,stroke-width:2px,color:#38bdf8;
    classDef qualityStyle fill:#132e35,stroke:#0d9488,stroke-width:2px,color:#2dd4bf;
    classDef storageStyle fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#a5b4fc;
    classDef uiStyle fill:#172554,stroke:#2563eb,stroke-width:2px,color:#93c5fd;

    subgraph External_Sources["1. Authoritative Source Documents"]
        MOT["Ministry of Tourism, Govt of India<br>(data.tourism.gov.in)"]:::sourceStyle
        PDFS["Official Annual Reports<br>Table 5.1.2 & Table 4.1.2<br>(PDFs & Word Archives)"]:::sourceStyle
    end

    subgraph Raw_Storage["2. Raw Data Repository"]
        RAW_CSV["india_tourism_statewise_2018_2022.csv<br>[74 rows × 7 cols, Wide Format]"]:::storageStyle
        RAW_META["metadata_india_tourism_statewise_2018_2022.json<br>[Official Source Lineage & Bounds]"]:::storageStyle
    end

    subgraph PySpark_ETL["3. Distributed PySpark ETL Engine (tourism_pipeline.py)"]
        EXTRACT["Extraction & Column Validation<br>(validate_raw_tourism_columns)"]:::processStyle
        UNPIVOT["Wide-to-Long Unpivot<br>(unpivot_tourism_data: 5x expansion)"]:::processStyle
        CAST_CLEAN["Data Type Casting & Null Guarding<br>(Preserves Ladakh 2018 NULL)"]:::processStyle
        CLASSIFY["Aggregate & Estimation Tagging<br>(is_aggregate & is_estimated)"]:::processStyle
        WINDOW_YOY["Longitudinal Windowing<br>(Window lag compute_yoy_growth)"]:::processStyle
        GATE["Quality Assertion Gate<br>(validate_tourism_curated)"]:::qualityStyle
    end

    subgraph Curated_Artifacts["4. Curated Lake & Governance Artifacts"]
        PARQUET["india_tourism_statewise_normalized.parquet<br>[370 rows × 9 cols, Snappy Parquet]"]:::storageStyle
        Q_JSON["quality_report.json<br>[Machine-Readable Quality Metrics]"]:::qualityStyle
        Q_MD["quality_report.md<br>[Audit Trail Summary]"]:::qualityStyle
    end

    subgraph SQL_Layer["5. Relational Database Storage (PostgreSQL 18 / SQLite)"]
        LOADER["Idempotent SQL Loader<br>(src/database/loader.py: _execute_upsert)"]:::processStyle
        SQL_TABLE[("tourism_statewise_annual<br>[370 rows × 12 cols, Indexed PK]")]:::storageStyle
    end

    subgraph Presentation_Layer["6. Streamlit Business Intelligence Platform"]
        DATA_LOADER["SQL Cached Data Loader<br>(app/data_loader.py: load_tourism_from_sql)"]:::processStyle
        
        OVERVIEW["Feature One: India Tourism Overview<br>• Macro KPIs & Share %<br>• National YoY Trends<br>• Top State Rankings<br>• Data Governance & Audit"]:::uiStyle
        
        EXPLORER["Feature Two: State Explorer<br>• Searchable 36 States/UTs<br>• Dynamic Single-State Trajectories<br>• Domestic vs Foreign Mix<br>• Automated Analytical Summary<br>• State-to-State Benchmark"]:::uiStyle
        
        GOVERNANCE_UI["Data Quality & Governance View<br>• Constraint Audits<br>• Null & Estimate Transparency"]:::uiStyle
    end

    %% Flow connections
    MOT --> PDFS
    PDFS --> RAW_CSV
    PDFS --> RAW_META
    RAW_CSV --> EXTRACT
    EXTRACT --> UNPIVOT
    UNPIVOT --> CAST_CLEAN
    CAST_CLEAN --> CLASSIFY
    CLASSIFY --> WINDOW_YOY
    WINDOW_YOY --> GATE
    GATE --> PARQUET
    GATE --> Q_JSON
    GATE --> Q_MD
    PARQUET --> LOADER
    LOADER --> SQL_TABLE
    SQL_TABLE --> DATA_LOADER
    PARQUET -. "Resilient Fallback" .-> DATA_LOADER
    DATA_LOADER --> OVERVIEW
    DATA_LOADER --> EXPLORER
    DATA_LOADER --> GOVERNANCE_UI
```

---

## 2. Component Lineage Breakdown

### Node 1: Official Sources to Raw CSV
- **Ingestion Origin:** Compiled from annual reports published by the Market Research Division, Ministry of Tourism, Govt. of India.
- **Archive Path:** [`data/raw/tourism/`](file:///d:/Travel%20and%20tourism/data/raw/tourism/)
- **Primary Raw CSV:** [`data/raw/tourism/india_tourism_statewise_2018_2022.csv`](file:///d:/Travel%20and%20tourism/data/raw/tourism/india_tourism_statewise_2018_2022.csv)
- **Schema:** 7 columns: `State/UT`, `Category`, `2018`, `2019`, `2020`, `2021`, `2022`.
- **Row Count:** 74 rows (37 entities × 2 categories).

### Node 2: PySpark Normalization & Processing
- **Execution Script:** [`src/pipeline/run_tourism_pipeline.py`](file:///d:/Travel%20and%20tourism/src/pipeline/run_tourism_pipeline.py)
- **Engine Module:** [`src/pipeline/tourism_pipeline.py`](file:///d:/Travel%20and%20tourism/src/pipeline/tourism_pipeline.py)
- **Core Operations:**
  1. Header and column validation (`validate_raw_tourism_columns`).
  2. Wide-to-long unpivoting across 5 years ($74 \times 5 = 370$ rows).
  3. Safe type casting to `BIGINT` and genuine historical null preservation (Ladakh 2018).
  4. Adding `is_aggregate = (state == 'Total India')` to isolate national totals.
  5. Tagging `is_estimated = True` for Maharashtra and Delhi in 2022 per official compendium footnotes.
  6. Computing Year-over-Year growth percentage via PySpark analytical window function:
     $$\text{yoy\_growth\_pct} = \frac{\text{visit\_count} - \text{prev\_visit}}{\text{prev\_visit}} \times 100$$
  7. Quality assertions gate (`validate_tourism_curated`).

### Node 3: Curated Parquet Lake
- **File Destination:** [`data/processed/tourism/india_tourism_statewise_normalized.parquet`](file:///d:/Travel%20and%20tourism/data/processed/tourism/india_tourism_statewise_normalized.parquet)
- **Compression:** Snappy Columnar Parquet.
- **Quality Artifacts Generated:**
  - Machine-readable audit: [`data/processed/tourism/quality_report.json`](file:///d:/Travel%20and%20tourism/data/processed/tourism/quality_report.json)
  - Human-readable audit: [`data/processed/tourism/quality_report.md`](file:///d:/Travel%20and%20tourism/data/processed/tourism/quality_report.md)

### Node 4: Relational SQL Persistence
- **Loading Module:** [`src/database/loader.py`](file:///d:/Travel%20and%20tourism/src/database/loader.py)
- **Table Destination:** `tourism_statewise_annual`
- **Dialect Handling:**
  - **PostgreSQL:** Uses `sqlalchemy.dialects.postgresql.insert` with `ON CONFLICT (state, category, year) DO UPDATE`.
  - **SQLite:** Uses `INSERT OR REPLACE` with transactional batching.
- **Verification:** Verified 370 rows with 0 duplicate keys on `(state, category, year)`.

### Node 5: Streamlit Analytics Platform
- **Data Access Helper:** [`app/data_loader.py`](file:///d:/Travel%20and%20tourism/app/data_loader.py)
- **Primary Data Source:** SQL Database via `load_tourism_from_sql()` (PostgreSQL or local SQLite store).
- **Fallback Layer:** If the SQL database service is unavailable, automatically falls back to curated Parquet lake directly.
- **User Views:**
  1. **India Tourism Overview:** Executive macro KPIs, national trajectories, top state rankings, and zero double-counting guarantee.
  2. **State Explorer:** Dedicated deep-dive for any of the 36 verified States/UTs with automated narrative synthesis, domestic vs foreign visitor mix, and side-by-side benchmarking.
  3. **Data Quality & Governance:** Transparent validation reports and schema constraint auditing.
