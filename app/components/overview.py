"""
Overview page component for TravelWise Platform.
Displays high-level executive KPIs, platform architecture, and temporal coverage.
Clearly distinguishes historical retrospective data from forward-looking weather forecasts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any

from app.data_loader import compute_platform_kpis


def format_large_number(num: float) -> str:
    """Formats large visit counts cleanly in Crores / Lakhs / Millions."""
    if pd.isna(num) or num is None:
        return "N/A"
    if num >= 1e7:
        return f"{num / 1e7:.2f} Cr"
    elif num >= 1e5:
        return f"{num / 1e5:.2f} Lakh"
    elif num >= 1e3:
        return f"{num / 1e3:.1f}K"
    return f"{int(num):,}"


def render_overview(tourism_df: pd.DataFrame, weather_df: pd.DataFrame):
    """Renders the executive Overview page."""
    kpis = compute_platform_kpis(tourism_df, weather_df)

    # Executive Header
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #111c33 0%, #0b1329 100%); padding: 22px 24px; border-radius: 8px; border: 1px solid #1e3a5f; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 style="color: #f8fafc; margin: 0; font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;">
                        TravelWise Analytics Platform
                    </h1>
                    <p style="color: #94a3b8; margin: 6px 0 0 0; font-size: 0.95rem; line-height: 1.5;">
                        Multi-Dimensional Tourism Data Engineering & Forward-Looking Destination Weather Intelligence
                    </p>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <span style="background-color: #1e3a5f; color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; border: 1px solid #0284c7;">
                        Curated Parquet Lake
                    </span>
                    <span style="background-color: #132e35; color: #2dd4bf; padding: 4px 10px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; border: 1px solid #0d9488;">
                        PySpark 3.5.1
                    </span>
                    <span style="background-color: #1e293b; color: #e2e8f0; padding: 4px 10px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; border: 1px solid #334155;">
                        PostgreSQL 18 Ready
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Clear distinction notice
    st.markdown(
        """
        <div style="background-color: #0d1b33; border: 1px solid #1e3a5f; border-left: 4px solid #0284c7; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 0.88rem; color: #cbd5e1; line-height: 1.5;">
            <strong style="color: #38bdf8;">Data Engineering Architecture Notice:</strong> This platform integrates two distinct analytical domains:
            <strong>Historical Tourism Series (2018–2022)</strong> sourced from the Ministry of Tourism, Government of India, and
            <strong>Forward-Looking 7-Day Weather Forecasts</strong> aggregated from 24 hourly readings per day via Open-Meteo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Aligned 4-Column KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Historical Visits",
            value=format_large_number(kpis["total_historical_visits"]),
            delta="2018–2022 Macro Volume",
            delta_color="off",
            help="National aggregate volume across 5 recorded years (Domestic + Foreign visits).",
        )

    with col2:
        domestic_share = (
            (kpis["total_domestic_visits"] / kpis["total_historical_visits"] * 100)
            if kpis["total_historical_visits"] > 0
            else 0
        )
        st.metric(
            label="Domestic Visits (DTV)",
            value=format_large_number(kpis["total_domestic_visits"]),
            delta=f"{domestic_share:.1f}% National Share",
            delta_color="normal",
            help="Cumulative Domestic Tourist Visits recorded across all states and years.",
        )

    with col3:
        foreign_share = (
            (kpis["total_foreign_visits"] / kpis["total_historical_visits"] * 100)
            if kpis["total_historical_visits"] > 0
            else 0
        )
        st.metric(
            label="Foreign Visits (FTV)",
            value=format_large_number(kpis["total_foreign_visits"]),
            delta=f"{foreign_share:.1f}% National Share",
            delta_color="normal",
            help="Cumulative Foreign Tourist Visits recorded across all states and years.",
        )

    with col4:
        st.metric(
            label="Weather Pilot Destinations",
            value=f"{kpis['weather_destinations_count']} Cities",
            delta="7-Day Operational Horizon",
            delta_color="off",
            help="Active destinations tracked: Lonavala, Mahabaleshwar, Matheran.",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Compact Side-by-Side Coverage Cards
    cov_col1, cov_col2 = st.columns(2)

    with cov_col1:
        st.markdown(
            f"""
            <div style="background-color: #111c33; padding: 18px 20px; border-radius: 8px; border: 1px solid #1e3a5f; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin: 0; color: #f8fafc; font-size: 1.05rem; font-weight: 600;">
                        Historical Tourism Domain
                    </h3>
                    <span style="background-color: rgba(2, 132, 199, 0.2); color: #38bdf8; padding: 2px 8px; border-radius: 4px; font-size: 0.74rem; font-weight: 600;">
                        Ministry of Tourism
                    </span>
                </div>
                <table style="width: 100%; font-size: 0.84rem; color: #cbd5e1; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #172540;">
                        <td style="padding: 6px 0; color: #94a3b8;">Temporal Period:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">{kpis['historical_period']} (5 annual series)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #172540;">
                        <td style="padding: 6px 0; color: #94a3b8;">Geographic Scope:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">{kpis['distinct_states_count']} States & UTs + National Total</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #172540;">
                        <td style="padding: 6px 0; color: #94a3b8;">Normalization:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">Wide-to-Long PySpark ETL (370 records)</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #94a3b8;">Integrity Rules:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">Preserved nulls (Ladakh 2018), estimates noted</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cov_col2:
        st.markdown(
            f"""
            <div style="background-color: #111c33; padding: 18px 20px; border-radius: 8px; border: 1px solid #1e3a5f; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin: 0; color: #f8fafc; font-size: 1.05rem; font-weight: 600;">
                        Operational Weather Domain
                    </h3>
                    <span style="background-color: rgba(20, 184, 166, 0.2); color: #2dd4bf; padding: 2px 8px; border-radius: 4px; font-size: 0.74rem; font-weight: 600;">
                        Open-Meteo API
                    </span>
                </div>
                <table style="width: 100%; font-size: 0.84rem; color: #cbd5e1; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #172540;">
                        <td style="padding: 6px 0; color: #94a3b8;">Pilot Coverage:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">{', '.join(kpis['weather_destinations'])}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #172540;">
                        <td style="padding: 6px 0; color: #94a3b8;">Forecast Horizon:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">{kpis['forecast_start']} to {kpis['forecast_end']} ({kpis['forecast_dates_count']} days)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #172540;">
                        <td style="padding: 6px 0; color: #94a3b8;">Aggregation Level:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">24 hourly readings -> Daily KPI records</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #94a3b8;">Classification:</td>
                        <td style="text-align: right; font-weight: 500; color: #f1f5f9;">Forward-looking predictions (no climatology)</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # National Macro Trend Visualization
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
            <h3 style="margin: 0; color: #f8fafc; font-size: 1.15rem; font-weight: 600;">
                National Tourism Trajectory (2018–2022)
            </h3>
            <span style="color: #94a3b8; font-size: 0.8rem;">
                Total India Benchmark • Domestic vs Foreign Visit Volumes
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    aggregate_df = tourism_df[tourism_df["is_aggregate"] == True].copy()
    if not aggregate_df.empty:
        # Sort values cleanly
        aggregate_df = aggregate_df.sort_values(by=["year", "category"])

        fig = px.bar(
            aggregate_df,
            x="year",
            y="visit_count",
            color="category",
            barmode="group",
            labels={"visit_count": "Recorded Visits", "year": "Year", "category": "Tourist Category"},
            color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
            height=340,
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10),
            font=dict(color="#cbd5e1", family="Inter, sans-serif", size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title="",
                font=dict(size=12, color="#e2e8f0"),
            ),
            xaxis=dict(
                showgrid=False,
                dtick=1,
                linecolor="#1e3a5f",
                tickfont=dict(size=12, color="#cbd5e1"),
                title="",
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#172540",
                linecolor="#1e3a5f",
                tickfont=dict(size=11, color="#cbd5e1"),
                title="Total Visits",
            ),
            hoverlabel=dict(
                bgcolor="#0f172a",
                bordercolor="#0284c7",
                font_size=12,
                font_color="#f8fafc",
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("National aggregate data is currently unavailable.")
