"""
Unit tests for TravelWise Phase 5: Dashboard Data Loading and Analytics Logic.
Validates Parquet dataset loading, pure transformation functions, KPI calculations,
and filter isolation without requiring a running Streamlit server.
"""

import pytest
import pandas as pd
from pathlib import Path

from app.data_loader import (
    load_tourism_data,
    load_weather_data,
    load_tourism_quality_report,
    load_weather_quality_report,
    compute_platform_kpis,
    filter_tourism_data,
    get_tourism_timeline_trends,
    get_top_states_by_visits,
    get_destination_weather,
)


@pytest.fixture(scope="module")
def tourism_df():
    """Loads curated tourism dataset fixture."""
    return load_tourism_data()


@pytest.fixture(scope="module")
def weather_df():
    """Loads curated weather dataset fixture."""
    return load_weather_data()


class TestDashboardDataLoading:
    """Tests loading of curated Parquet datasets and quality reports."""

    def test_load_tourism_dataset(self, tourism_df):
        assert isinstance(tourism_df, pd.DataFrame)
        assert len(tourism_df) == 370
        expected_cols = {
            "state", "category", "year", "visit_count",
            "is_aggregate", "entity_type", "is_estimated",
            "prev_year_visit_count", "yoy_growth_pct",
        }
        assert expected_cols.issubset(set(tourism_df.columns))

    def test_load_weather_dataset(self, weather_df):
        assert isinstance(weather_df, pd.DataFrame)
        assert len(weather_df) == 21
        expected_cols = {
            "destination", "forecast_date", "temp_min_c", "temp_max_c",
            "temp_avg_c", "total_precipitation_mm", "max_precipitation_probability_pct",
            "hourly_records_count", "metric_type", "is_forecast",
        }
        assert expected_cols.issubset(set(weather_df.columns))

    def test_load_quality_reports(self):
        t_report = load_tourism_quality_report()
        assert t_report is not None
        assert t_report.get("total_records") == 370
        assert t_report.get("duplicate_records") == 0
        assert t_report.get("negative_records") == 0

        w_report = load_weather_quality_report()
        assert w_report is not None
        assert w_report.get("total_daily_forecast_records") == 21
        assert w_report.get("hourly_records_parsed") == 504
        assert w_report.get("is_forecast_metric") is True


class TestAnalyticsAndKPITransformations:
    """Tests platform KPI computations and pure analytics transformation helpers."""

    def test_compute_platform_kpis(self, tourism_df, weather_df):
        kpis = compute_platform_kpis(tourism_df, weather_df)

        assert kpis["total_historical_visits"] > 0
        assert kpis["total_domestic_visits"] > 0
        assert kpis["total_foreign_visits"] > 0
        assert kpis["total_historical_visits"] == (kpis["total_domestic_visits"] + kpis["total_foreign_visits"])
        assert kpis["historical_period"] == "2018 – 2022"
        assert kpis["historical_years"] == [2018, 2019, 2020, 2021, 2022]
        assert kpis["distinct_states_count"] == 36
        assert kpis["weather_destinations_count"] == 3
        assert set(kpis["weather_destinations"]) == {"Lonavala", "Mahabaleshwar", "Matheran"}
        assert kpis["forecast_dates_count"] == 7

    def test_filter_tourism_data_aggregate_exclusion(self, tourism_df):
        # Default behavior: exclude Total India aggregate
        filtered = filter_tourism_data(tourism_df, include_aggregates=False)
        assert len(filtered) == 360
        assert "Total India" not in filtered["state"].values

        # Explicitly request aggregates
        with_agg = filter_tourism_data(tourism_df, include_aggregates=True)
        assert len(with_agg) == 370
        assert "Total India" in with_agg["state"].values

    def test_filter_tourism_data_multi_dimensional(self, tourism_df):
        # Filter by years, category, and single state
        filtered = filter_tourism_data(
            tourism_df,
            years=[2021, 2022],
            states=["Goa"],
            categories=["Domestic"],
            include_aggregates=False,
        )
        assert len(filtered) == 2
        assert all(filtered["state"] == "Goa")
        assert all(filtered["category"] == "Domestic")
        assert set(filtered["year"]) == {2021, 2022}

    def test_get_tourism_timeline_trends(self, tourism_df):
        trends = get_tourism_timeline_trends(tourism_df, include_aggregates=False)
        assert isinstance(trends, pd.DataFrame)
        # 5 years * 2 categories = 10 rows
        assert len(trends) == 10
        assert set(trends["year"]) == {2018, 2019, 2020, 2021, 2022}
        assert set(trends["category"]) == {"Domestic", "Foreign"}

    def test_get_top_states_by_visits(self, tourism_df):
        top_5 = get_top_states_by_visits(tourism_df, top_n=5)
        assert len(top_5) == 5
        # Crucial check: Total India must NEVER appear in top states rankings
        assert "Total India" not in top_5["state"].values
        # Sorted descending
        counts = top_5["visit_count"].tolist()
        assert counts == sorted(counts, reverse=True)

    def test_get_destination_weather(self, weather_df):
        lonavala = get_destination_weather(weather_df, "Lonavala")
        assert len(lonavala) == 7
        assert all(lonavala["destination"] == "Lonavala")
        assert list(lonavala["forecast_date"]) == sorted(list(lonavala["forecast_date"]))

        mahabaleshwar = get_destination_weather(weather_df, "Mahabaleshwar")
        assert len(mahabaleshwar) == 7

        matheran = get_destination_weather(weather_df, "Matheran")
        assert len(matheran) == 7

        # Case-insensitive destination match
        lower_match = get_destination_weather(weather_df, "lonavala")
        assert len(lower_match) == 7
