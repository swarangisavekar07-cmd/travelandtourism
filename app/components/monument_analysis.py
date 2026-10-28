"""
TravelWise — Monument Visitor Analysis Component.
Provides multi-dimensional analytics for Centrally Protected Ticketed Monuments in India
sourced from Archaeological Survey of India (ASI) and Ministry of Tourism publications.
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.data_loader import (
    format_large_number,
    get_monument_kpis,
    get_top_monuments,
    get_circle_footfall_summary,
    get_monument_comparison,
    load_monument_quality_report,
)

# Dark mode visual tokens consistent with TravelWise design system
DARK_BG = "#0d1629"
CARD_BG = "#131f37"
BORDER_COLOR = "#1e3a5f"
PRIMARY_COLOR = "#38bdf8"
ACCENT_COLOR = "#2dd4bf"
FOREIGN_COLOR = "#f59e0b"
DOMESTIC_COLOR = "#0284c7"
MUTED_TEXT = "#94a3b8"


def render_monument_analysis(monument_df: Optional[pd.DataFrame], db_source: str = "SQL Database") -> None:
    """
    Renders the Monument Visitor Analysis dashboard section.
    Gracefully handles empty data and database error states with informative guidance.
    """
    # -------------------------------------------------------------------------
    # Section Header
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">🏛️</span>
                <h1 style="color: #f8fafc; font-size: 1.85rem; font-weight: 700; margin: 0; letter-spacing: -0.02em;">
                    Centrally Protected Ticketed ASI Monuments — National Visitor Analytics
                </h1>
            </div>
            <p style="color: #94a3b8; font-size: 0.92rem; margin-top: 6px; line-height: 1.5;">
                Longitudinal evaluation of domestic and international footfall across <strong>145 Centrally Protected Ticketed Monuments</strong>
                governed by the <strong>Archaeological Survey of India (ASI)</strong>. Verified against the
                <em>Ministry of Tourism, Government of India (India Tourism Data Compendium 2024, Table 4.2.3)</em>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # Empty / Unloaded State Handling
    # -------------------------------------------------------------------------
    if monument_df is None or monument_df.empty:
        st.warning(
            "⚠️ **Monument Visitor Statistics Not Loaded**\n\n"
            "The `asi_monument_visitors` table is currently empty or has not been populated in your active database.\n\n"
            "**To populate this dataset:**\n"
            "1. Run the PySpark Monument ETL Pipeline: `python -m src.pipeline.run_pipelines --pipeline monuments`\n"
            "2. Ingest into the active SQL store: `python -m src.database.init_db --sqlite --load-data`"
        )
        return

    # -------------------------------------------------------------------------
    # Sidebar Filters
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("<hr style='border: 0; height: 1px; background: #172540; margin: 12px 0 16px 0;'>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="color: #38bdf8; font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                Monument Filters
            </div>
            """,
            unsafe_allow_html=True,
        )

        all_years = sorted(monument_df["financial_year"].dropna().unique().tolist())
        selected_fy = st.selectbox(
            "Financial Year",
            options=["All Years"] + all_years,
            index=1 if "2023-24" in all_years else 0,
            help="Filter by Indian fiscal reporting period (1 April to 31 March)",
        )

        all_states = ["All States/UTs"] + sorted(monument_df["state_or_region"].dropna().unique().tolist())
        selected_state = st.selectbox(
            "State / Union Territory",
            options=all_states,
            index=0,
            help="Filter monuments situated in a specific State or Union Territory",
        )

        all_circles = ["All Circles"] + sorted(monument_df["circle"].dropna().unique().tolist())
        selected_circle = st.selectbox(
            "ASI Circle Jurisdiction",
            options=all_circles,
            index=0,
            help="Filter by Archaeological Survey of India administrative circle",
        )

        top_n = st.slider("Top Monuments to Display", min_value=5, max_value=30, value=10, step=5)

    # Filter base dataset for global KPIs
    filtered_base = monument_df.copy()
    if selected_fy != "All Years":
        filtered_base = filtered_base[filtered_base["financial_year"] == selected_fy]
    if selected_state != "All States/UTs":
        filtered_base = filtered_base[filtered_base["state_or_region"] == selected_state]
    if selected_circle != "All Circles":
        filtered_base = filtered_base[filtered_base["circle"] == selected_circle]

    kpis = get_monument_kpis(filtered_base, financial_year=None)

    # -------------------------------------------------------------------------
    # Executive KPI Cards
    # -------------------------------------------------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Footfall",
            value=format_large_number(kpis["total_visitors"]),
            delta=f"{selected_fy}" if selected_fy != "All Years" else "Cumulative (2 FYs)",
            help="Sum of domestic and foreign ticketed footfall",
        )

    with col2:
        st.metric(
            label="Domestic Visits",
            value=format_large_number(kpis["domestic_visitors"]),
            delta=f"{100 - kpis['foreign_share_pct']:.1f}% share",
            help="Total Indian national visitors",
        )

    with col3:
        st.metric(
            label="Foreign Visits",
            value=format_large_number(kpis["foreign_visitors"]),
            delta=f"{kpis['foreign_share_pct']:.2f}% share",
            help="Total foreign national visitors",
        )

    with col4:
        st.metric(
            label="Centrally Protected Sites",
            value=f"{kpis['monuments_count']} Sites",
            delta=f"{kpis['circles_count']} ASI Circles",
            help="Ticketed monuments covered under current filter",
        )

    with col5:
        st.metric(
            label="Most Visited Monument",
            value=kpis["top_monument_name"][:18] + "..." if len(kpis["top_monument_name"]) > 18 else kpis["top_monument_name"],
            delta=format_large_number(kpis["top_monument_footfall"]),
            help="Top visited monument within active filter",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # Tabbed Visualizations
    # -------------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Top Monument Rankings",
        "📈 Financial Year YoY Trends",
        "🌐 ASI Circles & States",
        "🔍 Single-Monument Inspector",
    ])

    # --- TAB 1: Top Monument Rankings ---
    with tab1:
        st.markdown(
            f"""
            <div style="margin-bottom: 12px;">
                <h3 style="color: #f1f5f9; font-size: 1.15rem; font-weight: 600; margin: 0;">
                    Top {top_n} Centrally Protected Monuments by Footfall ({selected_fy})
                </h3>
                <p style="color: #94a3b8; font-size: 0.84rem; margin-top: 2px;">
                    Ranked by verified ticketed visitor volumes. Compare domestic footfall against international visitor pull.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ranked_df = get_top_monuments(
            df=monument_df,
            financial_year="2023-24" if selected_fy == "All Years" else selected_fy,
            top_n=top_n,
            category="total_visitors",
            circle=selected_circle if selected_circle != "All Circles" else None,
            state=selected_state if selected_state != "All States/UTs" else None,
        )

        if not ranked_df.empty:
            # Dual stacked horizontal bar: Domestic vs Foreign
            fig_top = go.Figure()
            fig_top.add_trace(
                go.Bar(
                    y=ranked_df["monument_name"],
                    x=ranked_df["domestic_visitors"],
                    name="Domestic Visitors",
                    orientation="h",
                    marker=dict(color=DOMESTIC_COLOR, line=dict(color="#38bdf8", width=1)),
                    hovertemplate="<b>%{y}</b><br>Domestic: %{x:,.0f}<extra></extra>",
                )
            )
            fig_top.add_trace(
                go.Bar(
                    y=ranked_df["monument_name"],
                    x=ranked_df["foreign_visitors"],
                    name="Foreign Visitors",
                    orientation="h",
                    marker=dict(color=FOREIGN_COLOR, line=dict(color="#fde047", width=1)),
                    hovertemplate="<b>%{y}</b><br>Foreign: %{x:,.0f}<extra></extra>",
                )
            )

            fig_top.update_layout(
                barmode="stack",
                paper_bgcolor=DARK_BG,
                plot_bgcolor=CARD_BG,
                font=dict(family="Inter, sans-serif", color="#e2e8f0", size=12),
                xaxis=dict(
                    title="Visitor Footfall",
                    gridcolor=BORDER_COLOR,
                    zerolinecolor=BORDER_COLOR,
                    tickformat=",.0f",
                ),
                yaxis=dict(
                    title="",
                    autorange="reversed",
                    gridcolor="rgba(0,0,0,0)",
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color="#cbd5e1"),
                ),
                margin=dict(l=20, r=20, t=30, b=30),
                height=max(400, top_n * 32),
            )
            st.plotly_chart(fig_top, use_container_width=True)

            # Tabular breakdown
            display_cols = [
                "rank",
                "monument_name",
                "circle",
                "state_or_region",
                "domestic_visitors",
                "foreign_visitors",
                "total_visitors",
                "foreign_visitor_share_pct",
                "yoy_growth_pct",
            ]
            renamed_cols = {
                "rank": "Rank",
                "monument_name": "Monument Name",
                "circle": "ASI Circle",
                "state_or_region": "State / UT",
                "domestic_visitors": "Domestic",
                "foreign_visitors": "Foreign",
                "total_visitors": "Total Visitors",
                "foreign_visitor_share_pct": "Foreign Share (%)",
                "yoy_growth_pct": "YoY Growth (%)",
            }
            styled_df = ranked_df[display_cols].rename(columns=renamed_cols)
            st.dataframe(
                styled_df.style.format({
                    "Domestic": "{:,.0f}",
                    "Foreign": "{:,.0f}",
                    "Total Visitors": "{:,.0f}",
                    "Foreign Share (%)": "{:.2f}%",
                    "YoY Growth (%)": lambda v: f"{v:+.1f}%" if pd.notna(v) else "N/A",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No monuments found matching the active filter combination.")

    # --- TAB 2: Financial Year YoY Trends ---
    with tab2:
        st.markdown(
            """
            <div style="margin-bottom: 12px;">
                <h3 style="color: #f1f5f9; font-size: 1.15rem; font-weight: 600; margin: 0;">
                    National Footfall Dynamics: FY 2022-23 vs. FY 2023-24
                </h3>
                <p style="color: #94a3b8; font-size: 0.84rem; margin-top: 2px;">
                    Comparison of official national aggregates demonstrates sustained domestic footing (+10.8%) alongside
                    a pronounced rebound in international tourist footfall (+60.1%) as global travel restrictions fully normalized.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fy_summary = (
            monument_df.groupby("financial_year")
            .agg(
                domestic=("domestic_visitors", "sum"),
                foreign=("foreign_visitors", "sum"),
                total=("total_visitors", "sum"),
            )
            .reset_index()
        )

        col_fy1, col_fy2 = st.columns(2)

        with col_fy1:
            fig_fy = go.Figure()
            fig_fy.add_trace(
                go.Bar(
                    x=fy_summary["financial_year"],
                    y=fy_summary["domestic"],
                    name="Domestic Footfall",
                    marker_color=DOMESTIC_COLOR,
                    text=fy_summary["domestic"].apply(lambda v: f"{v/1e7:.2f} Cr"),
                    textposition="auto",
                )
            )
            fig_fy.add_trace(
                go.Bar(
                    x=fy_summary["financial_year"],
                    y=fy_summary["foreign"],
                    name="Foreign Footfall",
                    marker_color=FOREIGN_COLOR,
                    text=fy_summary["foreign"].apply(lambda v: f"{v/1e5:.2f} Lakh"),
                    textposition="auto",
                )
            )
            fig_fy.update_layout(
                title="Annual Footfall Comparison by Category",
                barmode="group",
                paper_bgcolor=DARK_BG,
                plot_bgcolor=CARD_BG,
                font=dict(family="Inter, sans-serif", color="#e2e8f0"),
                xaxis=dict(title="Financial Year", gridcolor=BORDER_COLOR),
                yaxis=dict(title="Visitor Count", gridcolor=BORDER_COLOR, tickformat=",.0f"),
                margin=dict(l=20, r=20, t=40, b=20),
                height=380,
            )
            st.plotly_chart(fig_fy, use_container_width=True)

        with col_fy2:
            # Foreign footfall share comparison
            fy_summary["foreign_share"] = (fy_summary["foreign"] / fy_summary["total"]) * 100.0
            fig_share = go.Figure()
            fig_share.add_trace(
                go.Bar(
                    x=fy_summary["financial_year"],
                    y=fy_summary["foreign_share"],
                    marker=dict(
                        color=["#38bdf8", "#2dd4bf"],
                        line=dict(color="#ffffff", width=1),
                    ),
                    text=fy_summary["foreign_share"].apply(lambda v: f"{v:.2f}%"),
                    textposition="outside",
                )
            )
            fig_share.update_layout(
                title="Foreign Visitor Share of Total Monument Footfall (%)",
                paper_bgcolor=DARK_BG,
                plot_bgcolor=CARD_BG,
                font=dict(family="Inter, sans-serif", color="#e2e8f0"),
                xaxis=dict(title="Financial Year", gridcolor=BORDER_COLOR),
                yaxis=dict(title="Share (%)", gridcolor=BORDER_COLOR, range=[0, max(fy_summary["foreign_share"]) * 1.3]),
                margin=dict(l=20, r=20, t=40, b=20),
                height=380,
            )
            st.plotly_chart(fig_share, use_container_width=True)

        # Executive Context Box
        st.markdown(
            """
            <div style="background-color: #111c33; border: 1px solid #1e3a5f; padding: 16px 20px; border-radius: 8px; margin-top: 12px;">
                <div style="color: #38bdf8; font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;">
                    Executive Insight: Post-Pandemic Cultural Heritage Rebound
                </div>
                <div style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.6;">
                    Across the 145 centrally protected ticketed monuments in India:
                    <ul>
                        <li><strong>Domestic footfall</strong> expanded from <strong>4.79 Crore</strong> in FY 2022-23 to <strong>5.31 Crore</strong> in FY 2023-24 (+10.8% YoY).</li>
                        <li><strong>Foreign visitor traffic</strong> exhibited an extraordinary acceleration from <strong>14.45 Lakh</strong> to <strong>23.15 Lakh</strong> (+60.1% YoY), raising international visitor share from 2.93% to 4.18%.</li>
                        <li>The <strong>Taj Mahal</strong> alone accounted for 6.81 Lakh foreign visitors (29.4% of all international ticketed monument visits across India in FY 2023-24).</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- TAB 3: ASI Circles & States ---
    with tab3:
        st.markdown(
            f"""
            <div style="margin-bottom: 12px;">
                <h3 style="color: #f1f5f9; font-size: 1.15rem; font-weight: 600; margin: 0;">
                    Regional Distribution across 33 ASI Administrative Circles ({selected_fy})
                </h3>
                <p style="color: #94a3b8; font-size: 0.84rem; margin-top: 2px;">
                    The Archaeological Survey of India administers ticketed heritage sites through 33 circle jurisdictions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        circle_df = get_circle_footfall_summary(
            df=monument_df,
            financial_year="2023-24" if selected_fy == "All Years" else selected_fy,
        )

        if not circle_df.empty:
            top_circles = circle_df.head(15)
            fig_circle = px.bar(
                top_circles,
                x="total_visitors",
                y="circle",
                color="state_or_region",
                orientation="h",
                title=f"Top 15 ASI Circles by Total Visitor Volume ({selected_fy})",
                labels={"total_visitors": "Total Visitors", "circle": "ASI Circle", "state_or_region": "State / Region"},
            )
            fig_circle.update_layout(
                paper_bgcolor=DARK_BG,
                plot_bgcolor=CARD_BG,
                font=dict(family="Inter, sans-serif", color="#e2e8f0"),
                yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
                xaxis=dict(gridcolor=BORDER_COLOR, tickformat=",.0f"),
                margin=dict(l=20, r=20, t=40, b=20),
                height=480,
            )
            st.plotly_chart(fig_circle, use_container_width=True)

            st.dataframe(
                circle_df.rename(columns={
                    "circle": "ASI Circle",
                    "state_or_region": "State / Region",
                    "monument_count": "Ticketed Sites",
                    "domestic_visitors": "Domestic Visitors",
                    "foreign_visitors": "Foreign Visitors",
                    "total_visitors": "Total Footfall",
                    "foreign_share_pct": "Foreign Share (%)",
                }).style.format({
                    "Domestic Visitors": "{:,.0f}",
                    "Foreign Visitors": "{:,.0f}",
                    "Total Footfall": "{:,.0f}",
                    "Foreign Share (%)": "{:.2f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

    # --- TAB 4: Single-Monument Inspector ---
    with tab4:
        st.markdown(
            """
            <div style="margin-bottom: 12px;">
                <h3 style="color: #f1f5f9; font-size: 1.15rem; font-weight: 600; margin: 0;">
                    Monument Deep-Dive Inspector
                </h3>
                <p style="color: #94a3b8; font-size: 0.84rem; margin-top: 2px;">
                    Select any of the 145 centrally protected monuments to examine historical trajectories, foreign appeal, and official metrics.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        all_monuments = sorted(monument_df["monument_name"].dropna().unique().tolist())
        chosen_monument = st.selectbox(
            "Select Monument to Inspect",
            options=all_monuments,
            index=all_monuments.index("Taj Mahal") if "Taj Mahal" in all_monuments else 0,
        )

        mon_info = get_monument_comparison(monument_df, chosen_monument)
        if mon_info and mon_info.get("records"):
            m_records = mon_info["records"]
            m_circle = mon_info["circle"]
            m_state = mon_info["state_or_region"]

            st.markdown(
                f"""
                <div style="background-color: #111c33; border: 1px solid #1e3a5f; padding: 14px 18px; border-radius: 8px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <span style="font-size: 1.25rem; font-weight: 700; color: #f8fafc;">{chosen_monument}</span>
                            <span style="margin-left: 10px; color: #38bdf8; font-size: 0.85rem; font-weight: 600;">Circle: {m_circle}</span>
                            <span style="margin-left: 8px; color: #94a3b8; font-size: 0.85rem;">• State: {m_state}</span>
                        </div>
                        <div style="color: #2dd4bf; font-size: 0.8rem; font-weight: 500;">
                            Official ASI Centrally Protected Heritage Site
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            rec_df = pd.DataFrame(m_records)
            m_col1, m_col2 = st.columns([1, 1])

            with m_col1:
                # Trajectory chart
                fig_m = go.Figure()
                fig_m.add_trace(
                    go.Bar(
                        x=rec_df["financial_year"],
                        y=rec_df["domestic_visitors"],
                        name="Domestic",
                        marker_color=DOMESTIC_COLOR,
                    )
                )
                fig_m.add_trace(
                    go.Bar(
                        x=rec_df["financial_year"],
                        y=rec_df["foreign_visitors"],
                        name="Foreign",
                        marker_color=FOREIGN_COLOR,
                    )
                )
                fig_m.update_layout(
                    barmode="stack",
                    title="Financial Year Footfall Breakdown",
                    paper_bgcolor=DARK_BG,
                    plot_bgcolor=CARD_BG,
                    font=dict(family="Inter, sans-serif", color="#e2e8f0"),
                    xaxis=dict(title="Financial Year", gridcolor=BORDER_COLOR),
                    yaxis=dict(title="Visitors", gridcolor=BORDER_COLOR, tickformat=",.0f"),
                    margin=dict(l=20, r=20, t=30, b=20),
                    height=320,
                )
                st.plotly_chart(fig_m, use_container_width=True)

            with m_col2:
                # Metric Table
                sub_display = rec_df[[
                    "financial_year",
                    "domestic_visitors",
                    "foreign_visitors",
                    "total_visitors",
                    "foreign_visitor_share_pct",
                    "yoy_growth_pct",
                ]].rename(columns={
                    "financial_year": "FY",
                    "domestic_visitors": "Domestic",
                    "foreign_visitors": "Foreign",
                    "total_visitors": "Total Visitors",
                    "foreign_visitor_share_pct": "Foreign Share",
                    "yoy_growth_pct": "YoY Growth",
                })
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.dataframe(
                    sub_display.style.format({
                        "Domestic": lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A (Closed)",
                        "Foreign": lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A (Closed)",
                        "Total Visitors": lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A (Closed)",
                        "Foreign Share": lambda v: f"{v:.2f}%" if pd.notna(v) else "N/A",
                        "YoY Growth": lambda v: f"{v:+.1f}%" if pd.notna(v) else "Base Year",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

    # -------------------------------------------------------------------------
    # Governance & Methodology Footnote
    # -------------------------------------------------------------------------
    st.markdown("<hr style='border: 0; height: 1px; background: #172540; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-size: 0.78rem; color: #64748b; line-height: 1.5;">
            <strong>Data Source & Governance Notice:</strong><br>
            • Primary source: <em>Ministry of Tourism, Government of India</em>, published in the <em>India Tourism Data Compendium 2024</em> (Table 4.2.3).<br>
            • Reporting scope: Restricted strictly to 145 centrally protected monuments administered with ticketed access by the Archaeological Survey of India (ASI).<br>
            • Active query source: <strong>{db_source}</strong>. All figures reflect verified historical ticketing records; no values are extrapolated, modeled, or estimated.
        </div>
        """,
        unsafe_allow_html=True,
    )
