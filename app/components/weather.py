"""
Weather Explorer component for TravelWise Platform.
Displays forward-looking 7-day daily weather forecasts for travel destinations
(Lonavala, Mahabaleshwar, Matheran) derived from hourly Open-Meteo predictions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.data_loader import get_destination_weather


def render_weather_explorer(weather_df: pd.DataFrame):
    """Renders the interactive Weather Explorer page."""
    # Header Banner
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                <h2 style="color: #f8fafc; margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em;">
                    Destination Weather Forecast Explorer
                </h2>
                <span style="color: #2dd4bf; font-size: 0.84rem; font-weight: 500; background-color: #112a2b; padding: 4px 10px; border-radius: 4px; border: 1px solid #0d9488;">
                    Forward-Looking 7-Day Horizon
                </span>
            </div>
            <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 0.9rem;">
                High-resolution daily weather metrics derived from 24 hourly readings per day via Open-Meteo Weather API.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if weather_df.empty:
        st.warning("No weather forecast records found in curated Parquet lake.")
        return

    # Forecast Classification Notice
    st.markdown(
        """
        <div style="background-color: #0d1b33; border: 1px solid #1e3a5f; border-left: 4px solid #14b8a6; padding: 10px 14px; border-radius: 4px; margin-bottom: 16px; font-size: 0.85rem; color: #cbd5e1;">
            <strong style="color: #2dd4bf;">Operational Status:</strong> All weather data represents
            <strong>forward-looking 7-day forecast simulations</strong>. These are operational predictions, not historical climatological averages.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Destination Selection Card
    available_destinations = sorted(weather_df["destination"].dropna().unique().tolist())

    col_sel, col_meta = st.columns([1, 2])

    with col_sel:
        selected_destination = st.selectbox(
            "Select Destination",
            options=available_destinations,
            index=0,
            help="Choose a destination to view its 7-day daily weather forecast.",
        )

    dest_data = get_destination_weather(weather_df, selected_destination)

    if dest_data.empty:
        st.error(f"No forecast records found for {selected_destination}.")
        return

    # Metadata details
    lat = dest_data["latitude"].iloc[0] if "latitude" in dest_data.columns else None
    lon = dest_data["longitude"].iloc[0] if "longitude" in dest_data.columns else None
    retrieved_at = dest_data["latest_retrieved_at_utc"].iloc[0] if "latest_retrieved_at_utc" in dest_data.columns else "N/A"
    records_count = len(dest_data)

    with col_meta:
        coords_str = f"{lat:.4f}° N, {lon:.4f}° E" if lat and lon else "N/A"
        st.markdown(
            f"""
            <div style="background-color: #111c33; padding: 10px 14px; border-radius: 6px; border: 1px solid #1e3a5f; margin-top: 4px;">
                <div style="display: flex; gap: 16px; flex-wrap: wrap; font-size: 0.82rem; color: #cbd5e1;">
                    <div><span style="color: #94a3b8;">Coordinates:</span> <strong>{coords_str}</strong></div>
                    <div><span style="color: #94a3b8;">Retrieved:</span> <strong>{retrieved_at} UTC</strong></div>
                    <div><span style="color: #94a3b8;">Daily Records:</span> <strong>{records_count} Days</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Aligned 5-Column Forecast KPI Bar
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    avg_temp = dest_data["temp_avg_c"].mean()
    min_temp = dest_data["temp_min_c"].min()
    max_temp = dest_data["temp_max_c"].max()
    total_precip = dest_data["total_precipitation_mm"].sum()
    max_precip_prob = dest_data["max_precipitation_probability_pct"].max()
    max_wind = dest_data["max_wind_speed_kmh"].max()

    with kpi_col1:
        st.metric(
            label="Mean Temperature",
            value=f"{avg_temp:.1f} °C",
            help="7-day average temperature across all forecast hours.",
        )

    with kpi_col2:
        st.metric(
            label="Weekly Range",
            value=f"{min_temp:.1f}° – {max_temp:.1f}°",
            delta=f"Δ {max_temp - min_temp:.1f} °C Spread",
            delta_color="off",
            help="Minimum to maximum temperature range expected across the 7-day period.",
        )

    with kpi_col3:
        st.metric(
            label="Cumulative Rainfall",
            value=f"{total_precip:.1f} mm",
            delta="Dry Conditions" if total_precip < 5 else "Rain Expected",
            delta_color="off",
            help="Sum of expected precipitation across all 7 forecast days.",
        )

    with kpi_col4:
        st.metric(
            label="Peak Rain Prob.",
            value=f"{max_precip_prob}%",
            delta="High Chance" if max_precip_prob > 50 else "Low Chance",
            delta_color="inverse",
            help="Highest single-day precipitation probability.",
        )

    with kpi_col5:
        st.metric(
            label="Max Wind Speed",
            value=f"{max_wind:.1f} km/h",
            help="Peak wind gust speed forecasted.",
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Forecast Visualizations Tabs
    w_tab1, w_tab2, w_tab3 = st.tabs([
        "Temperature Profile",
        "Precipitation & Rain Probability",
        "7-Day Forecast Matrix",
    ])

    with w_tab1:
        st.markdown(
            f"""
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                Daily Temperature Bounds & Mean (°C) — {selected_destination}
            </div>
            """,
            unsafe_allow_html=True,
        )

        fig_temp = go.Figure()

        # Shaded ribbon between Min and Max
        fig_temp.add_trace(go.Scatter(
            x=dest_data["forecast_date"],
            y=dest_data["temp_max_c"],
            mode="lines",
            line=dict(color="#38bdf8", width=1.5, dash="dot"),
            name="Max Temp (°C)",
        ))
        fig_temp.add_trace(go.Scatter(
            x=dest_data["forecast_date"],
            y=dest_data["temp_avg_c"],
            mode="lines+markers",
            line=dict(color="#0284c7", width=3),
            marker=dict(size=8, color="#38bdf8"),
            name="Mean Temp (°C)",
        ))
        fig_temp.add_trace(go.Scatter(
            x=dest_data["forecast_date"],
            y=dest_data["temp_min_c"],
            mode="lines",
            line=dict(color="#14b8a6", width=1.5, dash="dot"),
            name="Min Temp (°C)",
            fill="tonexty",
            fillcolor="rgba(2, 132, 199, 0.08)",
        ))

        fig_temp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color="#cbd5e1", family="Inter, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            xaxis=dict(showgrid=False, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1"), title=""),
            yaxis=dict(showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1"), title="Temperature (°C)"),
            hovermode="x unified",
            height=340,
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with w_tab2:
        st.markdown(
            f"""
            <div style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 8px; font-weight: 500;">
                Precipitation Volume (mm) & Rain Likelihood (%) — {selected_destination}
            </div>
            """,
            unsafe_allow_html=True,
        )

        fig_rain = make_subplots(specs=[[{"secondary_y": True}]])

        fig_rain.add_trace(
            go.Bar(
                x=dest_data["forecast_date"],
                y=dest_data["total_precipitation_mm"],
                name="Rainfall (mm)",
                marker_color="#0284c7",
                opacity=0.85,
            ),
            secondary_y=False,
        )

        fig_rain.add_trace(
            go.Scatter(
                x=dest_data["forecast_date"],
                y=dest_data["max_precipitation_probability_pct"],
                name="Rain Probability (%)",
                mode="lines+markers",
                line=dict(color="#14b8a6", width=2.5),
                marker=dict(size=7, color="#2dd4bf"),
            ),
            secondary_y=True,
        )

        fig_rain.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color="#cbd5e1", family="Inter, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            xaxis=dict(showgrid=False, linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1"), title=""),
            height=340,
        )
        fig_rain.update_yaxes(title_text="Rainfall (mm)", secondary_y=False, showgrid=True, gridcolor="#172540", linecolor="#1e3a5f", tickfont=dict(color="#cbd5e1"))
        fig_rain.update_yaxes(title_text="Probability (%)", secondary_y=True, showgrid=False, range=[0, 100], tickfont=dict(color="#cbd5e1"))

        st.plotly_chart(fig_rain, use_container_width=True)

    with w_tab3:
        table_cols = [
            "forecast_date",
            "temp_min_c",
            "temp_max_c",
            "temp_avg_c",
            "total_precipitation_mm",
            "max_precipitation_probability_pct",
            "avg_wind_speed_kmh",
            "max_wind_speed_kmh",
            "hourly_records_count",
            "is_forecast",
        ]
        col_rename = {
            "forecast_date": "Forecast Date",
            "temp_min_c": "Min Temp (°C)",
            "temp_max_c": "Max Temp (°C)",
            "temp_avg_c": "Avg Temp (°C)",
            "total_precipitation_mm": "Rainfall (mm)",
            "max_precipitation_probability_pct": "Rain Prob (%)",
            "avg_wind_speed_kmh": "Avg Wind (km/h)",
            "max_wind_speed_kmh": "Max Wind (km/h)",
            "hourly_records_count": "Hourly Obs",
            "is_forecast": "Forecast Flag",
        }
        st.dataframe(
            dest_data[table_cols].rename(columns=col_rename),
            use_container_width=True,
            hide_index=True,
        )
