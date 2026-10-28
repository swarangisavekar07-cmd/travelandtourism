import pytest
from sqlalchemy import create_engine, inspect, select, func
from sqlalchemy.orm import Session

from src.database.models import Base, ASIMonumentVisitor
from src.database.loader import (
    create_all_tables,
    load_curated_monuments_to_db,
    verify_database_counts,
)

@pytest.fixture
def sqlite_engine():
    """Provides an isolated in-memory SQLite engine for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    create_all_tables(engine)
    yield engine
    engine.dispose()

def test_monument_table_schema(sqlite_engine):
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()
    assert "asi_monument_visitors" in tables

    columns = {col["name"]: col for col in inspector.get_columns("asi_monument_visitors")}
    assert "id" in columns
    assert "monument_name" in columns
    assert "circle" in columns
    assert "state_or_region" in columns
    assert "financial_year" in columns
    assert "domestic_visitors" in columns
    assert "foreign_visitors" in columns
    assert "total_visitors" in columns
    assert "yoy_growth_pct" in columns
    assert "foreign_visitor_share_pct" in columns

def test_monument_unique_constraint(sqlite_engine):
    with Session(sqlite_engine) as session:
        m1 = ASIMonumentVisitor(
            monument_name="Test Monument",
            circle="Agra",
            state_or_region="Uttar Pradesh",
            financial_year="2023-24",
            domestic_visitors=1000,
            foreign_visitors=100,
            total_visitors=1100,
        )
        session.add(m1)
        session.commit()

        # Duplicate natural key insert attempt
        m2 = ASIMonumentVisitor(
            monument_name="Test Monument",
            circle="Agra",
            state_or_region="Uttar Pradesh",
            financial_year="2023-24",
            domestic_visitors=2000,
            foreign_visitors=200,
            total_visitors=2200,
        )
        session.add(m2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()

def test_idempotent_monument_loading(sqlite_engine):
    """
    Verifies that calling load_curated_monuments_to_db multiple times
    is strictly idempotent and results in exactly 290 records without duplicates.
    """
    first_run_count = load_curated_monuments_to_db(engine=sqlite_engine)
    assert first_run_count == 290

    # Repeat load to verify idempotency
    second_run_count = load_curated_monuments_to_db(engine=sqlite_engine)
    assert second_run_count == 290

    # Total row count in table must remain 290
    with sqlite_engine.connect() as conn:
        count = conn.execute(select(func.count(ASIMonumentVisitor.id))).scalar()
        assert count == 290

def test_verify_database_counts_includes_monuments(sqlite_engine):
    load_curated_monuments_to_db(engine=sqlite_engine)
    metrics = verify_database_counts(engine=sqlite_engine)

    assert metrics["monument_total_count"] == 290
    assert metrics["monument_distinct_count"] == 145
    assert metrics["monument_distinct_circles"] == 33
    assert metrics["monument_distinct_states"] == 21
    assert metrics["monument_financial_years"] == ["2022-23", "2023-24"]
    assert metrics["monument_total_footfall"] == 104751032
