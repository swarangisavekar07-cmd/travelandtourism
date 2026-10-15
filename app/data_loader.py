"""
Data loading and transformation utility module for TravelWise Streamlit Platform.
Reads curated Parquet datasets directly and provides cached data access and pure
filtering/analytics helpers for the dashboard views.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Project root safe resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TOURIISM_PARQUET = PROJECT_ROOT / "data" / "processed" / "tourism" / "india_tourism_statewise_normalized.parquet"
DEFAULT_WEATHER_PARQUET = PROJECT_ROOT / "data" / "processed" / "weather" / "daily_weather_forecast_curated.parquet"
DEFAULT_TOURIISM_QUALITY = PROJECT_ROOT / "data" / "processed" / "tourism" / "quality_report.json"
DEFAULT_WEATHER_QUALITY = PROJECT_ROOT / "data" / "processed" / "weather" / "quality_report.json"


def get_project_root() -> Path:
    """Returns the absolute project root path."""
    return PROJECT_ROOT


@st.cache_data(show_spinner=False)
def load_tourism_data(path: Optional[str] = None) -> pd.DataFrame:
    """
    Loads curated statewise tourism dataset from Parquet.
    Returns a pandas DataFrame.
    """
    target = Path(path) if path else DEFAULT_TOURIISM_PARQUET
    if not target.exists():
        raise FileNotFoundError(f"Tourism dataset not found at {target}")
    df = pd.read_parquet(target)
    return df


@st.cache_data(show_spinner=False)
def load_weather_data(path: Optional[str] = None) -> pd.DataFrame:
    """
    Loads curated daily weather forecasts from Parquet.
    Returns a pandas DataFrame.
    """
    target = Path(path) if path else DEFAULT_WEATHER_PARQUET
    if not target.exists():
        raise FileNotFoundError(f"Weather forecast dataset not found at {target}")
    df = pd.read_parquet(target)
    return df


@st.cache_data(show_spinner=False)
def load_tourism_quality_report(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Loads tourism quality report JSON if available."""
    target = Path(path) if path else DEFAULT_TOURIISM_QUALITY
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read tourism quality report: {e}")
        return None


@st.cache_data(show_spinner=False)
def load_weather_quality_report(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Loads weather quality report JSON if available."""
    target = Path(path) if path else DEFAULT_WEATHER_QUALITY
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read weather quality report: {e}")
        return None


# -----------------------------------------------------------------------------
# Pure Analytics & Transformation Helpers (Independent of Streamlit context)
# -----------------------------------------------------------------------------

def compute_platform_kpis(tourism_df: pd.DataFrame, weather_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes key platform summary metrics for the Overview page.
    Distinguishes historical aggregate totals from state breakdowns and forecast metadata.
    """
    # Filter for Total India aggregate rows to get authentic national totals
    aggregate_df = tourism_df[tourism_df["is_aggregate"] == True]
    state_df = tourism_df[tourism_df["is_aggregate"] == False]

    # Total visits recorded at national level
    if not aggregate_df.empty:
        total_domestic_visits = aggregate_df[aggregate_df["category"] == "Domestic"]["visit_count"].sum()
        total_foreign_visits = aggregate_df[aggregate_df["category"] == "Foreign"]["visit_count"].sum()
    else:
        # Fallback to summing state totals
        total_domestic_visits = state_df[state_df["category"] == "Domestic"]["visit_count"].sum()
        total_foreign_visits = state_df[state_df["category"] == "Foreign"]["visit_count"].sum()

    total_visits = total_domestic_visits + total_foreign_visits

    historical_years = sorted(tourism_df["year"].dropna().unique().tolist())
    historical_period = f"{historical_years[0]} – {historical_years[-1]}" if historical_years else "N/A"
    distinct_states_count = state_df["state"].nunique()

    # Weather Forecast Metrics
    weather_destinations = sorted(weather_df["destination"].dropna().unique().tolist())
    forecast_dates = sorted(weather_df["forecast_date"].dropna().unique().tolist())
    forecast_start = forecast_dates[0] if forecast_dates else "N/A"
    forecast_end = forecast_dates[-1] if forecast_dates else "N/A"
    latest_retrieved = weather_df["latest_retrieved_at_utc"].dropna().iloc[0] if not weather_df.empty and "latest_retrieved_at_utc" in weather_df.columns else "N/A"

    return {
        "total_historical_visits": int(total_visits) if pd.notna(total_visits) else 0,
        "total_domestic_visits": int(total_domestic_visits) if pd.notna(total_domestic_visits) else 0,
        "total_foreign_visits": int(total_foreign_visits) if pd.notna(total_foreign_visits) else 0,
        "historical_period": historical_period,
        "historical_years": historical_years,
        "distinct_states_count": distinct_states_count,
        "weather_destinations": weather_destinations,
        "weather_destinations_count": len(weather_destinations),
        "forecast_dates_count": len(forecast_dates),
        "forecast_start": forecast_start,
        "forecast_end": forecast_end,
        "latest_weather_retrieved_at": latest_retrieved,
    }


def filter_tourism_data(
    df: pd.DataFrame,
    years: Optional[List[int]] = None,
    states: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    include_aggregates: bool = False,
) -> pd.DataFrame:
    """
    Applies multi-dimensional filtering to the curated tourism DataFrame.
    By default excludes Total India aggregate rows to prevent double-counting.
    """
    filtered = df.copy()

    # Exclude or isolate aggregate rows
    if not include_aggregates:
        filtered = filtered[filtered["is_aggregate"] == False]
    else:
        # If user explicitly requested aggregates only or both
        pass

    if years:
        filtered = filtered[filtered["year"].isin(years)]

    if states:
        filtered = filtered[filtered["state"].isin(states)]

    if categories:
        filtered = filtered[filtered["category"].isin(categories)]

    return filtered


def get_tourism_timeline_trends(df: pd.DataFrame, include_aggregates: bool = False) -> pd.DataFrame:
    """
    Aggregates tourism visit counts by Year and Category.
    """
    data = df[df["is_aggregate"] == include_aggregates].copy()
    grouped = data.groupby(["year", "category"], as_index=False)["visit_count"].sum()
    return grouped.sort_values(by=["year", "category"])


def get_top_states_by_visits(
    df: pd.DataFrame,
    year: Optional[int] = None,
    category: Optional[str] = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Returns top states ranked by total visit counts for specified filters.
    Strictly excludes aggregate rows to prevent distortion.
    """
    state_data = df[df["is_aggregate"] == False].copy()

    if year is not None:
        state_data = state_data[state_data["year"] == year]

    if category is not None and category != "All":
        state_data = state_data[state_data["category"] == category]

    grouped = state_data.groupby("state", as_index=False)["visit_count"].sum()
    grouped = grouped.sort_values(by="visit_count", ascending=False).head(top_n)
    return grouped


def get_destination_weather(weather_df: pd.DataFrame, destination: str) -> pd.DataFrame:
    """
    Filters weather forecasts for a specific travel destination, sorted by date.
    """
    dest_df = weather_df[weather_df["destination"].str.lower() == destination.lower()].copy()
    if not dest_df.empty:
        dest_df = dest_df.sort_values(by="forecast_date")
    return dest_df
