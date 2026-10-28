import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window
import pandas as pd

from src.pipeline.spark_session import get_spark_session

logger = logging.getLogger(__name__)

EXPECTED_RAW_COLUMNS = [
    "monument_name",
    "circle",
    "state_or_region",
    "financial_year",
    "domestic_visitors",
    "foreign_visitors",
    "total_visitors",
    "source",
]
ALLOWED_FINANCIAL_YEARS = {"2022-23", "2023-24"}

class MonumentPipelineError(Exception):
    """Custom exception raised for Monument ETL Pipeline failures."""
    pass

def validate_raw_monument_columns(columns: List[str]) -> None:
    """
    Validates that the raw monument DataFrame contains all required columns.
    """
    missing = [c for c in EXPECTED_RAW_COLUMNS if c not in columns]
    if missing:
        raise MonumentPipelineError(
            f"Missing required columns in raw monument dataset: {missing}. Expected: {EXPECTED_RAW_COLUMNS}"
        )

def process_monument_data(df: DataFrame) -> DataFrame:
    """
    Cleans, casts, and normalizes monument visitor statistics:
    - Trims string fields
    - Casts numeric visitor counts while preserving genuine nulls
    - Computes consistent total visitors if not already set
    - Drops duplicates on natural key (monument_name, financial_year)
    """
    validate_raw_monument_columns(df.columns)

    # Clean and cast fields
    cleaned_df = df.select(
        (F.col("serial_number").cast("int") if "serial_number" in df.columns else F.lit(None).cast("int")).alias("serial_number"),
        F.trim(F.col("monument_name")).alias("monument_name"),
        F.trim(F.col("circle")).alias("circle"),
        F.trim(F.col("state_or_region")).alias("state_or_region"),
        F.trim(F.col("financial_year")).alias("financial_year"),
        F.when(
            F.col("domestic_visitors").isNull() | (F.trim(F.col("domestic_visitors").cast("string")) == ""),
            None
        ).otherwise(F.col("domestic_visitors").cast("bigint")).alias("domestic_visitors"),
        F.when(
            F.col("foreign_visitors").isNull() | (F.trim(F.col("foreign_visitors").cast("string")) == ""),
            None
        ).otherwise(F.col("foreign_visitors").cast("bigint")).alias("foreign_visitors"),
        F.when(
            F.col("total_visitors").isNull() | (F.trim(F.col("total_visitors").cast("string")) == ""),
            None
        ).otherwise(F.col("total_visitors").cast("bigint")).alias("total_visitors"),
        F.trim(F.col("source")).alias("source"),
    )

    # Reconcile total_visitors: if total_visitors is null but either domestic or foreign is present
    reconciled_df = cleaned_df.withColumn(
        "total_visitors",
        F.when(
            F.col("domestic_visitors").isNull() & F.col("foreign_visitors").isNull(),
            None
        ).when(
            F.col("total_visitors").isNotNull(),
            F.col("total_visitors")
        ).otherwise(
            F.coalesce(F.col("domestic_visitors"), F.lit(0)) + F.coalesce(F.col("foreign_visitors"), F.lit(0))
        )
    )

    # Deduplicate on natural key (monument_name, financial_year)
    deduped_df = reconciled_df.dropDuplicates(["monument_name", "financial_year"])

    return deduped_df

def compute_monument_metrics(df: DataFrame) -> DataFrame:
    """
    Computes windowed longitudinal metrics:
    - Previous financial year domestic, foreign, and total visitor counts
    - YoY percentage growth for total visitors
    - Foreign visitor footfall share percentage
    """
    window_spec = Window.partitionBy("monument_name").orderBy("financial_year")

    prev_total = F.lag("total_visitors", 1).over(window_spec)
    prev_domestic = F.lag("domestic_visitors", 1).over(window_spec)
    prev_foreign = F.lag("foreign_visitors", 1).over(window_spec)

    result_df = df.withColumn(
        "prev_year_domestic_visitors",
        prev_domestic
    ).withColumn(
        "prev_year_foreign_visitors",
        prev_foreign
    ).withColumn(
        "prev_year_total_visitors",
        prev_total
    ).withColumn(
        "yoy_growth_pct",
        F.when(
            F.col("total_visitors").isNotNull() & prev_total.isNotNull() & (prev_total > 0),
            F.round(((F.col("total_visitors") - prev_total) / prev_total) * 100.0, 2)
        ).otherwise(None)
    ).withColumn(
        "foreign_visitor_share_pct",
        F.when(
            F.col("total_visitors").isNotNull() & (F.col("total_visitors") > 0) & F.col("foreign_visitors").isNotNull(),
            F.round((F.col("foreign_visitors") / F.col("total_visitors")) * 100.0, 2)
        ).otherwise(None)
    )

    return result_df

def validate_monument_curated(df: DataFrame) -> Dict[str, Any]:
    """
    Performs comprehensive data quality validation on the curated monument DataFrame:
    - Verifies valid financial years ('2022-23', '2023-24')
    - Checks for negative visitor counts
    - Checks for duplicate (monument_name, financial_year) natural keys
    - Computes completeness metrics and category sums
    """
    total_records = df.count()
    if total_records == 0:
        raise MonumentPipelineError("Curated monument dataset contains 0 records.")

    # Check allowed financial years
    years = [row["financial_year"] for row in df.select("financial_year").distinct().collect()]
    invalid_years = [y for y in years if y not in ALLOWED_FINANCIAL_YEARS]
    if invalid_years:
        raise MonumentPipelineError(f"Invalid financial years found: {invalid_years}. Allowed: {ALLOWED_FINANCIAL_YEARS}")

    # Check negative values
    neg_dom = df.filter(F.col("domestic_visitors") < 0).count()
    neg_for = df.filter(F.col("foreign_visitors") < 0).count()
    neg_tot = df.filter(F.col("total_visitors") < 0).count()
    if neg_dom > 0 or neg_for > 0 or neg_tot > 0:
        raise MonumentPipelineError(f"Found negative visitor counts in dataset: dom={neg_dom}, for={neg_for}, tot={neg_tot}")

    # Check duplicates on natural key (monument_name, financial_year)
    dup_count = df.groupBy("monument_name", "financial_year").count().filter(F.col("count") > 1).count()
    if dup_count > 0:
        raise MonumentPipelineError(f"Found {dup_count} duplicate (monument_name, financial_year) records.")

    # Counts and metrics
    distinct_monuments = df.select("monument_name").distinct().count()
    distinct_circles = df.select("circle").distinct().count()
    distinct_states = df.select("state_or_region").distinct().count()

    null_domestic = df.filter(F.col("domestic_visitors").isNull()).count()
    null_foreign = df.filter(F.col("foreign_visitors").isNull()).count()
    null_total = df.filter(F.col("total_visitors").isNull()).count()
    null_yoy = df.filter(F.col("yoy_growth_pct").isNull()).count()

    # Sum aggregations for reconciliation
    sums_by_year = (
        df.groupBy("financial_year")
        .agg(
            F.coalesce(F.sum("domestic_visitors"), F.lit(0)).alias("total_domestic"),
            F.coalesce(F.sum("foreign_visitors"), F.lit(0)).alias("total_foreign"),
            F.coalesce(F.sum("total_visitors"), F.lit(0)).alias("total_visitors")
        )
        .collect()
    )

    reconciliation = {
        row["financial_year"]: {
            "domestic_visitors": int(row["total_domestic"]),
            "foreign_visitors": int(row["total_foreign"]),
            "total_visitors": int(row["total_visitors"]),
        }
        for row in sums_by_year
    }

    metrics = {
        "total_records": total_records,
        "distinct_monuments": distinct_monuments,
        "distinct_circles": distinct_circles,
        "distinct_states": distinct_states,
        "financial_years": sorted(years),
        "null_domestic_records": null_domestic,
        "null_foreign_records": null_foreign,
        "null_total_records": null_total,
        "null_yoy_growth_records": null_yoy,
        "duplicate_records": dup_count,
        "negative_records": neg_dom + neg_for + neg_tot,
        "reconciliation": reconciliation,
    }
    return metrics

def run_monument_pipeline(
    input_json_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    spark: Optional[SparkSession] = None
) -> Tuple[DataFrame, Dict[str, Any]]:
    """
    Executes the full PySpark Monument ETL Pipeline:
    1. Reads raw monument JSON dataset
    2. Cleans schema, casts numeric footfalls, deduplicates on natural key
    3. Computes longitudinal YoY growth and foreign visitor share
    4. Validates data quality constraints and reconciles official footfall totals
    5. Saves curated Parquet and quality report
    """
    close_spark_at_end = False
    if spark is None:
        spark = get_spark_session("TravelWise-Monument-ETL")
        close_spark_at_end = True

    base_dir = Path(__file__).resolve().parents[2]
    if input_json_path is None:
        input_json = base_dir / "data" / "raw" / "monuments" / "asi_monument_visitors.json"
    else:
        input_json = Path(input_json_path)

    if output_dir is None:
        out_dir = base_dir / "data" / "processed" / "monuments"
    else:
        out_dir = Path(output_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_json.exists():
        raise MonumentPipelineError(f"Input monument JSON does not exist: {input_json}")

    logger.info(f"Reading raw monument JSON data from {input_json}")
    raw_df = spark.read.option("multiline", "true").json(str(input_json))
    raw_rows_count = raw_df.count()

    # Step 1: Clean and Normalize
    processed_df = process_monument_data(raw_df)

    # Step 2: Compute YoY Growth and Visitor Shares
    curated_df = compute_monument_metrics(processed_df)

    # Step 3: Validate Constraints & Reconcile
    quality_metrics = validate_monument_curated(curated_df)
    quality_metrics["input_json"] = str(input_json)
    quality_metrics["input_rows"] = raw_rows_count
    quality_metrics["output_rows"] = quality_metrics["total_records"]
    quality_metrics["output_dir"] = str(out_dir)

    # Step 4: Save Curated Parquet using pyarrow engine for guaranteed Windows compatibility
    parquet_path = out_dir / "asi_monument_visitors_normalized.parquet"
    curated_pdf = curated_df.toPandas()
    curated_pdf.to_parquet(str(parquet_path), engine="pyarrow", index=False)
    logger.info(f"Successfully saved normalized monument Parquet to {parquet_path}")

    # Step 5: Save Quality Report
    report_json = out_dir / "quality_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(quality_metrics, f, indent=2)

    report_md = out_dir / "quality_report.md"
    report_content = f"""# ASI Monument ETL Pipeline Quality Report

- **Input File**: `{quality_metrics['input_json']}`
- **Input Raw Rows**: {quality_metrics['input_rows']}
- **Output Curated Rows**: {quality_metrics['output_rows']}
- **Distinct Ticketed Monuments**: {quality_metrics['distinct_monuments']}
- **Distinct ASI Circles**: {quality_metrics['distinct_circles']}
- **Distinct States/Regions**: {quality_metrics['distinct_states']}
- **Financial Years Analyzed**: {', '.join(quality_metrics['financial_years'])}
- **Output Parquet**: `{parquet_path}`
- **Duplicate Records**: {quality_metrics['duplicate_records']}
- **Negative Value Records**: {quality_metrics['negative_records']}
- **Null Domestic Counts**: {quality_metrics['null_domestic_records']} (Preserved historical nulls: Fort St. George 2022-23, Mattancherry 2023-24)
- **Null Foreign Counts**: {quality_metrics['null_foreign_records']}
- **Null Total Footfall Counts**: {quality_metrics['null_total_records']}
- **Null YoY Growth Records**: {quality_metrics['null_yoy_growth_records']} (Base FY 2022-23 records + unrecorded prior period)

## Official Reconciled Totals
- **FY 2022-23 Footfall**: Domestic = {quality_metrics['reconciliation'].get('2022-23', {}).get('domestic_visitors', 0):,}, Foreign = {quality_metrics['reconciliation'].get('2022-23', {}).get('foreign_visitors', 0):,}, Total = {quality_metrics['reconciliation'].get('2022-23', {}).get('total_visitors', 0):,}
- **FY 2023-24 Footfall**: Domestic = {quality_metrics['reconciliation'].get('2023-24', {}).get('domestic_visitors', 0):,}, Foreign = {quality_metrics['reconciliation'].get('2023-24', {}).get('foreign_visitors', 0):,}, Total = {quality_metrics['reconciliation'].get('2023-24', {}).get('total_visitors', 0):,}
"""
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(report_content)

    if close_spark_at_end:
        spark.stop()

    return curated_df, quality_metrics
