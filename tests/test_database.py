"""
Unit and integration tests for TravelWise Phase 4: Database Integration.
Tests execute against an isolated in-memory SQLite engine to guarantee that
production PostgreSQL credentials are never required to run and pass the test suite.
"""

import pytest
from sqlalchemy import create_engine, inspect, select, func
from sqlalchemy.orm import Session

from src.database.config import DatabaseSettings, get_db_settings
from src.database.models import Base, TourismStatewiseAnnual, WeatherDailyForecast
from src.database.connection import (
    get_engine,
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


@pytest.fixture
def sqlite_engine():
    """Provides an isolated in-memory SQLite engine for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    yield engine
    engine.dispose()


class TestDatabaseConfig:
    """Tests configuration parsing and credential security."""

    def test_default_settings(self):
        settings = DatabaseSettings()
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.name == "travelwise_db"
        assert settings.user == "postgres"

    def test_sqlalchemy_url_generation(self):
        settings = DatabaseSettings(
            host="db.example.com",
            port=5433,
            name="test_db",
            user="app_user",
            password="secret_password!@#",
        )
        url = settings.sqlalchemy_url
        assert "postgresql+psycopg2://app_user:" in url
        assert "@db.example.com:5433/test_db" in url
        # Verify URL encoding of special chars in password
        assert "secret_password%21%40%23" in url

    def test_database_url_override(self):
        settings = DatabaseSettings(database_url_override="postgres://user:pass@host:5432/db")
        assert settings.sqlalchemy_url == "postgresql+psycopg2://user:pass@host:5432/db"

    def test_is_configured_logic(self):
        # Empty password
        unconfigured = DatabaseSettings(password="")
        assert not unconfigured.is_configured()

        # Placeholder password
        placeholder = DatabaseSettings(password="change_me_in_dotenv")
        assert not placeholder.is_configured()

        # Configured password
        configured = DatabaseSettings(password="valid_strong_pass_123")
        assert configured.is_configured()

        # Custom DATABASE_URL always counts as configured
        override = DatabaseSettings(database_url_override="sqlite:///:memory:")
        assert override.is_configured()


class TestDatabaseSchema:
    """Tests table schema creation, constraints, and relationships."""

    def test_create_and_drop_tables(self, sqlite_engine):
        # Verify tables do not exist initially
        inspector = inspect(sqlite_engine)
        assert "tourism_statewise_annual" not in inspector.get_table_names()
        assert "weather_daily_forecast" not in inspector.get_table_names()

        # Create tables
        create_all_tables(sqlite_engine)
        inspector = inspect(sqlite_engine)
        tables = inspector.get_table_names()
        assert "tourism_statewise_annual" in tables
        assert "weather_daily_forecast" in tables

        # Verify columns in tourism_statewise_annual
        tourism_cols = {c["name"] for c in inspector.get_columns("tourism_statewise_annual")}
        expected_t_cols = {
            "id", "state", "category", "year", "visit_count",
            "is_aggregate", "entity_type", "is_estimated",
            "prev_year_visit_count", "yoy_growth_pct",
            "created_at", "updated_at",
        }
        assert expected_t_cols.issubset(tourism_cols)

        # Verify columns in weather_daily_forecast
        weather_cols = {c["name"] for c in inspector.get_columns("weather_daily_forecast")}
        expected_w_cols = {
            "id", "destination", "forecast_date", "latitude", "longitude",
            "temp_min_c", "temp_max_c", "temp_avg_c", "total_precipitation_mm",
            "max_precipitation_probability_pct", "avg_precipitation_probability_pct",
            "avg_wind_speed_kmh", "max_wind_speed_kmh", "hourly_records_count",
            "metric_type", "is_forecast", "latest_retrieved_at_utc",
            "source_api", "created_at", "updated_at",
        }
        assert expected_w_cols.issubset(weather_cols)

        # Drop tables
        drop_all_tables(sqlite_engine)
        inspector = inspect(sqlite_engine)
        assert "tourism_statewise_annual" not in inspector.get_table_names()
        assert "weather_daily_forecast" not in inspector.get_table_names()


class TestDatabaseLoaderAndIntegrity:
    """Tests dataset ingestion, upsert idempotency, and constraint preservation."""

    def test_load_curated_tourism_to_db(self, sqlite_engine):
        create_all_tables(sqlite_engine)

        count = load_curated_tourism_to_db(engine=sqlite_engine)
        assert count == 370

        with Session(sqlite_engine) as session:
            # Check total row count
            total = session.query(func.count(TourismStatewiseAnnual.id)).scalar()
            assert total == 370

            # Check Total India aggregate separation
            aggregates = session.query(TourismStatewiseAnnual).filter(
                TourismStatewiseAnnual.is_aggregate == True
            ).all()
            assert len(aggregates) == 10
            assert all(a.state == "Total India" for a in aggregates)
            assert all(a.entity_type == "AGGREGATE_TOTAL" for a in aggregates)

            # Check individual state count
            states = session.query(TourismStatewiseAnnual).filter(
                TourismStatewiseAnnual.is_aggregate == False
            ).all()
            assert len(states) == 360
            assert all(s.entity_type == "STATE_OR_UT" for s in states)

            # Check preservation of genuine historical nulls (Ladakh 2018)
            ladakh_2018 = session.query(TourismStatewiseAnnual).filter(
                TourismStatewiseAnnual.state == "Ladakh",
                TourismStatewiseAnnual.year == 2018,
            ).all()
            assert len(ladakh_2018) == 2
            for record in ladakh_2018:
                assert record.visit_count is None
                assert record.yoy_growth_pct is None

            # Check estimated data flags (Delhi and Maharashtra 2022)
            delhi_2022 = session.query(TourismStatewiseAnnual).filter(
                TourismStatewiseAnnual.state == "Delhi",
                TourismStatewiseAnnual.year == 2022,
            ).all()
            assert all(d.is_estimated is True for d in delhi_2022)

    def test_tourism_idempotent_upsert(self, sqlite_engine):
        """Verify that running load_curated_tourism_to_db repeatedly does not duplicate records."""
        create_all_tables(sqlite_engine)

        count_first = load_curated_tourism_to_db(engine=sqlite_engine)
        assert count_first == 370

        # Run again
        count_second = load_curated_tourism_to_db(engine=sqlite_engine)
        assert count_second == 370

        with Session(sqlite_engine) as session:
            total = session.query(func.count(TourismStatewiseAnnual.id)).scalar()
            assert total == 370, "Repeated loading must not create duplicate tourism records"

    def test_load_curated_weather_to_db(self, sqlite_engine):
        create_all_tables(sqlite_engine)

        count = load_curated_weather_to_db(engine=sqlite_engine)
        assert count == 21

        with Session(sqlite_engine) as session:
            total = session.query(func.count(WeatherDailyForecast.id)).scalar()
            assert total == 21

            # Check destinations
            destinations = [
                d[0] for d in session.query(WeatherDailyForecast.destination).distinct().order_by(
                    WeatherDailyForecast.destination
                ).all()
            ]
            assert destinations == ["Lonavala", "Mahabaleshwar", "Matheran"]

            # Check all marked as forecast
            forecast_count = session.query(func.count(WeatherDailyForecast.id)).filter(
                WeatherDailyForecast.is_forecast == True
            ).scalar()
            assert forecast_count == 21

            # Check numerical sanity
            sample = session.query(WeatherDailyForecast).filter(
                WeatherDailyForecast.destination == "Lonavala"
            ).first()
            assert sample is not None
            assert sample.temp_min_c <= sample.temp_max_c
            assert sample.hourly_records_count == 24
            assert sample.latest_retrieved_at_utc is not None
            assert sample.source_api is not None

    def test_weather_idempotent_upsert(self, sqlite_engine):
        """Verify that running load_curated_weather_to_db repeatedly does not duplicate records."""
        create_all_tables(sqlite_engine)

        count_first = load_curated_weather_to_db(engine=sqlite_engine)
        assert count_first == 21

        # Run again
        count_second = load_curated_weather_to_db(engine=sqlite_engine)
        assert count_second == 21

        with Session(sqlite_engine) as session:
            total = session.query(func.count(WeatherDailyForecast.id)).scalar()
            assert total == 21, "Repeated loading must not create duplicate weather records"

    def test_verify_database_counts(self, sqlite_engine):
        create_all_tables(sqlite_engine)
        load_curated_tourism_to_db(engine=sqlite_engine)
        load_curated_weather_to_db(engine=sqlite_engine)

        metrics = verify_database_counts(sqlite_engine)
        assert metrics["tourism_total_count"] == 370
        assert metrics["tourism_state_count"] == 360
        assert metrics["tourism_aggregate_count"] == 10
        assert metrics["tourism_distinct_states"] == 36
        assert metrics["tourism_null_visit_count"] == 2
        assert metrics["tourism_years"] == [2018, 2019, 2020, 2021, 2022]
        assert metrics["weather_total_count"] == 21
        assert metrics["weather_distinct_destinations"] == 3
        assert metrics["weather_destinations"] == ["Lonavala", "Mahabaleshwar", "Matheran"]
        assert metrics["weather_distinct_dates"] == 7
        assert metrics["weather_all_forecast"] is True


class TestDatabaseConnectionAndSession:
    """Tests session context management and connection checks."""

    def test_session_commit_and_rollback(self, sqlite_engine):
        create_all_tables(sqlite_engine)

        # Successful transaction
        with get_db_session(sqlite_engine) as session:
            record = TourismStatewiseAnnual(
                state="MockState",
                category="Domestic",
                year=2022,
                visit_count=5000,
                is_aggregate=False,
                entity_type="STATE_OR_UT",
                is_estimated=False,
            )
            session.add(record)

        with Session(sqlite_engine) as session:
            count = session.query(func.count(TourismStatewiseAnnual.id)).filter(
                TourismStatewiseAnnual.state == "MockState"
            ).scalar()
            assert count == 1

        # Rollback on exception
        with pytest.raises(RuntimeError):
            with get_db_session(sqlite_engine) as session:
                record = TourismStatewiseAnnual(
                    state="RollbackState",
                    category="Domestic",
                    year=2022,
                    visit_count=5000,
                    is_aggregate=False,
                    entity_type="STATE_OR_UT",
                    is_estimated=False,
                )
                session.add(record)
                raise RuntimeError("Simulated transaction failure")

        with Session(sqlite_engine) as session:
            count = session.query(func.count(TourismStatewiseAnnual.id)).filter(
                TourismStatewiseAnnual.state == "RollbackState"
            ).scalar()
            assert count == 0

    def test_check_database_connection_sqlite(self, sqlite_engine):
        ok, msg = check_database_connection(sqlite_engine)
        assert ok is True
        assert "SQLite" in msg
