"""
TravelWise Database Module.
Provides SQLAlchemy ORM models, connection management, schema initialization,
and idempotent loading functions for PostgreSQL integration.
"""

from src.database.config import DatabaseSettings, get_db_settings
from src.database.models import (
    Base,
    TourismStatewiseAnnual,
    WeatherDailyForecast,
)
from src.database.connection import (
    get_engine,
    get_session_factory,
    get_db_session,
    check_database_connection,
)
from src.database.loader import (
    create_all_tables,
    drop_all_tables,
    load_curated_tourism_to_db,
    load_curated_weather_to_db,
    verify_database_counts,
)

__all__ = [
    "DatabaseSettings",
    "get_db_settings",
    "Base",
    "TourismStatewiseAnnual",
    "WeatherDailyForecast",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "check_database_connection",
    "create_all_tables",
    "drop_all_tables",
    "load_curated_tourism_to_db",
    "load_curated_weather_to_db",
    "verify_database_counts",
]
