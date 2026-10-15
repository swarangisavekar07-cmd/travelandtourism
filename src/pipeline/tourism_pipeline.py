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

EXPECTED_RAW_COLUMNS = ["State/UT", "Category", "2018", "2019", "2020", "2021", "2022"]
ALLOWED_CATEGORIES = {"Domestic", "Foreign"}
YEAR_COLUMNS = ["2018", "2019", "2020", "2021", "2022"]

class TourismPipelineError(Exception):
    """Custom exception raised for Tourism ETL Pipeline failures."""
    pass

def validate_raw_tourism_columns(columns: List[str]) -> None:
    """
    Validates that the raw tourism DataFrame contains all required columns.
    """
    missing = [c for c in EXPECTED_RAW_COLUMNS if c not in columns]
    if missing:
        raise TourismPipelineError(
            f"Missing required columns in raw tourism dataset: {missing}. Expected: {EXPECTED_RAW_COLUMNS}"
        )

def unpivot_tourism_data(df: DataFrame) -> DataFrame:
    """
    Transforms wide year columns (2018-2022) into normalized long format.
    Preserves null values (does NOT convert nulls to zero or drop records).
    Adds classification indicators:
    - is_aggregate (bool): True for 'Total India'
    - entity_type (str): 'AGGREGATE_TOTAL' vs 'STATE_OR_UT'
    - is_estimated (bool): True for 2022 figures for Maharashtra and Delhi per official source metadata
    """
    validate_raw_tourism_columns(df.columns)

    # Use PySpark unpivot
    unpivoted = df.unpivot(
        ids=["State/UT", "Category"],
        values=YEAR_COLUMNS,
        variableColumnName="year_str",
        valueColumnName="visit_str"
    )

    # Clean and cast columns
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

    # Add aggregate indicator, entity type, and estimation flags
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

    return curated_df

def compute_yoy_growth(df: DataFrame) -> DataFrame:
    """
    Calculates year-over-year growth percentage for each state and category.
    Growth is calculated only when both current and previous year values exist and previous > 0.
    The first year (2018) or any year following a null year has no growth value (None).
    """
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

    return result_df

def validate_tourism_curated(df: DataFrame) -> Dict[str, Any]:
    """
    Performs comprehensive data quality validation on the curated tourism DataFrame:
    - Verifies allowed categories ('Domestic', 'Foreign')
    - Checks for negative visit counts
    - Checks for duplicate (state, category, year) combinations
    - Profiles null counts and total record counts
    """
    total_records = df.count()

    # Check categories
    categories = [row["category"] for row in df.select("category").distinct().collect()]
    invalid_categories = [c for c in categories if c not in ALLOWED_CATEGORIES]
    if invalid_categories:
        raise TourismPipelineError(f"Invalid categories found: {invalid_categories}")

    # Check negative values
    neg_count = df.filter(F.col("visit_count") < 0).count()
    if neg_count > 0:
        raise TourismPipelineError(f"Found {neg_count} negative visit counts in dataset.")

    # Check duplicates on primary key (state, category, year)
    dup_count = df.groupBy("state", "category", "year").count().filter(F.col("count") > 1).count()
    if dup_count > 0:
        raise TourismPipelineError(f"Found {dup_count} duplicate (state, category, year) records.")

    # Null counts
    null_visits = df.filter(F.col("visit_count").isNull()).count()
    null_growth = df.filter(F.col("yoy_growth_pct").isNull()).count()
    aggregate_records = df.filter(F.col("is_aggregate") == True).count()
    estimated_records = df.filter(F.col("is_estimated") == True).count()

    metrics = {
        "total_records": total_records,
        "distinct_states": df.select("state").distinct().count(),
        "categories": categories,
        "null_visit_counts": null_visits,
        "null_yoy_growth_records": null_growth,
        "aggregate_records": aggregate_records,
        "estimated_records": estimated_records,
        "duplicate_records": dup_count,
        "negative_records": neg_count
    }
    return metrics

def run_tourism_pipeline(
    input_csv_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    spark: Optional[SparkSession] = None
) -> Tuple[DataFrame, Dict[str, Any]]:
    """
    Executes the full PySpark Tourism ETL Pipeline:
    1. Reads raw tourism CSV
    2. Validates schema and unpivots wide columns to long format
    3. Computes YoY growth with Window partitioning
    4. Validates data quality constraints
    5. Saves curated Parquet and quality report
    """
    close_spark_at_end = False
    if spark is None:
        spark = get_spark_session("TravelWise-Tourism-ETL")
        close_spark_at_end = True

    base_dir = Path(__file__).resolve().parents[2]
    if input_csv_path is None:
        input_csv = base_dir / "data" / "raw" / "tourism" / "india_tourism_statewise_2018_2022.csv"
    else:
        input_csv = Path(input_csv_path)

    if output_dir is None:
        out_dir = base_dir / "data" / "processed" / "tourism"
    else:
        out_dir = Path(output_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_csv.exists():
        raise TourismPipelineError(f"Input tourism CSV does not exist: {input_csv}")

    logger.info(f"Reading raw tourism data from {input_csv}")
    raw_df = spark.read.csv(str(input_csv), header=True, inferSchema=False)
    raw_rows_count = raw_df.count()

    # Step 1: Unpivot
    unpivoted_df = unpivot_tourism_data(raw_df)

    # Step 2: Compute YoY Growth
    curated_df = compute_yoy_growth(unpivoted_df)

    # Step 3: Validate
    quality_metrics = validate_tourism_curated(curated_df)
    quality_metrics["input_csv"] = str(input_csv)
    quality_metrics["input_rows"] = raw_rows_count
    quality_metrics["output_rows"] = quality_metrics["total_records"]
    quality_metrics["output_dir"] = str(out_dir)

    # Step 4: Save Curated Parquet using pyarrow engine for guaranteed Windows compatibility
    parquet_path = out_dir / "india_tourism_statewise_normalized.parquet"
    curated_pdf = curated_df.toPandas()
    curated_pdf.to_parquet(str(parquet_path), engine="pyarrow", index=False)
    logger.info(f"Successfully saved normalized tourism Parquet to {parquet_path}")

    # Step 5: Save Quality Report
    report_json = out_dir / "quality_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(quality_metrics, f, indent=2)

    report_md = out_dir / "quality_report.md"
    report_content = f"""# Tourism ETL Pipeline Quality Report

- **Input File**: `{quality_metrics['input_csv']}`
- **Input Raw Rows**: {quality_metrics['input_rows']}
- **Output Curated Rows**: {quality_metrics['output_rows']}
- **Distinct Entities**: {quality_metrics['distinct_states']} (28 States + 8 UTs + 1 Total India)
- **Output Parquet**: `{parquet_path}`
- **Duplicate Records**: {quality_metrics['duplicate_records']}
- **Negative Value Records**: {quality_metrics['negative_records']}
- **Null Visit Counts**: {quality_metrics['null_visit_counts']} (Expected: Ladakh 2018 Domestic & Foreign only)
- **Null YoY Growth Records**: {quality_metrics['null_yoy_growth_records']} (All 2018 records + Ladakh 2019)
- **Official Aggregate Records (Total India)**: {quality_metrics['aggregate_records']}
- **Estimated Records (Maharashtra & Delhi 2022)**: {quality_metrics['estimated_records']}
"""
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(report_content)

    if close_spark_at_end:
        spark.stop()

    return curated_df, quality_metrics
