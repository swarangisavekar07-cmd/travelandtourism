import pytest
import json
from pathlib import Path
from pyspark.sql import SparkSession

from src.pipeline.spark_session import get_spark_session
from src.pipeline.weather_pipeline import (
    parse_weather_json_record,
    aggregate_daily_weather,
    WeatherPipelineError,
    run_weather_pipeline,
)

@pytest.fixture(scope="session")
def spark_session():
    """Shared SparkSession fixture for pipeline tests."""
    spark = get_spark_session("Pytest-Weather-Pipeline")
    yield spark
    spark.stop()

@pytest.fixture
def synthetic_weather_json(tmp_path):
    """
    Creates a synthetic Open-Meteo weather response JSON for testing.
    Spans 2 days with 4 hourly points each.
    """
    payload = {
        "metadata": {
            "destination_name": "TestVille",
            "latitude": 19.5,
            "longitude": 73.8,
            "retrieved_at_utc": "2026-10-10T12:00:00+00:00",
            "source_api": "https://api.open-meteo.com/v1/forecast"
        },
        "raw_response": {
            "latitude": 19.5,
            "longitude": 73.8,
            "hourly": {
                "time": [
                    "2026-10-10T00:00", "2026-10-10T06:00", "2026-10-10T12:00", "2026-10-10T18:00",
                    "2026-10-11T00:00", "2026-10-11T06:00", "2026-10-11T12:00", "2026-10-11T18:00"
                ],
                "temperature_2m": [20.0, 22.0, 28.0, 24.0, 18.0, 21.0, 26.0, 23.0],
                "precipitation_probability": [0, 10, 40, 20, 5, 15, 60, 30],
                "precipitation": [0.0, 0.5, 2.5, 1.0, 0.0, 0.2, 4.8, 1.0],
                "wind_speed_10m": [5.0, 8.0, 12.0, 7.0, 4.0, 6.0, 15.0, 9.0]
            }
        }
    }
    file_path = tmp_path / "weather_testville_20261010.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return str(file_path)

def test_parse_weather_json_record_success(synthetic_weather_json):
    records = parse_weather_json_record(synthetic_weather_json)

    assert len(records) == 8
    first = records[0]
    assert first["destination"] == "TestVille"
    assert first["latitude"] == 19.5
    assert first["longitude"] == 73.8
    assert first["retrieved_at_utc"] == "2026-10-10T12:00:00+00:00"
    assert first["forecast_date"] == "2026-10-10"
    assert first["temperature_2m"] == 20.0
    assert first["precipitation"] == 0.0

def test_parse_weather_json_record_missing_fields(tmp_path):
    bad_payload = {
        "metadata": {"destination_name": "BadCity"},
        "raw_response": {"hourly": {"time": ["2026-10-10T00:00"]}}  # missing temperature, etc.
    }
    bad_file = tmp_path / "weather_badcity.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(bad_payload, f)

    with pytest.raises(WeatherPipelineError, match="Missing required hourly fields"):
        parse_weather_json_record(str(bad_file))

def test_aggregate_daily_weather(spark_session, synthetic_weather_json):
    hourly_records = parse_weather_json_record(synthetic_weather_json)
    daily_df = aggregate_daily_weather(spark_session, hourly_records)

    assert daily_df.count() == 2  # 2 distinct dates: 2026-10-10 and 2026-10-11

    rows = daily_df.collect()
    day1 = [r for r in rows if r["forecast_date"] == "2026-10-10"][0]

    assert day1["destination"] == "TestVille"
    assert day1["hourly_records_count"] == 4
    assert day1["temp_min_c"] == 20.0
    assert day1["temp_max_c"] == 28.0
    assert day1["temp_avg_c"] == 23.5  # (20 + 22 + 28 + 24) / 4
    assert day1["total_precipitation_mm"] == 4.0  # 0.0 + 0.5 + 2.5 + 1.0
    assert day1["max_precipitation_probability_pct"] == 40
    assert day1["max_wind_speed_kmh"] == 12.0
    assert day1["is_forecast"] is True

def test_real_weather_pipeline_execution(spark_session, tmp_path):
    out_dir = tmp_path / "processed_weather"
    daily_df, report = run_weather_pipeline(output_dir=str(out_dir), spark=spark_session)

    assert daily_df.count() > 0
    assert report["raw_json_files_found"] >= 3
    assert set(report["destinations_covered"]) >= {"Lonavala", "Mahabaleshwar", "Matheran"}
    assert report["is_forecast_metric"] is True
    assert report["climatology_claimed"] is False

    parquet_file = out_dir / "daily_weather_forecast_curated.parquet"
    assert parquet_file.exists()
    assert (out_dir / "quality_report.json").exists()
    assert (out_dir / "quality_report.md").exists()
