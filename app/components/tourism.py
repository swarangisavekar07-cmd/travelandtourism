"""
Tourism Analytics component for TravelWise Platform.
Provides multi-dimensional analysis of state/UT tourism data with Plotly charts,
YoY growth analysis, Domestic vs Foreign breakdown, and transparent null/estimate auditing.
Strictly isolates 'Total India' aggregate records from state-level calculations.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Optional

from app.data_loader import filter_tourism_data, get_top_states_by_visits


def format_count_short(num: float) -> str:
    """Formats large figures concisely for metrics and chart tooltips."""
    if pd.isna(num) or num is None:
        return "N/A"
    if num >= 1e7:
        return f"{num / 1e7:.2f} Cr"
    elif num >= 1e5:
        return f"{num / 1e5:.2f} Lakh"
    elif num >= 1e3:
        return f"{num / 1e3:.1f}K"
    return f"{int(num):,}"


def render_tourism_analytics(df: pd.DataFrame):
    """Renders the comprehensive Tourism Analytics page."""
    # Page Header
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                <h2 style="color: #f8fafc; margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em;">
                    State & UT Tourism Analytics
                </h2>
                <span style="color: #38bdf8; font-size: 0.84rem; font-weight: 500; background-color: #111c33; padding: 4px 10px; border-radius: 4px; border: 1px solid #1e3a5f;">
                    Historical Series: 2018 – 2022
                </span>
            </div>
            <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 0.9rem;">
                Comparative evaluation of Domestic Tourist Visits (DTV) and Foreign Tourist Visits (FTV) across Indian States & Union Territories.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filter Strip
    with st.expander("Filter Controls", expanded=True):
        f_col1, f_col2, f_col3 = st.columns([1.2, 1, 1.2])

        available_years = sorted(df["year"].dropna().unique().tolist())
        all_states = sorted(df[df["is_aggregate"] == False]["state"].unique().tolist())
        categories = ["All", "Domestic", "Foreign"]

        with f_col1:
            selected_years = st.multiselect(
                "Years",
                options=available_years,
                default=available_years,
                help="Select one or more historical years.",
            )

        with f_col2:
            selected_category = st.selectbox(
                "Visitor Category",
                options=categories,
                index=0,
                help="Filter by Domestic or Foreign tourist category.",
            )

        with f_col3:
            include_aggregate = st.checkbox(
                "Include 'Total India' Aggregate",
                value=False,
                help="Keep unchecked to compare individual states without national double-counting.",
            )

        selected_states = st.multiselect(
            "Filter Specific States/UTs (Leave empty for all 36 States & UTs)",
            options=all_states,
            default=[],
            help="Select one or more specific states to isolate.",
        )

    if include_aggregate:
        st.markdown(
            """
            <div style="background-color: #271d0b; border: 1px solid #78350f; border-left: 4px solid #f59e0b; padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; font-size: 0.85rem; color: #fef3c7;">
                <strong>Notice:</strong> National aggregate ('Total India') records are included in the view. Do not sum across states to prevent double counting.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Filter execution
    cat_filter = [selected_category] if selected_category != "All" else ["Domestic", "Foreign"]
    state_filter = selected_states if selected_states else None
    filtered_df = filter_tourism_data(
        df=df,
        years=selected_years if selected_years else available_years,
        states=state_filter,
        categories=cat_filter,
        include_aggregates=include_aggregate,
    )

    if filtered_df.empty:
        st.error("No records found matching the active filter criteria. Please broaden your selection.")
        return

    # Filtered KPI Strip
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    total_filtered_visits = filtered_df["visit_count"].sum()
    dom_visits = filtered_df[filtered_df["category"] == "Domestic"]["visit_count"].sum()
    for_visits = filtered_df[filtered_df["category"] == "Foreign"]["visit_count"].sum()
    active_states = filtered_df["state"].nunique()

    with kpi_col1:
        st.metric(
            label="Filtered Total Footfall",
            value=format_count_short(total_filtered_visits),
            help="Sum of recorded tourist visits within the current filter selection.",
        )
    with kpi_col2:
        st.metric(
            label="Domestic Visits (DTV)",
            value=format_count_short(dom_visits),
            help="Domestic tourist visits matching selected filters.",
        )
    with kpi_col3:
        st.metric(
            label="Foreign Visits (FTV)",
            value=format_count_short(for_visits),
            help="Foreign tourist visits matching selected filters.",
        )
    with kpi_col4:
        st.metric(
            label="States Represented",
            value=f"{active_states} Entities",
            help="Number of distinct states/UTs included in filtered view.",
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Visual Analytics Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Time-Series Trends",
        "State Rankings",
        "YoY Growth Dynamics",
        "Data Audit & Source Table",
    ])

    with tab1:
        st.markdown(
            """
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 12px; font-weight: 500;">
                Annual Trajectory & Tourist Category Breakdown (2018–2022)
            </div>
            """,
            unsafe_allow_html=True,
        )

        trend_data = filtered_df.groupby(["year", "category"], as_index=False)["visit_count"].sum()

        col_trend, col_pie = st.columns([1.6, 1])

        with col_trend:
            fig_trend = px.line(
                trend_data,
                x="year",
                y="visit_count",
                color="category",
                markers=True,
                labels={"visit_count": "Recorded Visits", "year": "Historical Year", "category": "Category"},
                color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
                height=350,
            )
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                xaxis=dict(showgrid=False, dtick=1, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                hovermode="x unified",
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with col_pie:
            category_totals = trend_data.groupby("category", as_index=False)["visit_count"].sum()
            fig_pie = px.pie(
                category_totals,
                values="visit_count",
                names="category",
                hole=0.55,
                color="category",
                color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
                height=350,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, title=""),
            )
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                insidetextfont=dict(color="#ffffff", size=12),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: #cbd5e1; font-size: 0.92rem; font-weight: 500;">
                    Top States & UTs by Cumulative Footfall (Excludes National Aggregate)
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        top_n = st.slider("Number of States to Display", min_value=5, max_value=25, value=10, step=5)

        # Strictly exclude aggregate records
        clean_state_df = filtered_df[filtered_df["is_aggregate"] == False]
        top_states = clean_state_df.groupby("state", as_index=False)["visit_count"].sum().sort_values(
            by="visit_count", ascending=True
        ).tail(top_n)

        fig_states = px.bar(
            top_states,
            x="visit_count",
            y="state",
            orientation="h",
            labels={"visit_count": "Recorded Visits", "state": "State / UT"},
            color="visit_count",
            color_continuous_scale=[[0, "#0b2545"], [0.5, "#0284c7"], [1, "#2dd4bf"]],
            height=420,
        )
        fig_states.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color="#cbd5e1", family="Inter, sans-serif"),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
            yaxis=dict(showgrid=False, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
        )
        st.plotly_chart(fig_states, use_container_width=True)

    with tab3:
        st.markdown(
            """
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                Year-on-Year (YoY) Growth Percentage Trajectory
            </div>
            <p style="color: #94a3b8; font-size: 0.84rem; margin-bottom: 14px;">
                Visualizes the severe contraction in 2020 (-74% national domestic decline) during COVID lockdowns,
                followed by strong domestic post-lockdown rebound in 2021 (+11%) and 2022 (+155%).
            </p>
            """,
            unsafe_allow_html=True,
        )

        growth_df = filtered_df.dropna(subset=["yoy_growth_pct"]).copy()

        if not growth_df.empty:
            avg_growth_by_year = growth_df.groupby(["year", "category"], as_index=False)["yoy_growth_pct"].median()

            fig_growth = px.bar(
                avg_growth_by_year,
                x="year",
                y="yoy_growth_pct",
                color="category",
                barmode="group",
                labels={"yoy_growth_pct": "Median YoY Growth (%)", "year": "Year", "category": "Category"},
                color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
                height=350,
            )
            fig_growth.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                xaxis=dict(showgrid=False, dtick=1, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", zeroline=True, zerolinecolor="#94a3b8"),
            )
            st.plotly_chart(fig_growth, use_container_width=True)
        else:
            st.info("YoY growth calculations are not available for the selected subset.")

    with tab4:
        st.markdown(
            """
            <div style="background-color: #111c33; padding: 14px 18px; border-radius: 6px; border: 1px solid #1e3a5f; margin-bottom: 14px;">
                <div style="color: #38bdf8; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px;">
                    Official Footnotes & Data Integrity Audit
                </div>
                <ul style="color: #cbd5e1; font-size: 0.82rem; margin: 0; padding-left: 20px; line-height: 1.6;">
                    <li><strong>Ladakh (2018):</strong> Preserved as genuine historical null (<code>NULL</code>). Ladakh was designated a separate UT in October 2019 following bifurcation from Jammu & Kashmir.</li>
                    <li><strong>Delhi & Maharashtra (2022):</strong> Domestic figures flagged with <code>is_estimated = True</code> per Ministry of Tourism official compendium notes.</li>
                    <li><strong>Total India:</strong> Flagged with <code>is_aggregate = True</code> and <code>entity_type = 'AGGREGATE_TOTAL'</code> to isolate national sums from state-level calculations.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        display_cols = [
            "state", "category", "year", "visit_count",
            "is_aggregate", "is_estimated", "prev_year_visit_count", "yoy_growth_pct"
        ]
        rename_map = {
            "state": "State / UT",
            "category": "Category",
            "year": "Year",
            "visit_count": "Visit Count",
            "is_aggregate": "Aggregate Flag",
            "is_estimated": "Estimated Flag",
            "prev_year_visit_count": "Prev Year Visits",
            "yoy_growth_pct": "YoY Growth (%)",
        }

        st.dataframe(
            filtered_df[display_cols].rename(columns=rename_map).sort_values(by=["Year", "State / UT", "Category"]),
            use_container_width=True,
            hide_index=True,
        )
