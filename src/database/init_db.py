"""
CLI initialization and data ingestion script for TravelWise PostgreSQL database.
Handles table creation, dataset ingestion with upsert logic, and database verification.

Usage:
    python -m src.database.init_db --all
    python -m src.database.init_db --check-connection
    python -m src.database.init_db --create-tables
    python -m src.database.init_db --load-data
    python -m src.database.init_db --verify
"""

import sys
import argparse
import logging
from typing import Optional
from sqlalchemy.engine import Engine

from src.database.config import get_db_settings
from src.database.connection import get_engine, check_database_connection
from src.database.loader import (
    create_all_tables,
    load_curated_tourism_to_db,
    load_curated_weather_to_db,
    load_curated_monuments_to_db,
    verify_database_counts,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("init_db")


def print_postgres_setup_instructions() -> None:
    """Prints instructions for setting up PostgreSQL and configuring .env."""
    settings = get_db_settings()
    print("\n" + "=" * 70)
    print("  POSTGRESQL CONFIGURATION GUIDE FOR TRAVELWISE")
    print("=" * 70)
    print("PostgreSQL connection could not be established with current settings:")
    print(f"  Host: {settings.host}")
    print(f"  Port: {settings.port}")
    print(f"  Database: {settings.name}")
    print(f"  User: {settings.user}")
    print("\nTo configure PostgreSQL on your machine:")
    print("1. Ensure PostgreSQL is installed and the Windows Service is running.")
    print("   (Check Windows Services for 'postgresql-x64-18' or similar).")
    print("\n2. Create the TravelWise database using psql or pgAdmin:")
    print(f"   psql -U {settings.user} -c \"CREATE DATABASE {settings.name};\"")
    print("\n3. Create or update your .env file in the project root:")
    print("   DB_HOST=localhost")
    print("   DB_PORT=5432")
    print(f"   DB_NAME={settings.name}")
    print(f"   DB_USER={settings.user}")
    print("   DB_PASSWORD=your_actual_postgres_password")
    print("\n4. Re-run this initialization script:")
    print("   python -m src.database.init_db --all")
    print("=" * 70 + "\n")


def run_check_connection() -> bool:
    """Performs connection health check and prints diagnostic results."""
    print("\n[Step: Health Check] Verifying database connectivity...")
    ok, message = check_database_connection()
    if ok:
        print(f"SUCCESS: {message}")
        return True
    else:
        print(f"WARNING: {message}")
        print_postgres_setup_instructions()
        return False


def run_create_tables(engine: Optional[Engine] = None) -> bool:
    """Creates database schema tables."""
    print("\n[Step: Schema Creation] Initializing database tables...")
    try:
        create_all_tables(engine=engine)
        print("SUCCESS: Tables 'tourism_statewise_annual', 'weather_daily_forecast', and 'asi_monument_visitors' ready.")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False


def run_load_data(
    tourism_path: Optional[str] = None,
    weather_path: Optional[str] = None,
    monument_path: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> bool:
    """Loads curated Parquet datasets into database."""
    print("\n[Step: Data Ingestion] Loading curated datasets with idempotent upsert...")
    try:
        t_count = load_curated_tourism_to_db(parquet_path=tourism_path, engine=engine)
        print(f"SUCCESS: Ingested {t_count} records into 'tourism_statewise_annual'.")

        w_count = load_curated_weather_to_db(parquet_path=weather_path, engine=engine)
        print(f"SUCCESS: Ingested {w_count} records into 'weather_daily_forecast'.")

        m_count = load_curated_monuments_to_db(parquet_path=monument_path, engine=engine)
        print(f"SUCCESS: Ingested {m_count} records into 'asi_monument_visitors'.")
        return True
    except Exception as e:
        logger.error(f"Failed during data loading: {e}")
        return False


def run_verify(engine: Optional[Engine] = None) -> bool:
    """Queries and displays verification metrics from the database."""
    print("\n[Step: Verification] Querying database record counts and integrity...")
    try:
        metrics = verify_database_counts(engine=engine)
        print("\n--- DATABASE VERIFICATION SUMMARY ---")
        print(f"Tourism Total Records      : {metrics['tourism_total_count']} (Expected: 370)")
        print(f"  - State/UT Records       : {metrics['tourism_state_count']} (Expected: 360)")
        print(f"  - Total India Aggregate  : {metrics['tourism_aggregate_count']} (Expected: 10)")
        print(f"  - Distinct States/UTs    : {metrics['tourism_distinct_states']} (Expected: 36)")
        print(f"  - Preserved Nulls        : {metrics['tourism_null_visit_count']} (Expected: 2, Ladakh 2018)")
        print(f"  - Historical Years       : {metrics['tourism_years']}")
        print(f"Weather Total Records      : {metrics['weather_total_count']} (Expected: 21)")
        print(f"  - Distinct Destinations  : {metrics['weather_distinct_destinations']} (Expected: 3)")
        print(f"  - Destinations           : {', '.join(metrics['weather_destinations'])}")
        print(f"  - Distinct Forecast Dates: {metrics['weather_distinct_dates']} (Expected: 7)")
        print(f"  - All Marked as Forecast : {metrics['weather_all_forecast']}")
        print(f"Monument Total Records     : {metrics.get('monument_total_count', 0)} (Expected: 290)")
        print(f"  - Distinct Monuments     : {metrics.get('monument_distinct_count', 0)} (Expected: 145)")
        print(f"  - Distinct ASI Circles   : {metrics.get('monument_distinct_circles', 0)} (Expected: 33)")
        print(f"  - Distinct States/Regions: {metrics.get('monument_distinct_states', 0)}")
        print(f"  - Financial Years        : {metrics.get('monument_financial_years', [])}")
        print(f"  - Total Footfall Tracked : {metrics.get('monument_total_footfall', 0):,}")
        print("--------------------------------------\n")
        return True
    except Exception as e:
        logger.error(f"Failed during verification: {e}")
        print("\nTip: If tables do not exist yet or have not been loaded, run:")
        print("     python -m src.database.init_db --all")
        return False


def main():
    parser = argparse.ArgumentParser(description="TravelWise PostgreSQL Database Management CLI")
    parser.add_argument("--check-connection", action="store_true", help="Check database connectivity")
    parser.add_argument("--create-tables", action="store_true", help="Create database tables")
    parser.add_argument("--load-data", action="store_true", help="Load curated datasets with upsert")
    parser.add_argument("--verify", action="store_true", help="Verify database counts and constraints")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: check, create, load, verify")
    parser.add_argument("--sqlite", action="store_true", help="Target local SQLite store at data/travelwise.db")
    parser.add_argument("--tourism-path", type=str, default=None, help="Custom path to tourism Parquet")
    parser.add_argument("--weather-path", type=str, default=None, help="Custom path to weather Parquet")
    parser.add_argument("--monument-path", type=str, default=None, help="Custom path to monument Parquet")

    args = parser.parse_args()

    # Determine target engine
    target_engine = None
    if args.sqlite:
        from pathlib import Path
        from sqlalchemy import create_engine
        sqlite_file = Path(__file__).resolve().parent.parent.parent / "data" / "travelwise.db"
        target_engine = create_engine(f"sqlite:///{sqlite_file.as_posix()}", echo=False)
        print(f"Using local SQLite engine: {target_engine.url}")

    # Default to --all if no action specified
    if not any([args.check_connection, args.create_tables, args.load_data, args.verify, args.all]):
        args.all = True

    if (args.check_connection or args.all) and not args.sqlite:
        if not run_check_connection():
            if args.all:
                print("Aborting database initialization because PostgreSQL connection could not be established.")
                sys.exit(1)

    if args.create_tables or args.all:
        if not run_create_tables(engine=target_engine):
            sys.exit(1)

    if args.load_data or args.all:
        if not run_load_data(args.tourism_path, args.weather_path, args.monument_path, engine=target_engine):
            sys.exit(1)

    if args.verify or args.all:
        if not run_verify(engine=target_engine):
            sys.exit(1)

    print("\nTravelWise Database operations completed successfully.")


if __name__ == "__main__":
    main()
