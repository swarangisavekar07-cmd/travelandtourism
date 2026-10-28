import pytest
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.pipeline.spark_session import get_spark_session
from src.pipeline.monument_pipeline import (
    validate_raw_monument_columns,
    process_monument_data,
    compute_monument_metrics,
    validate_monument_curated,
    MonumentPipelineError,
    run_monument_pipeline,
)

@pytest.fixture(scope="session")
def spark_session():
    """Shared SparkSession fixture for pipeline tests."""
    spark = get_spark_session("Pytest-Monument-Pipeline")
    yield spark
    spark.stop()

@pytest.fixture
def synthetic_raw_monument_spark_df(spark_session):
    """
    Creates synthetic raw monument DataFrame for testing PySpark transformations.
    Includes:
    - Normal site with both years
    - Site with legitimate nulls in year 1
    - Duplicate natural key to verify deduplication
    """
    data = [
        (1, "Site Alpha", "Agra", "Uttar Pradesh", "2022-23", 100000, 10000, 110000, "Source A"),
        (1, "Site Alpha", "Agra", "Uttar Pradesh", "2023-24", 150000, 20000, 170000, "Source A"),
        (1, "Site Alpha", "Agra", "Uttar Pradesh", "2023-24", 150000, 20000, 170000, "Source A"),  # Intentional dupe
        (2, "Site Beta", "Delhi", "Delhi", "2022-23", None, None, None, "Source B"),  # Legitimate null
        (2, "Site Beta", "Delhi", "Delhi", "2023-24", 50000, 5000, 55000, "Source B"),
    ]
    columns = [
        "serial_number",
        "monument_name",
        "circle",
        "state_or_region",
        "financial_year",
        "domestic_visitors",
        "foreign_visitors",
        "total_visitors",
        "source",
    ]
    return spark_session.createDataFrame(data, columns)

def test_validate_raw_monument_columns_success():
    valid_cols = [
        "monument_name",
        "circle",
        "state_or_region",
        "financial_year",
        "domestic_visitors",
        "foreign_visitors",
        "total_visitors",
        "source",
    ]
    validate_raw_monument_columns(valid_cols)

def test_validate_raw_monument_columns_missing():
    invalid_cols = ["monument_name", "circle", "financial_year"]
    with pytest.raises(MonumentPipelineError, match="Missing required columns"):
        validate_raw_monument_columns(invalid_cols)

def test_process_monument_data(synthetic_raw_monument_spark_df):
    processed = process_monument_data(synthetic_raw_monument_spark_df)

    assert set(processed.columns) == {
        "serial_number",
        "monument_name",
        "circle",
        "state_or_region",
        "financial_year",
        "domestic_visitors",
        "foreign_visitors",
        "total_visitors",
        "source",
    }
    # Duplicate for Site Alpha in 2023-24 must be removed (4 records remaining)
    assert processed.count() == 4

    # Legitimate nulls preserved
    beta_22 = processed.filter((F.col("monument_name") == "Site Beta") & (F.col("financial_year") == "2022-23")).first()
    assert beta_22["domestic_visitors"] is None
    assert beta_22["foreign_visitors"] is None
    assert beta_22["total_visitors"] is None

def test_compute_monument_metrics(synthetic_raw_monument_spark_df):
    processed = process_monument_data(synthetic_raw_monument_spark_df)
    curated = compute_monument_metrics(processed)

    assert "prev_year_total_visitors" in curated.columns
    assert "yoy_growth_pct" in curated.columns
    assert "foreign_visitor_share_pct" in curated.columns

    # Check YoY calculation for Site Alpha in 2023-24:
    # 2022-23 total = 110,000; 2023-24 total = 170,000 -> Growth = (60000 / 110000) * 100 = 54.55%
    alpha_23 = curated.filter((F.col("monument_name") == "Site Alpha") & (F.col("financial_year") == "2023-24")).first()
    assert alpha_23["prev_year_total_visitors"] == 110000
    assert alpha_23["yoy_growth_pct"] == 54.55
    # Foreign share = (20000 / 170000) * 100 = 11.76%
    assert alpha_23["foreign_visitor_share_pct"] == 11.76

    # Base year 2022-23 has null YoY growth
    alpha_22 = curated.filter((F.col("monument_name") == "Site Alpha") & (F.col("financial_year") == "2022-23")).first()
    assert alpha_22["prev_year_total_visitors"] is None
    assert alpha_22["yoy_growth_pct"] is None

def test_validate_monument_curated_negative_rejection(spark_session):
    bad_data = [
        ("Site Neg", "Circle", "State", "2023-24", -10, 5, 5, "Source")
    ]
    cols = ["monument_name", "circle", "state_or_region", "financial_year", "domestic_visitors", "foreign_visitors", "total_visitors", "source"]
    df = spark_session.createDataFrame(bad_data, cols)
    df_curated = df.withColumn("prev_year_total_visitors", F.lit(None)).withColumn("yoy_growth_pct", F.lit(None)).withColumn("foreign_visitor_share_pct", F.lit(None))

    with pytest.raises(MonumentPipelineError, match="Found negative visitor counts"):
        validate_monument_curated(df_curated)

def test_validate_monument_curated_invalid_financial_year(spark_session):
    bad_year = [
        ("Site FY", "Circle", "State", "1999-00", 100, 10, 110, "Source")
    ]
    cols = ["monument_name", "circle", "state_or_region", "financial_year", "domestic_visitors", "foreign_visitors", "total_visitors", "source"]
    df = spark_session.createDataFrame(bad_year, cols)
    df_curated = df.withColumn("prev_year_total_visitors", F.lit(None)).withColumn("yoy_growth_pct", F.lit(None)).withColumn("foreign_visitor_share_pct", F.lit(None))

    with pytest.raises(MonumentPipelineError, match="Invalid financial years found"):
        validate_monument_curated(df_curated)

def test_real_monument_pipeline_execution(spark_session, tmp_path):
    """Executes the full pipeline against official raw JSON dataset and verifies output integrity."""
    out_dir = tmp_path / "monuments_curated_test"
    curated_df, metrics = run_monument_pipeline(output_dir=str(out_dir), spark=spark_session)

    assert curated_df.count() == 290
    assert metrics["total_records"] == 290
    assert metrics["distinct_monuments"] == 145
    assert metrics["distinct_circles"] == 33
    assert metrics["negative_records"] == 0
    assert metrics["duplicate_records"] == 0

    # Official reconciliation check
    assert metrics["reconciliation"]["2022-23"]["domestic_visitors"] == 47901021
    assert metrics["reconciliation"]["2022-23"]["foreign_visitors"] == 1445363
    assert metrics["reconciliation"]["2023-24"]["domestic_visitors"] == 53090007
    assert metrics["reconciliation"]["2023-24"]["foreign_visitors"] == 2314641

    parquet_file = out_dir / "asi_monument_visitors_normalized.parquet"
    assert parquet_file.exists()
    quality_json = out_dir / "quality_report.json"
    assert quality_json.exists()
