"""
Data loader module for TravelWise PostgreSQL database integration.
Provides idempotent loading of curated Parquet datasets (tourism and weather)
into relational tables with conflict handling (upsert) and data verification.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from sqlalchemy import select, func, distinct
from sqlalchemy.engine import Engine

from src.database.connection import get_engine, get_db_session
from src.database.models import Base, TourismStatewiseAnnual, WeatherDailyForecast

logger = logging.getLogger(__name__)

# Default file paths for curated datasets
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TOURIISM_PARQUET = PROJECT_ROOT / "data" / "processed" / "tourism" / "india_tourism_statewise_normalized.parquet"
DEFAULT_WEATHER_PARQUET = PROJECT_ROOT / "data" / "processed" / "weather" / "daily_weather_forecast_curated.parquet"


def create_all_tables(engine: Optional[Engine] = None) -> None:
    """Creates all defined database tables if they do not already exist."""
    eng = engine or get_engine()
    logger.info(f"Creating all database tables using engine {eng.url}...")
    Base.metadata.create_all(bind=eng)
    logger.info("Database tables initialized successfully.")


def drop_all_tables(engine: Optional[Engine] = None) -> None:
    """Drops all defined database tables."""
    eng = engine or get_engine()
    logger.warning(f"Dropping all database tables using engine {eng.url}...")
    Base.metadata.drop_all(bind=eng)
    logger.info("Database tables dropped.")


def _clean_dataframe_for_sql(df: pd.DataFrame, int_cols: List[str]) -> List[Dict[str, Any]]:
    """
    Converts DataFrame records to dictionary objects suitable for SQL insertion.
    Preserves None for NaN/null values and casts numeric columns cleanly.
    """
    records = df.to_dict(orient="records")
    cleaned_records = []

    for row in records:
        cleaned_row = {}
        for key, val in row.items():
            if pd.isna(val):
                cleaned_row[key] = None
            elif key in int_cols and val is not None:
                cleaned_row[key] = int(val)
            elif isinstance(val, (np.floating, float)):
                cleaned_row[key] = float(val)
            elif isinstance(val, (np.integer, int)):
                cleaned_row[key] = int(val)
            elif isinstance(val, (np.bool_, bool)):
                cleaned_row[key] = bool(val)
            else:
                cleaned_row[key] = str(val) if val is not None else None
        cleaned_records.append(cleaned_row)

    return cleaned_records


def _execute_upsert(
    engine: Engine,
    model: Any,
    records: List[Dict[str, Any]],
    conflict_columns: List[str],
    batch_size: int = 500,
) -> int:
    """
    Executes an idempotent upsert (INSERT ... ON CONFLICT DO UPDATE).
    Supports PostgreSQL and SQLite dialects.
    """
    if not records:
        return 0

    dialect_name = engine.dialect.name
    total_processed = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]

        with engine.begin() as conn:
            if dialect_name == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                stmt = pg_insert(model).values(batch)
                update_cols = {
                    col.name: col
                    for col in stmt.excluded
                    if col.name not in ("id", "created_at")
                }
                update_cols["updated_at"] = func.now()
                stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_columns,
                    set_=update_cols,
                )
                conn.execute(stmt)

            elif dialect_name == "sqlite":
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                stmt = sqlite_insert(model).values(batch)
                update_cols = {
                    col.name: col
                    for col in stmt.excluded
                    if col.name not in ("id", "created_at")
                }
                update_cols["updated_at"] = func.now()
                stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_columns,
                    set_=update_cols,
                )
                conn.execute(stmt)

            else:
                # Fallback for standard SQL: Simple insert
                from sqlalchemy import insert
                stmt = insert(model).values(batch)
                conn.execute(stmt)

        total_processed += len(batch)

    return total_processed


def load_curated_tourism_to_db(
    parquet_path: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> int:
    """
    Loads curated statewise tourism records from Parquet into PostgreSQL.
    Uses ON CONFLICT (state, category, year) DO UPDATE to prevent duplicate rows.
    Preserves null visit counts and aggregate classifications.
    """
    path = Path(parquet_path) if parquet_path else DEFAULT_TOURIISM_PARQUET
    if not path.exists():
        raise FileNotFoundError(f"Curated tourism Parquet file not found at: {path}")

    logger.info(f"Reading curated tourism dataset from: {path}")
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df)} tourism records from Parquet.")

    # Clean records, casting integer columns where not null
    int_cols = ["year", "visit_count", "prev_year_visit_count"]
    records = _clean_dataframe_for_sql(df, int_cols)

    eng = engine or get_engine()
    conflict_cols = ["state", "category", "year"]

    processed = _execute_upsert(
        engine=eng,
        model=TourismStatewiseAnnual,
        records=records,
        conflict_columns=conflict_cols,
    )
    logger.info(f"Successfully upserted {processed} tourism records into database.")
    return processed


def load_curated_weather_to_db(
    parquet_path: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> int:
    """
    Loads curated daily weather forecasts from Parquet into PostgreSQL.
    Uses ON CONFLICT (destination, forecast_date) DO UPDATE to prevent duplicate rows.
    Preserves numerical metrics, metadata, and forecast indicators.
    """
    path = Path(parquet_path) if parquet_path else DEFAULT_WEATHER_PARQUET
    if not path.exists():
        raise FileNotFoundError(f"Curated weather Parquet file not found at: {path}")

    logger.info(f"Reading curated weather dataset from: {path}")
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df)} daily weather forecast records from Parquet.")

    # Clean records, casting integer columns where not null
    int_cols = ["hourly_records_count", "max_precipitation_probability_pct"]
    records = _clean_dataframe_for_sql(df, int_cols)

    eng = engine or get_engine()
    conflict_cols = ["destination", "forecast_date"]

    processed = _execute_upsert(
        engine=eng,
        model=WeatherDailyForecast,
        records=records,
        conflict_columns=conflict_cols,
    )
    logger.info(f"Successfully upserted {processed} weather forecast records into database.")
    return processed


def verify_database_counts(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Queries the database and computes validation metrics for tourism and weather tables.
    Returns a comprehensive dictionary of verification statistics.
    """
    eng = engine or get_engine()

    with eng.connect() as conn:
        # Tourism Metrics
        total_tourism = conn.execute(
            select(func.count(TourismStatewiseAnnual.id))
        ).scalar() or 0

        state_level_tourism = conn.execute(
            select(func.count(TourismStatewiseAnnual.id)).where(
                TourismStatewiseAnnual.is_aggregate == False
            )
        ).scalar() or 0

        aggregate_tourism = conn.execute(
            select(func.count(TourismStatewiseAnnual.id)).where(
                TourismStatewiseAnnual.is_aggregate == True
            )
        ).scalar() or 0

        distinct_states = conn.execute(
            select(func.count(distinct(TourismStatewiseAnnual.state))).where(
                TourismStatewiseAnnual.is_aggregate == False
            )
        ).scalar() or 0

        null_visit_counts = conn.execute(
            select(func.count(TourismStatewiseAnnual.id)).where(
                TourismStatewiseAnnual.visit_count.is_(None)
            )
        ).scalar() or 0

        tourism_years_raw = conn.execute(
            select(distinct(TourismStatewiseAnnual.year)).order_by(TourismStatewiseAnnual.year)
        ).fetchall()
        tourism_years = [r[0] for r in tourism_years_raw]

        # Weather Metrics
        total_weather = conn.execute(
            select(func.count(WeatherDailyForecast.id))
        ).scalar() or 0

        distinct_destinations_raw = conn.execute(
            select(distinct(WeatherDailyForecast.destination)).order_by(WeatherDailyForecast.destination)
        ).fetchall()
        destinations = [r[0] for r in distinct_destinations_raw]

        distinct_dates_count = conn.execute(
            select(func.count(distinct(WeatherDailyForecast.forecast_date)))
        ).scalar() or 0

        non_forecast_count = conn.execute(
            select(func.count(WeatherDailyForecast.id)).where(
                WeatherDailyForecast.is_forecast == False
            )
        ).scalar() or 0

    return {
        "tourism_total_count": total_tourism,
        "tourism_state_count": state_level_tourism,
        "tourism_aggregate_count": aggregate_tourism,
        "tourism_distinct_states": distinct_states,
        "tourism_null_visit_count": null_visit_counts,
        "tourism_years": tourism_years,
        "weather_total_count": total_weather,
        "weather_distinct_destinations": len(destinations),
        "weather_destinations": destinations,
        "weather_distinct_dates": distinct_dates_count,
        "weather_all_forecast": (non_forecast_count == 0 and total_weather > 0),
    }
