"""
TravelWise Data Pipeline Module.
Implements PySpark ETL pipelines for Historical Tourism and Live Weather analytics.
"""

from src.pipeline.spark_session import get_spark_session
from src.pipeline.tourism_pipeline import (
    run_tourism_pipeline,
    unpivot_tourism_data,
    compute_yoy_growth,
    validate_raw_tourism_columns,
    validate_tourism_curated,
)
from src.pipeline.weather_pipeline import (
    run_weather_pipeline,
    parse_weather_json_record,
    aggregate_daily_weather,
)
from src.pipeline.monument_pipeline import (
    run_monument_pipeline,
    process_monument_data,
    compute_monument_metrics,
    validate_monument_curated,
    MonumentPipelineError,
)

__all__ = [
    "get_spark_session",
    "run_tourism_pipeline",
    "unpivot_tourism_data",
    "compute_yoy_growth",
    "validate_raw_tourism_columns",
    "validate_tourism_curated",
    "run_weather_pipeline",
    "parse_weather_json_record",
    "aggregate_daily_weather",
    "run_monument_pipeline",
    "process_monument_data",
    "compute_monument_metrics",
    "validate_monument_curated",
    "MonumentPipelineError",
]
