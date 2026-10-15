import pytest
from pathlib import Path
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.pipeline.spark_session import get_spark_session
from src.pipeline.tourism_pipeline import (
    validate_raw_tourism_columns,
    unpivot_tourism_data,
    compute_yoy_growth,
    validate_tourism_curated,
    TourismPipelineError,
    run_tourism_pipeline,
)

@pytest.fixture(scope="session")
def spark_session():
    """Shared SparkSession fixture for pipeline tests."""
    spark = get_spark_session("Pytest-Tourism-Pipeline")
    yield spark
    spark.stop()

@pytest.fixture
def synthetic_raw_tourism_spark_df(spark_session, tmp_path):
    """
    Creates synthetic wide raw tourism DataFrame for testing.
    Includes:
    - Normal state
    - State with null 2018 (like Ladakh)
    - Total India aggregate
    """
    data = [
        ("StateA", "Domestic", "1000", "1200", "600", "800", "1600"),
        ("StateA", "Foreign", "100", "110", "50", "60", "120"),
        ("StateB", "Domestic", None, "500", "300", "400", "800"),  # Null in 2018
        ("StateB", "Foreign", None, "50", "20", "30", "60"),
        ("Total India", "Domestic", "10000", "12000", "6000", "8000", "16000"),
        ("Total India", "Foreign", "1000", "1100", "500", "600", "1200"),
    ]
    columns = ["State/UT", "Category", "2018", "2019", "2020", "2021", "2022"]
    return spark_session.createDataFrame(data, columns)

def test_validate_raw_tourism_columns_success():
    valid_cols = ["State/UT", "Category", "2018", "2019", "2020", "2021", "2022"]
    # Should not raise
    validate_raw_tourism_columns(valid_cols)

def test_validate_raw_tourism_columns_missing():
    invalid_cols = ["State/UT", "Category", "2018", "2019"]
    with pytest.raises(TourismPipelineError, match="Missing required columns"):
        validate_raw_tourism_columns(invalid_cols)

def test_unpivot_tourism_data(synthetic_raw_tourism_spark_df):
    unpivoted = unpivot_tourism_data(synthetic_raw_tourism_spark_df)

    assert set(unpivoted.columns) == {
        "state", "category", "year", "visit_count",
        "is_aggregate", "entity_type", "is_estimated"
    }

    # 6 input rows * 5 years = 30 unpivoted rows
    assert unpivoted.count() == 30

    # Verify null preservation: StateB 2018 must be None, NOT zero
    state_b_2018 = unpivoted.filter(
        (F.col("state") == "StateB") & (F.col("year") == 2018) & (F.col("category") == "Domestic")
    ).collect()
    assert len(state_b_2018) == 1
    assert state_b_2018[0]["visit_count"] is None

    # Verify aggregate classification
    tot_india = unpivoted.filter(F.col("state") == "Total India").collect()
    for row in tot_india:
        assert row["is_aggregate"] is True
        assert row["entity_type"] == "AGGREGATE_TOTAL"

    state_a = unpivoted.filter(F.col("state") == "StateA").collect()
    for row in state_a:
        assert row["is_aggregate"] is False
        assert row["entity_type"] == "STATE_OR_UT"

def test_compute_yoy_growth(synthetic_raw_tourism_spark_df):
    unpivoted = unpivot_tourism_data(synthetic_raw_tourism_spark_df)
    curated = compute_yoy_growth(unpivoted)

    # First year (2018) must have None growth
    state_a_2018 = curated.filter(
        (F.col("state") == "StateA") & (F.col("category") == "Domestic") & (F.col("year") == 2018)
    ).collect()[0]
    assert state_a_2018["yoy_growth_pct"] is None

    # 2019 growth for StateA Domestic: (1200 - 1000)/1000 * 100 = 20.0%
    state_a_2019 = curated.filter(
        (F.col("state") == "StateA") & (F.col("category") == "Domestic") & (F.col("year") == 2019)
    ).collect()[0]
    assert state_a_2019["yoy_growth_pct"] == 20.0

    # 2020 growth for StateA Domestic: (600 - 1200)/1200 * 100 = -50.0%
    state_a_2020 = curated.filter(
        (F.col("state") == "StateA") & (F.col("category") == "Domestic") & (F.col("year") == 2020)
    ).collect()[0]
    assert state_a_2020["yoy_growth_pct"] == -50.0

    # StateB: 2018 is null -> 2019 has no previous year value, so growth must be None
    state_b_2019 = curated.filter(
        (F.col("state") == "StateB") & (F.col("category") == "Domestic") & (F.col("year") == 2019)
    ).collect()[0]
    assert state_b_2019["yoy_growth_pct"] is None

    # StateB 2020: current 300, prev 500 -> (300 - 500)/500 * 100 = -40.0%
    state_b_2020 = curated.filter(
        (F.col("state") == "StateB") & (F.col("category") == "Domestic") & (F.col("year") == 2020)
    ).collect()[0]
    assert state_b_2020["yoy_growth_pct"] == -40.0

def test_validate_tourism_curated_duplicate_detection(spark_session):
    schema = "state string, category string, year int, visit_count bigint, is_aggregate boolean, entity_type string, is_estimated boolean, yoy_growth_pct double"
    # Intentional duplicate tuple (StateA, Domestic, 2018)
    data = [
        ("StateA", "Domestic", 2018, 1000, False, "STATE_OR_UT", False, None),
        ("StateA", "Domestic", 2018, 1000, False, "STATE_OR_UT", False, None),
    ]
    dup_df = spark_session.createDataFrame(data, schema=schema)

    with pytest.raises(TourismPipelineError, match="duplicate"):
        validate_tourism_curated(dup_df)

def test_validate_tourism_curated_negative_detection(spark_session):
    schema = "state string, category string, year int, visit_count bigint, is_aggregate boolean, entity_type string, is_estimated boolean, yoy_growth_pct double"
    data = [
        ("StateA", "Domestic", 2018, -500, False, "STATE_OR_UT", False, None),
    ]
    neg_df = spark_session.createDataFrame(data, schema=schema)

    with pytest.raises(TourismPipelineError, match="negative visit counts"):
        validate_tourism_curated(neg_df)

def test_real_tourism_pipeline_execution(spark_session, tmp_path):
    out_dir = tmp_path / "processed_tourism"
    df, report = run_tourism_pipeline(output_dir=str(out_dir), spark=spark_session)

    assert df.count() == 370  # 74 entities * 5 years
    assert report["total_records"] == 370
    assert report["distinct_states"] == 37
    assert report["duplicate_records"] == 0
    assert report["null_visit_counts"] == 2  # Ladakh 2018 Domestic & Foreign only

    parquet_file = out_dir / "india_tourism_statewise_normalized.parquet"
    assert parquet_file.exists()
    assert (out_dir / "quality_report.json").exists()
    assert (out_dir / "quality_report.md").exists()
