import os
import glob
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
import pandas as pd

from src.pipeline.spark_session import get_spark_session

logger = logging.getLogger(__name__)

REQUIRED_HOURLY_FIELDS = ["time", "temperature_2m", "precipitation_probability", "precipitation", "wind_speed_10m"]

class WeatherPipelineError(Exception):
    """Custom exception raised for Weather ETL Pipeline failures."""
    pass

def parse_weather_json_record(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses a single raw weather JSON file into flat hourly records.
    Preserves destination metadata, coordinates, and retrieval timestamp.
    Validates that required hourly fields exist.
    """
    p = Path(file_path)
    if not p.exists():
        raise WeatherPipelineError(f"Weather JSON file not found: {file_path}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    raw_resp = data.get("raw_response", {})
    hourly = raw_resp.get("hourly", {})

    destination = metadata.get("destination_name", "Unknown")
    latitude = metadata.get("latitude", raw_resp.get("latitude"))
    longitude = metadata.get("longitude", raw_resp.get("longitude"))
    retrieved_at_utc = metadata.get("retrieved_at_utc")
    source_api = metadata.get("source_api", "https://api.open-meteo.com/v1/forecast")

    # Validate fields
    missing_fields = [f for f in REQUIRED_HOURLY_FIELDS if f not in hourly]
    if missing_fields:
        raise WeatherPipelineError(f"Missing required hourly fields in {file_path}: {missing_fields}")

    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    precip_probs = hourly.get("precipitation_probability", [])
    precips = hourly.get("precipitation", [])
    winds = hourly.get("wind_speed_10m", [])

    num_records = len(times)
    records = []
    for i in range(num_records):
        iso_time = times[i]
        date_part = iso_time.split("T")[0] if "T" in iso_time else iso_time.split(" ")[0]
        hour_part = iso_time.split("T")[1] if "T" in iso_time else ""

        records.append({
            "destination": destination,
            "latitude": float(latitude) if latitude is not None else None,
            "longitude": float(longitude) if longitude is not None else None,
            "retrieved_at_utc": retrieved_at_utc,
            "source_api": source_api,
            "forecast_time": iso_time,
            "forecast_date": date_part,
            "forecast_hour": hour_part,
            "temperature_2m": float(temps[i]) if temps[i] is not None else None,
            "precipitation_probability": int(precip_probs[i]) if precip_probs[i] is not None else None,
            "precipitation": float(precips[i]) if precips[i] is not None else None,
            "wind_speed_10m": float(winds[i]) if winds[i] is not None else None
        })

    return records

def load_and_deduplicate_raw_weather(raw_dir: str) -> List[Dict[str, Any]]:
    """
    Scans raw directory for weather_*.json files.
    Groups files by destination and uses the latest retrieved snapshot for each destination.
    Returns all hourly records.
    """
    p = Path(raw_dir)
    json_files = sorted(glob.glob(str(p / "weather_*.json")))
    if not json_files:
        raise WeatherPipelineError(f"No weather_*.json files found in {raw_dir}")

    # Group by destination and select latest file per destination
    dest_to_latest_file: Dict[str, Tuple[str, str]] = {}
    for fpath in json_files:
        with open(fpath, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        dest = d.get("metadata", {}).get("destination_name", "Unknown").lower()
        retrieved = d.get("metadata", {}).get("retrieved_at_utc", "")
        if dest not in dest_to_latest_file or retrieved > dest_to_latest_file[dest][0]:
            dest_to_latest_file[dest] = (retrieved, fpath)

    all_hourly_records: List[Dict[str, Any]] = []
    for dest, (retrieved, latest_path) in dest_to_latest_file.items():
        logger.info(f"Loading latest snapshot for {dest}: {latest_path} (retrieved: {retrieved})")
        recs = parse_weather_json_record(latest_path)
        all_hourly_records.extend(recs)

    return all_hourly_records

def aggregate_daily_weather(spark: SparkSession, hourly_records: List[Dict[str, Any]]) -> DataFrame:
    """
    Converts hourly weather records into PySpark DataFrame and computes daily aggregates:
    - temp_min, temp_max, temp_avg
    - total_precipitation
    - max_precipitation_probability, avg_precipitation_probability
    - avg_wind_speed, max_wind_speed
    - hourly_records_count
    Clearly labels dataset as short-term forecast (NOT historical climatology).
    """
    if not hourly_records:
        raise WeatherPipelineError("No hourly weather records provided for aggregation.")

    hourly_df = spark.createDataFrame(hourly_records)

    daily_df = hourly_df.groupBy("destination", "forecast_date").agg(
        F.first("latitude").alias("latitude"),
        F.first("longitude").alias("longitude"),
        F.max("retrieved_at_utc").alias("latest_retrieved_at_utc"),
        F.first("source_api").alias("source_api"),
        F.count("forecast_time").alias("hourly_records_count"),
        F.round(F.min("temperature_2m"), 2).alias("temp_min_c"),
        F.round(F.max("temperature_2m"), 2).alias("temp_max_c"),
        F.round(F.avg("temperature_2m"), 2).alias("temp_avg_c"),
        F.round(F.sum("precipitation"), 2).alias("total_precipitation_mm"),
        F.max("precipitation_probability").alias("max_precipitation_probability_pct"),
        F.round(F.avg("precipitation_probability"), 2).alias("avg_precipitation_probability_pct"),
        F.round(F.avg("wind_speed_10m"), 2).alias("avg_wind_speed_kmh"),
        F.round(F.max("wind_speed_10m"), 2).alias("max_wind_speed_kmh")
    ).withColumn(
        "metric_type", F.lit("7_DAY_HOURLY_FORECAST_DAILY_AGGREGATE")
    ).withColumn(
        "is_forecast", F.lit(True)
    ).orderBy("destination", "forecast_date")

    return daily_df

def run_weather_pipeline(
    raw_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    spark: Optional[SparkSession] = None
) -> Tuple[DataFrame, Dict[str, Any]]:
    """
    Executes the full PySpark Weather ETL Pipeline:
    1. Loads raw JSON files from data/raw/
    2. Parses hourly forecast fields with validation
    3. Computes daily aggregates using PySpark
    4. Saves curated daily weather Parquet
    5. Saves quality inspection report
    """
    close_spark_at_end = False
    if spark is None:
        spark = get_spark_session("TravelWise-Weather-ETL")
        close_spark_at_end = True

    base_dir = Path(__file__).resolve().parents[2]
    if raw_dir is None:
        in_dir = base_dir / "data" / "raw"
    else:
        in_dir = Path(raw_dir)

    if output_dir is None:
        out_dir = base_dir / "data" / "processed" / "weather"
    else:
        out_dir = Path(output_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1 & 2: Parse raw JSONs
    hourly_records = load_and_deduplicate_raw_weather(str(in_dir))
    raw_files_count = len(glob.glob(str(in_dir / "weather_*.json")))

    # Step 3: Compute daily aggregates
    daily_df = aggregate_daily_weather(spark, hourly_records)
    total_daily_records = daily_df.count()

    # Step 4: Quality Metrics
    destinations = [r["destination"] for r in daily_df.select("destination").distinct().collect()]
    null_temp = daily_df.filter(F.col("temp_avg_c").isNull()).count()
    null_precip = daily_df.filter(F.col("total_precipitation_mm").isNull()).count()

    quality_metrics = {
        "raw_json_files_found": raw_files_count,
        "hourly_records_parsed": len(hourly_records),
        "total_daily_forecast_records": total_daily_records,
        "destinations_covered": destinations,
        "null_temperature_records": null_temp,
        "null_precipitation_records": null_precip,
        "is_forecast_metric": True,
        "climatology_claimed": False,
        "output_dir": str(out_dir)
    }

    # Step 5: Save Curated Parquet using pyarrow
    parquet_path = out_dir / "daily_weather_forecast_curated.parquet"
    daily_pdf = daily_df.toPandas()
    daily_pdf.to_parquet(str(parquet_path), engine="pyarrow", index=False)
    logger.info(f"Successfully saved curated daily weather Parquet to {parquet_path}")

    # Step 6: Save Quality Reports
    report_json = out_dir / "quality_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(quality_metrics, f, indent=2)

    report_md = out_dir / "quality_report.md"
    report_content = f"""# Weather ETL Pipeline Quality Report

- **Source Directory**: `{in_dir}`
- **Raw Forecast JSON Files Evaluated**: {quality_metrics['raw_json_files_found']}
- **Total Hourly Forecast Points Ingested**: {quality_metrics['hourly_records_parsed']}
- **Total Curated Daily Forecast Records**: {quality_metrics['total_daily_forecast_records']}
- **Destinations Covered**: {", ".join(quality_metrics['destinations_covered'])}
- **Output Parquet**: `{parquet_path}`
- **Null Temperature Records**: {quality_metrics['null_temperature_records']}
- **Null Precipitation Records**: {quality_metrics['null_precipitation_records']}
- **Dataset Classification**: Short-term 7-day numerical weather forecast (Open-Meteo API). Note: Historical climate/climatology is NOT claimed from these forecast snapshots.
"""
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(report_content)

    if close_spark_at_end:
        spark.stop()

    return daily_df, quality_metrics
