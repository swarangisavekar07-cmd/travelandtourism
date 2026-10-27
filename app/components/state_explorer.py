"""
State Explorer component for TravelWise Platform (Feature Two: State-wise Tourism Analysis).
Allows users to explore any verified Indian State or Union Territory with dynamic
KPIs, year-wise trajectories, domestic vs foreign breakdowns, automated analytical
narratives, and side-by-side state benchmarking.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List

from app.data_loader import (
    get_all_distinct_states,
    compute_state_analytics,
    format_large_number,
)


def format_visit_metric(val: Optional[float], is_complete: bool = True) -> str:
    """Formats visit count or returns clear unrecorded indicator."""
    if val is None or pd.isna(val) or not is_complete:
        return "N/A (Unrecorded)"
    return format_large_number(val)


def render_state_explorer(tourism_df: pd.DataFrame, db_source: str = "SQL Database"):
    """
    Renders Feature Two: Dedicated State-wise Tourism Analysis.
    Searchable, dynamic, strictly accurate, and transparent.
    """
    # Retrieve verified states strictly excluding Total India aggregate
    verified_states = get_all_distinct_states(tourism_df)

    if not verified_states:
        st.error("No verified states found in dataset.")
        return

    # Header
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #111c33 0%, #0b1329 100%); padding: 22px 24px; border-radius: 8px; border: 1px solid #1e3a5f; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.6rem;">🏛️</span>
                        <h1 style="color: #f8fafc; margin: 0; font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;">
                            State Explorer
                        </h1>
                    </div>
                    <p style="color: #94a3b8; margin: 6px 0 0 0; font-size: 0.95rem; line-height: 1.5;">
                        Interactive Single-State & UT Deep-Dive: Trajectories, Visitor Mix, YoY Growth, and Comparative Benchmarking
                    </p>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                    <span style="background-color: #1e3a5f; color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; border: 1px solid #0284c7;">
                        36 Verified States/UTs
                    </span>
                    <span style="background-color: #132e35; color: #2dd4bf; padding: 4px 10px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; border: 1px solid #0d9488;">
                        Zero Double-Counting
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # State & Year Selection Controls
    col_state_select, col_year_select = st.columns([1.6, 1.2])

    with col_state_select:
        # Default to popular destination like Goa or Maharashtra if present
        default_idx = verified_states.index("Goa") if "Goa" in verified_states else 0
        selected_state = st.selectbox(
            "Select State or Union Territory",
            options=verified_states,
            index=default_idx,
            help="Choose any of the 36 verified Indian States or UTs in the dataset.",
        )

    with col_year_select:
        available_years = sorted(tourism_df["year"].dropna().unique().tolist())
        year_options = ["All Years (Cumulative 2018–2022)"] + [str(y) for y in available_years]
        selected_year_str = st.selectbox(
            "Historical Period / Year",
            options=year_options,
            index=0,
            help="Filter for a specific historical year or evaluate cumulative 5-year totals.",
        )
        selected_year = int(selected_year_str) if selected_year_str != "All Years (Cumulative 2018–2022)" else None

    # Compute single-state analytics dynamically
    analytics = compute_state_analytics(df=tourism_df, state_name=selected_state, year=selected_year)

    # State Title Banner
    period_label = f"Year {selected_year}" if selected_year else "Cumulative (2018–2022)"
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin: 16px 0 12px 0;">
            <h2 style="color: #f1f5f9; margin: 0; font-size: 1.35rem; font-weight: 700;">
                {selected_state} — Tourism Profile ({period_label})
            </h2>
            <span style="color: #38bdf8; font-size: 0.85rem; font-weight: 600;">
                National Overall Rank: #{analytics['total_rank']} of {analytics['total_states_count']}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metric Cards Strip
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        dom_val = analytics["domestic_visits"]
        dom_share_text = f"{analytics['domestic_share']}% of visits" if analytics["domestic_share"] is not None else "Share: N/A"
        st.metric(
            label="Domestic Tourist Visits (DTV)",
            value=format_visit_metric(dom_val),
            delta=dom_share_text,
            delta_color="normal",
            help="Indian residents visiting this destination.",
        )

    with m2:
        for_val = analytics["foreign_visits"]
        for_share_text = f"{analytics['foreign_share']}% of visits" if analytics["foreign_share"] is not None else "Share: N/A"
        st.metric(
            label="Foreign Tourist Visits (FTV)",
            value=format_visit_metric(for_val),
            delta=for_share_text,
            delta_color="normal",
            help="International travelers arriving in this state.",
        )

    with m3:
        tot_val = analytics["total_visits"]
        tot_label = format_visit_metric(tot_val, is_complete=analytics["is_complete"])
        rank_delta = f"Rank #{analytics['total_rank']} in India" if analytics["total_rank"] else "Rank: N/A"
        st.metric(
            label="Total Reported Visits",
            value=tot_label,
            delta=rank_delta,
            delta_color="off",
            help="Combined Domestic and Foreign visits. Shows N/A if either category was unrecorded.",
        )

    with m4:
        # Growth metric (if single year) or peak year metric (if cumulative)
        if selected_year is not None and analytics["total_yoy"] is not None:
            growth_val = analytics["total_yoy"]
            delta_str = f"{growth_val:+.2f}% YoY"
            st.metric(
                label="Year-over-Year Growth",
                value=f"{growth_val:+.2f}%",
                delta="vs Prior Year",
                delta_color="normal" if growth_val >= 0 else "inverse",
                help="Annual growth compared to previous year.",
            )
        elif selected_year == 2018:
            st.metric(
                label="YoY Growth Rate",
                value="Baseline Year",
                delta="First Series Year",
                delta_color="off",
                help="2018 is the initial observation year in this dataset.",
            )
        else:
            st.metric(
                label="Historical Peak Year",
                value=f"{analytics['peak_year']}" if analytics['peak_year'] else "N/A",
                delta=f"{format_large_number(analytics['peak_visits'])} Peak Volume",
                delta_color="off",
                help="Year with the highest recorded total tourist footfall for this state.",
            )

    # Automated Analytical Narrative Box
    st.markdown(
        f"""
        <div style="background-color: #0d1b33; border: 1px solid #1e3a5f; border-left: 4px solid #0284c7; padding: 14px 18px; border-radius: 6px; margin: 18px 0; font-size: 0.88rem; color: #e2e8f0; line-height: 1.6;">
            <div style="color: #38bdf8; font-weight: 600; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
                Automated Analytical Summary (Computed Data Insight)
            </div>
            {analytics['analytical_summary']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # State Analytics Tabs
    tab_trend, tab_mix, tab_growth, tab_bench, tab_data = st.tabs([
        "📈 Annual Trajectory (2018–2022)",
        "👥 Domestic vs. Foreign Mix",
        "📊 YoY Growth Trajectory",
        "🔄 State Benchmark & Comparison",
        "📋 Verified State Records",
    ])

    yearly_traj = analytics["yearly_trajectory"]

    # -------------------------------------------------------------------------
    # TAB 1: Annual Trajectory (2018-2022)
    # -------------------------------------------------------------------------
    with tab_trend:
        st.markdown(
            f"""
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                {selected_state}: Annual Trajectory of Domestic and Foreign Visits (2018–2022)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Plotly multi-line chart
        fig_state_trend = go.Figure()

        fig_state_trend.add_trace(go.Scatter(
            x=yearly_traj["year"],
            y=yearly_traj["domestic"],
            mode="lines+markers",
            name="Domestic Visits (DTV)",
            line=dict(color="#0284c7", width=3),
            marker=dict(size=8, color="#0284c7"),
        ))

        fig_state_trend.add_trace(go.Scatter(
            x=yearly_traj["year"],
            y=yearly_traj["foreign"],
            mode="lines+markers",
            name="Foreign Visits (FTV)",
            line=dict(color="#14b8a6", width=3),
            marker=dict(size=8, color="#14b8a6"),
        ))

        fig_state_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10),
            font=dict(color="#cbd5e1", family="Inter, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            xaxis=dict(showgrid=False, dtick=1, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
            yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
            hovermode="x unified",
            height=380,
        )
        st.plotly_chart(fig_state_trend, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 2: Domestic vs. Foreign Mix
    # -------------------------------------------------------------------------
    with tab_mix:
        c_mix1, c_mix2 = st.columns([1, 1.4])

        with c_mix1:
            st.markdown(
                """
                <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                    Tourist Mix Breakdown
                </div>
                """,
                unsafe_allow_html=True,
            )
            if analytics["domestic_visits"] is not None and analytics["foreign_visits"] is not None:
                pie_df = pd.DataFrame([
                    {"Category": "Domestic", "Visits": analytics["domestic_visits"]},
                    {"Category": "Foreign", "Visits": analytics["foreign_visits"]},
                ])
                fig_pie = px.pie(
                    pie_df,
                    values="Visits",
                    names="Category",
                    hole=0.55,
                    color="Category",
                    color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
                    height=340,
                )
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=10, b=10),
                    font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, title=""),
                )
                fig_pie.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    insidetextfont=dict(color="#ffffff", size=13),
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Incomplete data for tourist mix in this selection.")

        with c_mix2:
            st.markdown(
                """
                <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                    Annual Category Volume Distribution
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Long format for stacked bar
            state_long = tourism_df[
                (tourism_df["state"] == selected_state) & (tourism_df["is_aggregate"] == False)
            ].copy()

            fig_stack = px.bar(
                state_long,
                x="year",
                y="visit_count",
                color="category",
                barmode="stack",
                labels={"visit_count": "Visits", "year": "Year", "category": "Category"},
                color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
                height=340,
            )
            fig_stack.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                xaxis=dict(showgrid=False, dtick=1, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
            )
            st.plotly_chart(fig_stack, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 3: YoY Growth Trajectory
    # -------------------------------------------------------------------------
    with tab_growth:
        st.markdown(
            f"""
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                {selected_state}: Year-over-Year Percentage Growth or Contraction
            </div>
            """,
            unsafe_allow_html=True,
        )

        growth_data = []
        for _, row in yearly_traj.iterrows():
            if pd.notna(row["domestic_yoy"]):
                growth_data.append({"year": int(row["year"]), "category": "Domestic", "yoy_pct": row["domestic_yoy"]})
            if pd.notna(row["foreign_yoy"]):
                growth_data.append({"year": int(row["year"]), "category": "Foreign", "yoy_pct": row["foreign_yoy"]})

        if growth_data:
            gdf = pd.DataFrame(growth_data)
            fig_growth_bars = px.bar(
                gdf,
                x="year",
                y="yoy_pct",
                color="category",
                barmode="group",
                labels={"yoy_pct": "YoY Growth (%)", "year": "Historical Year", "category": "Category"},
                color_discrete_map={"Domestic": "#0284c7", "Foreign": "#14b8a6"},
                height=380,
            )
            fig_growth_bars.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                xaxis=dict(showgrid=False, dtick=1, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", zeroline=True, zerolinecolor="#94a3b8"),
            )
            st.plotly_chart(fig_growth_bars, use_container_width=True)
        else:
            st.info("YoY growth calculations are not available for this selection (e.g. baseline or unrecorded year).")

    # -------------------------------------------------------------------------
    # TAB 4: State Benchmark & Comparison
    # -------------------------------------------------------------------------
    with tab_bench:
        st.markdown(
            """
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 12px; font-weight: 500;">
                Side-by-Side State Benchmark & Direct Comparison
            </div>
            """,
            unsafe_allow_html=True,
        )

        other_states = [s for s in verified_states if s != selected_state]
        default_bench = "Kerala" if "Kerala" in other_states else (other_states[0] if other_states else None)

        benchmark_state = st.selectbox(
            f"Select a Benchmark State to Compare with {selected_state}",
            options=other_states,
            index=other_states.index(default_bench) if default_bench in other_states else 0,
        )

        if benchmark_state:
            bench_analytics = compute_state_analytics(df=tourism_df, state_name=benchmark_state, year=selected_year)

            # Comparative Table
            comp_table = [
                {
                    "Metric": "Total Tourist Footfall",
                    selected_state: format_visit_metric(analytics["total_visits"], analytics["is_complete"]),
                    benchmark_state: format_visit_metric(bench_analytics["total_visits"], bench_analytics["is_complete"]),
                },
                {
                    "Metric": "Domestic Tourist Visits (DTV)",
                    selected_state: format_visit_metric(analytics["domestic_visits"]),
                    benchmark_state: format_visit_metric(bench_analytics["domestic_visits"]),
                },
                {
                    "Metric": "Foreign Tourist Visits (FTV)",
                    selected_state: format_visit_metric(analytics["foreign_visits"]),
                    benchmark_state: format_visit_metric(bench_analytics["foreign_visits"]),
                },
                {
                    "Metric": "Domestic Share (%)",
                    selected_state: f"{analytics['domestic_share']}%" if analytics["domestic_share"] is not None else "N/A",
                    benchmark_state: f"{bench_analytics['domestic_share']}%" if bench_analytics["domestic_share"] is not None else "N/A",
                },
                {
                    "Metric": "Foreign Share (%)",
                    selected_state: f"{analytics['foreign_share']}%" if analytics["foreign_share"] is not None else "N/A",
                    benchmark_state: f"{bench_analytics['foreign_share']}%" if bench_analytics["foreign_share"] is not None else "N/A",
                },
                {
                    "Metric": "All-India Rank (Overall Footfall)",
                    selected_state: f"#{analytics['total_rank']}" if analytics["total_rank"] else "N/A",
                    benchmark_state: f"#{bench_analytics['total_rank']}" if bench_analytics["total_rank"] else "N/A",
                },
            ]

            st.dataframe(pd.DataFrame(comp_table), use_container_width=True, hide_index=True)

            # Comparative Line Chart
            comp_traj = yearly_traj.rename(columns={"total": selected_state})[["year", selected_state]]
            bench_traj = bench_analytics["yearly_trajectory"].rename(columns={"total": benchmark_state})[["year", benchmark_state]]
            merged_comp = pd.merge(comp_traj, bench_traj, on="year", how="outer").sort_values("year")

            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(
                x=merged_comp["year"],
                y=merged_comp[selected_state],
                mode="lines+markers",
                name=selected_state,
                line=dict(color="#0284c7", width=3),
                marker=dict(size=8),
            ))
            fig_comp.add_trace(go.Scatter(
                x=merged_comp["year"],
                y=merged_comp[benchmark_state],
                mode="lines+markers",
                name=benchmark_state,
                line=dict(color="#f59e0b", width=3),
                marker=dict(size=8),
            ))
            fig_comp.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(color="#cbd5e1", family="Inter, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                xaxis=dict(showgrid=False, dtick=1, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1")),
                height=340,
            )
            st.plotly_chart(fig_comp, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 5: Verified State Records
    # -------------------------------------------------------------------------
    with tab_data:
        st.markdown(
            f"""
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                Underlying SQL Records for {selected_state}
            </div>
            """,
            unsafe_allow_html=True,
        )

        state_rows = tourism_df[tourism_df["state"] == selected_state].copy()
        display_cols = ["state", "category", "year", "visit_count", "prev_year_visit_count", "yoy_growth_pct", "is_estimated"]
        rename_map = {
            "state": "State / UT",
            "category": "Category",
            "year": "Year",
            "visit_count": "Recorded Visits",
            "prev_year_visit_count": "Prior Year Visits",
            "yoy_growth_pct": "YoY Growth (%)",
            "is_estimated": "Estimated Flag",
        }

        st.dataframe(
            state_rows[display_cols].rename(columns=rename_map).sort_values(by=["Year", "Category"]),
            use_container_width=True,
            hide_index=True,
        )
