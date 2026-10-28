"""
Data loading and transformation utility module for TravelWise Streamlit Platform.
Provides direct SQL database access (PostgreSQL with seamless SQLite fallback)
and cached Parquet data access, alongside pure analytical and state-level helpers.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import streamlit as st

logger = logging.getLogger(__name__)

# Project root safe resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TOURIISM_PARQUET = PROJECT_ROOT / "data" / "processed" / "tourism" / "india_tourism_statewise_normalized.parquet"
DEFAULT_WEATHER_PARQUET = PROJECT_ROOT / "data" / "processed" / "weather" / "daily_weather_forecast_curated.parquet"
DEFAULT_MONUMENT_PARQUET = PROJECT_ROOT / "data" / "processed" / "monuments" / "asi_monument_visitors_normalized.parquet"
DEFAULT_TOURIISM_QUALITY = PROJECT_ROOT / "data" / "processed" / "tourism" / "quality_report.json"
DEFAULT_WEATHER_QUALITY = PROJECT_ROOT / "data" / "processed" / "weather" / "quality_report.json"
DEFAULT_MONUMENT_QUALITY = PROJECT_ROOT / "data" / "processed" / "monuments" / "quality_report.json"
DEFAULT_SQLITE_DB = PROJECT_ROOT / "data" / "travelwise.db"


def get_project_root() -> Path:
    """Returns the absolute project root path."""
    return PROJECT_ROOT


def format_large_number(num: Optional[float]) -> str:
    """Formats large visit counts cleanly in Crores / Lakhs / Millions."""
    if num is None or pd.isna(num):
        return "N/A"
    if num >= 1e7:
        return f"{num / 1e7:.2f} Cr"
    elif num >= 1e5:
        return f"{num / 1e5:.2f} Lakh"
    elif num >= 1e3:
        return f"{num / 1e3:.1f}K"
    return f"{int(num):,}"


# -----------------------------------------------------------------------------
# Database Connection & SQL Loading
# -----------------------------------------------------------------------------

def get_database_engine():
    """
    Returns an active SQLAlchemy engine for database queries.
    Attempts PostgreSQL connection; if unavailable, seamlessly connects
    to the local SQLite store at data/travelwise.db.
    """
    try:
        from src.database.connection import get_engine, check_database_connection
        ok, _ = check_database_connection()
        if ok:
            return get_engine(), "PostgreSQL"
    except Exception as e:
        logger.info(f"PostgreSQL connection check failed/unconfigured: {e}")

    # Fallback to local SQLite database
    from sqlalchemy import create_engine
    sqlite_path = DEFAULT_SQLITE_DB
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
    engine = create_engine(sqlite_url, echo=False)

    # Ensure tables exist and data is populated
    try:
        from src.database.loader import (
            create_all_tables,
            load_curated_tourism_to_db,
            load_curated_monuments_to_db,
        )
        create_all_tables(engine)
        with engine.connect() as conn:
            from sqlalchemy import text
            count = conn.execute(text("SELECT COUNT(1) FROM tourism_statewise_annual")).scalar()
            if not count or count == 0:
                load_curated_tourism_to_db(engine=engine)
            m_count = conn.execute(text("SELECT COUNT(1) FROM asi_monument_visitors")).scalar()
            if not m_count or m_count == 0:
                load_curated_monuments_to_db(engine=engine)
    except Exception as e:
        logger.warning(f"Error ensuring SQLite database state: {e}")

    return engine, "SQLite"


@st.cache_data(show_spinner=False)
def load_tourism_from_sql() -> Tuple[pd.DataFrame, str]:
    """
    Loads normalized tourism data directly from the SQL database via SQLAlchemy.
    Preserves exact types, historical nulls, and schema constraints.
    Returns (DataFrame, engine_name).
    """
    try:
        engine, engine_name = get_database_engine()
        query = (
            "SELECT state, category, year, visit_count, is_aggregate, "
            "entity_type, is_estimated, prev_year_visit_count, yoy_growth_pct "
            "FROM tourism_statewise_annual ORDER BY state, category, year"
        )
        df = pd.read_sql(query, engine)
        if not df.empty:
            df["is_aggregate"] = df["is_aggregate"].astype(bool)
            df["is_estimated"] = df["is_estimated"].astype(bool)
            return df, engine_name
    except Exception as e:
        logger.warning(f"Failed to load from SQL database ({e}), falling back to Parquet.")

    # Resilient fallback to curated Parquet
    df = load_tourism_data()
    return df, "Curated Parquet"


@st.cache_data(show_spinner=False)
def load_monuments_from_sql() -> Tuple[pd.DataFrame, str]:
    """
    Loads normalized monument visitor statistics directly from the SQL database via SQLAlchemy.
    Preserves exact types, legitimate nulls, and schema constraints.
    Returns (DataFrame, engine_name).
    """
    try:
        engine, engine_name = get_database_engine()
        query = (
            "SELECT serial_number, monument_name, circle, state_or_region, "
            "financial_year, domestic_visitors, foreign_visitors, total_visitors, "
            "prev_year_domestic_visitors, prev_year_foreign_visitors, prev_year_total_visitors, "
            "yoy_growth_pct, foreign_visitor_share_pct, source "
            "FROM asi_monument_visitors ORDER BY circle, monument_name, financial_year"
        )
        df = pd.read_sql(query, engine)
        if not df.empty:
            return df, engine_name
    except Exception as e:
        logger.warning(f"Failed to load monuments from SQL database ({e}), falling back to Parquet.")

    # Resilient fallback to curated Parquet
    try:
        df = load_monuments_data()
        return df, "Curated Parquet"
    except Exception as e:
        logger.warning(f"Parquet fallback also unavailable ({e})")
        return pd.DataFrame(), "None"


# -----------------------------------------------------------------------------
# Parquet File Loaders
# -----------------------------------------------------------------------------

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
def load_monuments_data(path: Optional[str] = None) -> pd.DataFrame:
    """
    Loads curated ASI monument visitor dataset from Parquet.
    Returns a pandas DataFrame.
    """
    target = Path(path) if path else DEFAULT_MONUMENT_PARQUET
    if not target.exists():
        raise FileNotFoundError(f"Monument dataset not found at {target}")
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
def load_monument_quality_report(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Loads monument quality report JSON if available."""
    target = Path(path) if path else DEFAULT_MONUMENT_QUALITY
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read monument quality report: {e}")
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

def compute_platform_kpis(
    tourism_df: pd.DataFrame,
    weather_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Computes key platform summary metrics for the Overview page.
    Distinguishes historical aggregate totals from state breakdowns.
    Weather support is fully optional for backward compatibility.
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

    # Weather Forecast Metrics (Optional)
    if weather_df is not None and not weather_df.empty:
        weather_destinations = sorted(weather_df["destination"].dropna().unique().tolist())
        forecast_dates = sorted(weather_df["forecast_date"].dropna().unique().tolist())
        forecast_start = forecast_dates[0] if forecast_dates else "N/A"
        forecast_end = forecast_dates[-1] if forecast_dates else "N/A"
        latest_retrieved = (
            weather_df["latest_retrieved_at_utc"].dropna().iloc[0]
            if "latest_retrieved_at_utc" in weather_df.columns and not weather_df["latest_retrieved_at_utc"].dropna().empty
            else "N/A"
        )
    else:
        weather_destinations = []
        forecast_dates = []
        forecast_start = "N/A"
        forecast_end = "N/A"
        latest_retrieved = "N/A"

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
    Preserved for backward test compatibility.
    """
    dest_df = weather_df[weather_df["destination"].str.lower() == destination.lower()].copy()
    if not dest_df.empty:
        dest_df = dest_df.sort_values(by="forecast_date")
    return dest_df


# -----------------------------------------------------------------------------
# State Explorer Dedicated Analytical Helpers
# -----------------------------------------------------------------------------

def get_all_distinct_states(df: pd.DataFrame) -> List[str]:
    """
    Returns sorted list of distinct States and Union Territories actually present in the dataset.
    Strictly excludes 'Total India' aggregate so only verified administrative entities appear.
    """
    state_df = df[df["is_aggregate"] == False]
    return sorted(state_df["state"].dropna().unique().tolist())


def compute_state_analytics(
    df: pd.DataFrame,
    state_name: str,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Computes rigorous state-level analytics based strictly on calculated values:
    - Domestic visits, Foreign visits, and Total visits
    - Yearly trajectories and YoY growth rates
    - National rank among 36 states/UTs
    - Domestic vs Foreign percentage share
    - Peak year and contraction/recovery dynamics
    - Transparent handling of missing values (e.g. Ladakh 2018)
    - Automatically generated data-driven summary
    """
    state_records = df[df["state"] == state_name].copy()
    all_clean_states = df[df["is_aggregate"] == False].copy()

    if state_records.empty:
        raise ValueError(f"State '{state_name}' not found in verified dataset.")

    # Distinct historical years
    historical_years = sorted(state_records["year"].dropna().unique().tolist())

    # Build yearly summary table for this state
    yearly_rows = []
    for y in historical_years:
        y_slice = state_records[state_records["year"] == y]
        dom_val = y_slice[y_slice["category"] == "Domestic"]["visit_count"].values
        for_val = y_slice[y_slice["category"] == "Foreign"]["visit_count"].values

        dom = dom_val[0] if len(dom_val) > 0 and pd.notna(dom_val[0]) else None
        forg = for_val[0] if len(for_val) > 0 and pd.notna(for_val[0]) else None

        # Genuine null check: if either is missing, total is incomplete (e.g. Ladakh 2018)
        if dom is None or forg is None:
            total = None
            is_complete = False
        else:
            total = dom + forg
            is_complete = True

        # Growth rates from dataframe
        dom_growth = y_slice[y_slice["category"] == "Domestic"]["yoy_growth_pct"].values
        for_growth = y_slice[y_slice["category"] == "Foreign"]["yoy_growth_pct"].values

        yearly_rows.append({
            "year": y,
            "domestic": dom,
            "foreign": forg,
            "total": total,
            "is_complete": is_complete,
            "domestic_yoy": dom_growth[0] if len(dom_growth) > 0 and pd.notna(dom_growth[0]) else None,
            "foreign_yoy": for_growth[0] if len(for_growth) > 0 and pd.notna(for_growth[0]) else None,
        })

    yearly_df = pd.DataFrame(yearly_rows)

    # Compute Total YoY growth safely
    yearly_df["total_prev"] = yearly_df["total"].shift(1)
    yearly_df["total_yoy"] = yearly_df.apply(
        lambda r: round(((r["total"] - r["total_prev"]) / r["total_prev"]) * 100.0, 2)
        if pd.notna(r["total"]) and pd.notna(r["total_prev"]) and r["total_prev"] > 0
        else None,
        axis=1
    )

    # Active selection (specific year or all-years aggregate)
    if year is not None:
        sel_row = yearly_df[yearly_df["year"] == year]
        if not sel_row.empty:
            r = sel_row.iloc[0]
            active_dom = int(r["domestic"]) if pd.notna(r["domestic"]) else None
            active_for = int(r["foreign"]) if pd.notna(r["foreign"]) else None
            active_total = int(r["total"]) if pd.notna(r["total"]) else None
            active_dom_yoy = float(r["domestic_yoy"]) if pd.notna(r["domestic_yoy"]) else None
            active_for_yoy = float(r["foreign_yoy"]) if pd.notna(r["foreign_yoy"]) else None
            active_total_yoy = float(r["total_yoy"]) if pd.notna(r["total_yoy"]) else None
            active_is_complete = bool(r["is_complete"]) if pd.notna(r["is_complete"]) else False
        else:
            active_dom = active_for = active_total = None
            active_dom_yoy = active_for_yoy = active_total_yoy = None
            active_is_complete = False

        # National rank for selected year
        year_states = all_clean_states[all_clean_states["year"] == year]
        dom_rank_series = year_states[year_states["category"] == "Domestic"].groupby("state")["visit_count"].sum().rank(ascending=False, method="min")
        for_rank_series = year_states[year_states["category"] == "Foreign"].groupby("state")["visit_count"].sum().rank(ascending=False, method="min")
        tot_rank_series = year_states.groupby("state")["visit_count"].sum().rank(ascending=False, method="min")

        dom_rank = int(dom_rank_series.get(state_name, 0)) if state_name in dom_rank_series else None
        for_rank = int(for_rank_series.get(state_name, 0)) if state_name in for_rank_series else None
        tot_rank = int(tot_rank_series.get(state_name, 0)) if state_name in tot_rank_series else None
    else:
        # Cumulative across all available years
        dom_sum = yearly_df["domestic"].dropna().sum()
        for_sum = yearly_df["foreign"].dropna().sum()
        active_dom = int(dom_sum) if not pd.isna(dom_sum) else None
        active_for = int(for_sum) if not pd.isna(for_sum) else None
        active_total = (active_dom + active_for) if (active_dom is not None and active_for is not None) else None
        active_dom_yoy = None
        active_for_yoy = None
        active_total_yoy = None
        active_is_complete = True

        # Cumulative national ranks
        cum_dom = all_clean_states[all_clean_states["category"] == "Domestic"].groupby("state")["visit_count"].sum().rank(ascending=False, method="min")
        cum_for = all_clean_states[all_clean_states["category"] == "Foreign"].groupby("state")["visit_count"].sum().rank(ascending=False, method="min")
        cum_tot = all_clean_states.groupby("state")["visit_count"].sum().rank(ascending=False, method="min")

        dom_rank = int(cum_dom.get(state_name, 0)) if state_name in cum_dom else None
        for_rank = int(cum_for.get(state_name, 0)) if state_name in cum_for else None
        tot_rank = int(cum_tot.get(state_name, 0)) if state_name in cum_tot else None

    # Share calculations
    if active_total and active_total > 0 and active_dom is not None and active_for is not None:
        dom_share = round((active_dom / active_total) * 100.0, 1)
        for_share = round((active_for / active_total) * 100.0, 1)
    else:
        dom_share = for_share = None

    # Peak and lowest years based on complete years
    valid_complete = yearly_df.dropna(subset=["total"])
    if not valid_complete.empty:
        peak_row = valid_complete.loc[valid_complete["total"].idxmax()]
        low_row = valid_complete.loc[valid_complete["total"].idxmin()]
        peak_year = int(peak_row["year"])
        peak_visits = int(peak_row["total"])
        low_year = int(low_row["year"])
        low_visits = int(low_row["total"])
    else:
        peak_year = peak_visits = low_year = low_visits = None

    # Generate strictly data-driven analytical summary narrative
    total_states_count = all_clean_states["state"].nunique()
    summary_sentences = []

    if dom_rank:
        summary_sentences.append(
            f"{state_name} ranks #{tot_rank} overall among all {total_states_count} Indian States and Union Territories "
            f"in total tourist footfall (#{dom_rank} in Domestic visits, #{for_rank} in Foreign visits)."
        )

    if dom_share is not None and for_share is not None:
        if dom_share >= 98.0:
            summary_sentences.append(
                f"Tourism is overwhelmingly domestic-driven, with Domestic Tourist Visits (DTV) accounting for {dom_share}% of total visitors."
            )
        elif for_share >= 5.0:
            summary_sentences.append(
                f"The destination maintains a high international appeal, with Foreign Tourist Visits (FTV) contributing a notable {for_share}% of all tourist arrivals."
            )
        else:
            summary_sentences.append(
                f"Domestic travelers comprise {dom_share}% of volume, while foreign visitors represent {for_share}%."
            )

    if peak_year and low_year:
        summary_sentences.append(
            f"Historically, {state_name} reached its peak volume in {peak_year} with {peak_visits:,.0f} total visits, "
            f"while its lowest recorded point occurred in {low_year} ({low_visits:,.0f} visits), reflecting lockdown impacts."
        )

    # State-specific official footnotes
    if state_name == "Ladakh":
        summary_sentences.append(
            "Official Notice: 2018 visit statistics are officially unrecorded (NULL) by the Ministry of Tourism because "
            "Ladakh was designated as a distinct Union Territory on 31 October 2019 following bifurcation from Jammu & Kashmir."
        )
    elif state_name in ("Maharashtra", "Delhi"):
        summary_sentences.append(
            f"Official Notice: 2022 figures for {state_name} incorporate official Ministry of Tourism estimates "
            "computed by applying national growth trajectories to the 2019 baseline."
        )

    analytical_summary = " ".join(summary_sentences)

    return {
        "state_name": state_name,
        "selected_year": year,
        "domestic_visits": active_dom,
        "foreign_visits": active_for,
        "total_visits": active_total,
        "is_complete": active_is_complete,
        "domestic_share": dom_share,
        "foreign_share": for_share,
        "domestic_yoy": active_dom_yoy,
        "foreign_yoy": active_for_yoy,
        "total_yoy": active_total_yoy,
        "domestic_rank": dom_rank,
        "foreign_rank": for_rank,
        "total_rank": tot_rank,
        "total_states_count": total_states_count,
        "peak_year": peak_year,
        "peak_visits": peak_visits,
        "lowest_year": low_year,
        "lowest_visits": low_visits,
        "yearly_trajectory": yearly_df,
        "analytical_summary": analytical_summary,
        "is_estimated_state": state_name in ("Maharashtra", "Delhi"),
        "has_null_history": state_name == "Ladakh",
    }


# -----------------------------------------------------------------------------
# Monument Analytical Helpers
# -----------------------------------------------------------------------------

def get_monument_kpis(df: pd.DataFrame, financial_year: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates executive KPIs for ASI Centrally Protected Ticketed Monuments.
    """
    if df is None or df.empty:
        return {
            "total_visitors": 0,
            "domestic_visitors": 0,
            "foreign_visitors": 0,
            "foreign_share_pct": 0.0,
            "monuments_count": 0,
            "circles_count": 0,
            "states_count": 0,
            "top_monument_name": "N/A",
            "top_monument_footfall": 0,
        }

    filtered = df.copy()
    if financial_year and financial_year != "All Years":
        filtered = filtered[filtered["financial_year"] == financial_year]

    tot_vis = float(filtered["total_visitors"].fillna(0).sum())
    dom_vis = float(filtered["domestic_visitors"].fillna(0).sum())
    for_vis = float(filtered["foreign_visitors"].fillna(0).sum())
    for_share = round((for_vis / tot_vis * 100.0), 2) if tot_vis > 0 else 0.0

    monuments_count = int(filtered["monument_name"].nunique())
    circles_count = int(filtered["circle"].nunique())
    states_count = int(filtered["state_or_region"].nunique())

    # Find highest footfall monument
    top_monument_name = "N/A"
    top_monument_footfall = 0
    if not filtered.empty:
        agg = filtered.groupby("monument_name")["total_visitors"].sum().reset_index()
        top_row = agg.sort_values(by="total_visitors", ascending=False).iloc[0]
        top_monument_name = top_row["monument_name"]
        top_monument_footfall = int(top_row["total_visitors"])

    return {
        "total_visitors": tot_vis,
        "domestic_visitors": dom_vis,
        "foreign_visitors": for_vis,
        "foreign_share_pct": for_share,
        "monuments_count": monuments_count,
        "circles_count": circles_count,
        "states_count": states_count,
        "top_monument_name": top_monument_name,
        "top_monument_footfall": top_monument_footfall,
    }


def get_top_monuments(
    df: pd.DataFrame,
    financial_year: str = "2023-24",
    top_n: int = 10,
    category: str = "total_visitors",
    circle: Optional[str] = None,
    state: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns ranked monuments filtered by financial year, circle, state, and category.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    filtered = df.copy()
    if financial_year and financial_year != "All Years":
        filtered = filtered[filtered["financial_year"] == financial_year]

    if circle and circle != "All Circles":
        filtered = filtered[filtered["circle"] == circle]

    if state and state != "All States/UTs":
        filtered = filtered[filtered["state_or_region"] == state]

    if category not in filtered.columns:
        category = "total_visitors"

    ranked = filtered.sort_values(by=category, ascending=False).head(top_n).copy()
    ranked["rank"] = range(1, len(ranked) + 1)
    return ranked


def get_circle_footfall_summary(
    df: pd.DataFrame,
    financial_year: str = "2023-24",
) -> pd.DataFrame:
    """
    Aggregates monument visitor footfalls across ASI circles.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    filtered = df.copy()
    if financial_year and financial_year != "All Years":
        filtered = filtered[filtered["financial_year"] == financial_year]

    summary = (
        filtered.groupby(["circle", "state_or_region"])
        .agg(
            monument_count=("monument_name", "nunique"),
            domestic_visitors=("domestic_visitors", "sum"),
            foreign_visitors=("foreign_visitors", "sum"),
            total_visitors=("total_visitors", "sum"),
        )
        .reset_index()
        .sort_values(by="total_visitors", ascending=False)
    )
    summary["foreign_share_pct"] = np.where(
        summary["total_visitors"] > 0,
        np.round((summary["foreign_visitors"] / summary["total_visitors"]) * 100.0, 2),
        0.0,
    )
    return summary


def get_monument_comparison(df: pd.DataFrame, monument_name: str) -> Dict[str, Any]:
    """
    Returns deep-dive multi-year footfall trajectory for a specific monument.
    """
    if df is None or df.empty:
        return {}

    sub = df[df["monument_name"] == monument_name].sort_values(by="financial_year")
    if sub.empty:
        return {}

    return {
        "monument_name": monument_name,
        "circle": sub["circle"].iloc[0],
        "state_or_region": sub["state_or_region"].iloc[0],
        "records": sub.to_dict(orient="records"),
    }
