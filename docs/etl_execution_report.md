# TravelWise — Detailed ETL Execution & Pipeline Verification Report

> **ETL Engine:** Apache PySpark 3.5.1 on Java HotSpot(TM) 64-Bit Server VM (build 21.0.12+7-LTS)  
> **Storage Target:** Snappy Parquet Lake & Relational SQL Store (PostgreSQL / SQLite)  
> **Execution Status:** **ALL PIPELINE STAGES VERIFIED (100% Success)**

---

## 1. Stage-by-Stage ETL Architecture & Operations

### Stage A: Extract (Ingestion & Pre-Transformation Validation)

- **Source File Path:** [`data/raw/tourism/india_tourism_statewise_2018_2022.csv`](file:///d:/Travel%20and%20tourism/data/raw/tourism/india_tourism_statewise_2018_2022.csv)
- **Ingestion Module:** [`src/pipeline/tourism_pipeline.py`](file:///d:/Travel%20and%20tourism/src/pipeline/tourism_pipeline.py) via [`src/pipeline/run_tourism_pipeline.py`](file:///d:/Travel%20and%20tourism/src/pipeline/run_tourism_pipeline.py)
- **Extraction Mechanism:** Loaded into a PySpark DataFrame using `spark.read.option("header", "true").csv(raw_csv_path)`.
- **Expected Input Schema:**
  ```text
  root
   |-- State/UT: string (nullable = true)
   |-- Category: string (nullable = true)
   |-- 2018: string (nullable = true)
   |-- 2019: string (nullable = true)
   |-- 2020: string (nullable = true)
   |-- 2021: string (nullable = true)
   |-- 2022: string (nullable = true)
  ```
- **Pre-Transformation Schema Validation:** The function `validate_raw_tourism_columns(df.columns)` executes before any transformation. It raises `TourismPipelineError` if any expected column (`["State/UT", "Category", "2018", "2019", "2020", "2021", "2022"]`) is absent.

---

### Stage B: Transform (PySpark Normalization & Feature Engineering)

Every transformation implemented in [`src/pipeline/tourism_pipeline.py`](file:///d:/Travel%20and%20tourism/src/pipeline/tourism_pipeline.py) is documented below:

#### Transformation 1: Wide-to-Long Matrix Unpivoting
1. **Input Structure:** Wide DataFrame (7 columns: `State/UT`, `Category`, `2018`, `2019`, `2020`, `2021`, `2022`).
2. **Operation Performed:**
   ```python
   unpivoted = df.unpivot(
       ids=["State/UT", "Category"],
       values=["2018", "2019", "2020", "2021", "2022"],
       variableColumnName="year_str",
       valueColumnName="visit_str"
   )
   ```
3. **Output Structure:** Normalized DataFrame with 4 columns: `State/UT`, `Category`, `year_str`, `visit_str` (370 rows).
4. **Reason:** Relational and time-series analytical engines require long (tidy) format where each record represents a single temporal observation.

#### Transformation 2: Cleaning, Casting, and Historical Null Preservation
1. **Input Structure:** String-typed `year_str` and `visit_str`.
2. **Operation Performed:**
   ```python
   long_df = unpivoted.select(
       F.trim(F.col("State/UT")).alias("state"),
       F.trim(F.col("Category")).alias("category"),
       F.col("year_str").cast("int").alias("year"),
       F.when(
           F.col("visit_str").isNull() | (F.trim(F.col("visit_str")) == "") | (F.trim(F.col("visit_str")) == "NaN"),
           None
       ).otherwise(
           F.col("visit_str").cast("bigint")
       ).alias("visit_count")
   )
   ```
3. **Output Structure:** Strongly typed columns (`state: string`, `category: string`, `year: int`, `visit_count: bigint`).
4. **Reason:** Guarantees numerical precision while strictly preserving genuine historical missing values (Ladakh in 2018) as `NULL` instead of coercing to 0.

#### Transformation 3: Classification Indicators & Official Estimation Tagging
1. **Input Structure:** Long DataFrame with `state`, `year`.
2. **Operation Performed:**
   ```python
   curated_df = long_df.withColumn(
       "is_aggregate",
       F.col("state") == "Total India"
   ).withColumn(
       "entity_type",
       F.when(F.col("state") == "Total India", F.lit("AGGREGATE_TOTAL")).otherwise(F.lit("STATE_OR_UT"))
   ).withColumn(
       "is_estimated",
       (F.col("state").isin(["Maharashtra", "Delhi"])) & (F.col("year") == 2022)
   )
   ```
3. **Output Structure:** Adds `is_aggregate: boolean`, `entity_type: string`, and `is_estimated: boolean`.
4. **Reason:** Enables downstream queries to isolate national aggregates to prevent 2x double counting and tags official Ministry estimates for auditability.

#### Transformation 4: Year-over-Year (YoY) Growth Window Computation
1. **Input Structure:** Curated DataFrame partitioned by entity and category.
2. **Operation Performed:**
   ```python
   window_spec = Window.partitionBy("state", "category").orderBy("year")
   prev_visit = F.lag("visit_count", 1).over(window_spec)

   result_df = df.withColumn(
       "prev_year_visit_count",
       prev_visit
   ).withColumn(
       "yoy_growth_pct",
       F.when(
           F.col("visit_count").isNotNull() & prev_visit.isNotNull() & (prev_visit > 0),
           F.round(((F.col("visit_count") - prev_visit) / prev_visit) * 100.0, 2)
       ).otherwise(None)
   )
   ```
3. **Output Structure:** Adds `prev_year_visit_count: bigint` and `yoy_growth_pct: float`.
4. **Reason:** Provides pre-computed longitudinal growth dynamics per state without requiring runtime table self-joins in the dashboard.

#### Transformation 5: Curated Schema & Domain Assertions
1. **Input Structure:** Transformed DataFrame.
2. **Operation Performed:** `validate_tourism_curated(df)` asserts:
   - Exactly 370 total records.
   - Zero negative values (`visit_count >= 0`).
   - Zero duplicate natural keys on `(state, category, year)`.
   - Exactly 2 null visit counts (Ladakh 2018).
   - Exactly 10 aggregate rows (`Total India`).
   - Exactly 4 estimated rows (Maharashtra & Delhi 2022).
3. **Output Structure:** Verified curated DataFrame.
4. **Reason:** Quality gate ensuring only verified data is written to the lake.

---

### Stage C: Curated Lake Output

- **Parquet Path:** [`data/processed/tourism/india_tourism_statewise_normalized.parquet`](file:///d:/Travel%20and%20tourism/data/processed/tourism/india_tourism_statewise_normalized.parquet)
- **Output Schema:** 9 columns (`state`, `category`, `year`, `visit_count`, `is_aggregate`, `entity_type`, `is_estimated`, `prev_year_visit_count`, `yoy_growth_pct`).
- **File Format:** Apache Parquet with Snappy compression.
- **Write Mode:** Idempotent `mode("overwrite")` ensures repeated runs replace rather than corrupt the lake.
- **Companion Quality Reports:**
  - JSON Machine Audit: [`data/processed/tourism/quality_report.json`](file:///d:/Travel%20and%20tourism/data/processed/tourism/quality_report.json)
  - Markdown Summary: [`data/processed/tourism/quality_report.md`](file:///d:/Travel%20and%20tourism/data/processed/tourism/quality_report.md)

---

### Stage D: Relational SQL Database Loading

- **Database Engine Support:** Dual-engine architecture:
  - **PostgreSQL 18** (Production engine via `psycopg2`).
  - **SQLite Store** ([`data/travelwise.db`](file:///d:/Travel%20and%20tourism/data/travelwise.db)) (Self-contained zero-configuration local engine).
- **Target Table Name:** `tourism_statewise_annual`
- **Table Definition ([src/database/models.py](file:///d:/Travel%20and%20tourism/src/database/models.py)):**
  - Primary Key: `id (INTEGER AUTOINCREMENT)`
  - Unique Constraint: `uq_tourism_state_category_year UNIQUE(state, category, year)`
  - Indexes: `idx_tourism_state_category (state, category)`, individual indexes on `year` and `is_aggregate`.
- **Loading Mechanism ([src/database/loader.py](file:///d:/Travel%20and%20tourism/src/database/loader.py)):**
  - Converts Parquet records into SQL dictionaries with strict `None` handling.
  - Implements dialect-aware idempotent upsert:
    - **PostgreSQL:** `INSERT ... ON CONFLICT (state, category, year) DO UPDATE SET ...`
    - **SQLite:** `INSERT OR REPLACE INTO tourism_statewise_annual ...`
  - Transactions are committed atomically in batches of 500 records.

---

### Stage E: Streamlit Dashboard Presentation

- **Connection & Data Loading ([app/data_loader.py](file:///d:/Travel%20and%20tourism/app/data_loader.py)):**
  - Executes SQL query `SELECT state, category, year, visit_count, is_aggregate, entity_type, is_estimated, prev_year_visit_count, yoy_growth_pct FROM tourism_statewise_annual ORDER BY state, category, year` via SQLAlchemy engine.
  - Caches results via `@st.cache_data`.
  - Fallback: If database is unreachable, gracefully reads curated Parquet lake directly.
- **KPI Aggregation Rules:**
  - National macro totals strictly filter `is_aggregate = TRUE` or sum `is_aggregate = FALSE` rows.
  - State rankings strictly filter `is_aggregate = FALSE` to eliminate `Total India` from state leaderboards.
- **State Explorer Deep-Dive:**
  - Dropdown populated with `get_all_distinct_states(df)` containing exactly 36 verified States/UTs.
  - Single-state analytics computed dynamically via `compute_state_analytics`.
  - Preserves `N/A (Unrecorded)` for missing historical figures (e.g. Ladakh 2018).

---

## 2. End-to-End Row-Count Reconciliation

The table below reconciles record counts across all pipeline stages:

| Stage Number | Pipeline Stage / Storage Layer | Entity / Table Name | Row Count | Column Count | Mathematical & Transformation Rationale |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | Raw Source File | `india_tourism_statewise_2018_2022.csv` | **74** | **7** | 37 entities (28 States + 8 UTs + 1 Total India) × 2 categories (`Domestic`, `Foreign`). All 5 years are horizontal columns. |
| **2** | PySpark Extraction | `DataFrame` (Extracted raw CSV) | **74** | **7** | Direct load of CSV with header option. Schema validated. |
| **3** | PySpark Normalization | `DataFrame` (Unpivoted long format) | **370** | **9** | **Mathematical Expansion:** 74 wide rows unpivoted across 5 years (2018–2022) = $74 \times 5 = \mathbf{370\text{ records}}$. |
| **4** | Curated Parquet Lake | `india_tourism_statewise_normalized.parquet` | **370** | **9** | Snappy compressed columnar lake storing all normalized records. |
| **5** | Relational SQL Database | Table `tourism_statewise_annual` | **370** | **12** | Relational persistence with surrogate primary key `id`, `created_at`, `updated_at`. |
| **6** | Streamlit SQL Query | In-Memory Cached DataFrame | **370** | **9** | Queried via SQLAlchemy. Divided into 360 State records and 10 Total India records. |

---

## 3. Repeat-Run & Idempotency Verification

An essential requirement of enterprise ETL pipelines is **idempotency**: running the ingestion script repeatedly on the same source data must never duplicate rows or alter correct values.

### Live Verification Execution Log (Terminal Run: October 2026)

```text
[Step 1] Initial Database Record Count Query:
         SELECT COUNT(1) FROM tourism_statewise_annual;
         -> Result: 370 records

[Step 2] Re-Running Ingestion Pipeline:
         load_curated_tourism_to_db(engine=engine)
         -> Result: 370 records processed via ON CONFLICT upsert

[Step 3] Post-Reload Record Count Query:
         SELECT COUNT(1) FROM tourism_statewise_annual;
         -> Result: 370 records (Zero row inflation)

[Step 4] Natural Key Uniqueness Audit Query:
         SELECT state, category, year, COUNT(1) 
         FROM tourism_statewise_annual 
         GROUP BY state, category, year 
         HAVING COUNT(1) > 1;
         -> Result: 0 duplicate rows found
```

**Final Idempotency Verification Status: PASSED (100% Idempotent)**
