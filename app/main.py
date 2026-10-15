"""
TravelWise — Tourism & Weather Intelligence Platform.
Main Streamlit Application Entrypoint.

Enterprise Business Intelligence interface for multi-dimensional historical
tourism analytics and high-resolution destination weather forecasts.
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.data_loader import load_tourism_data, load_weather_data
from app.components import (
    render_overview,
    render_tourism_analytics,
    render_weather_explorer,
    render_data_quality,
)


def apply_custom_styles():
    """Injects custom CSS for executive aesthetics, accessible contrast, and compact layout."""
    st.markdown(
        """
        <style>
        /* Import Inter for crisp business typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"], .stMarkdown, p, span, label {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            letter-spacing: -0.01em;
        }

        /* Top padding and responsive container margins */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1380px !important;
        }

        /* Executive Metric Cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #131f37 0%, #0d1629 100%) !important;
            border: 1px solid #1e3a5f !important;
            padding: 16px 20px !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
            transition: all 0.2s ease-in-out !important;
        }
        div[data-testid="stMetric"]:hover {
            border-color: #0284c7 !important;
            box-shadow: 0 6px 16px rgba(2, 132, 199, 0.2) !important;
            transform: translateY(-2px);
        }
        div[data-testid="stMetricLabel"] {
            color: #cbd5e1 !important; /* High-contrast readable light slate */
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 4px !important;
        }
        div[data-testid="stMetricValue"] {
            color: #f8fafc !important; /* Crisp pure white */
            font-size: 1.85rem !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stMetricDelta"] {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0a1122 !important;
            border-right: 1px solid #172540 !important;
        }
        section[data-testid="stSidebar"] div.stRadio > label {
            display: none !important;
        }
        section[data-testid="stSidebar"] div.stRadio > div[role="radiogroup"] {
            gap: 6px !important;
        }
        section[data-testid="stSidebar"] div.stRadio label[data-baseweb="radio"] {
            background-color: #131f37 !important;
            border: 1px solid #1e3a5f !important;
            padding: 10px 14px !important;
            border-radius: 6px !important;
            color: #e2e8f0 !important;
            font-weight: 500 !important;
            font-size: 0.92rem !important;
            transition: all 0.15s ease !important;
            width: 100% !important;
            margin-bottom: 4px !important;
        }
        section[data-testid="stSidebar"] div.stRadio label[data-baseweb="radio"]:hover {
            border-color: #0284c7 !important;
            background-color: #192744 !important;
            color: #ffffff !important;
        }
        section[data-testid="stSidebar"] div.stRadio label[data-baseweb="radio"] > div:first-child {
            display: none !important; /* Hide default radio circle for pill appearance */
        }

        /* Expander and Card Styling */
        div[data-testid="stExpander"] {
            background-color: #111c33 !important;
            border: 1px solid #1e3a5f !important;
            border-radius: 8px !important;
            margin-bottom: 1.2rem !important;
        }
        div[data-testid="stExpander"] summary {
            color: #f1f5f9 !important;
            font-weight: 600 !important;
            padding: 12px 16px !important;
        }

        /* Tab Navigation Bar */
        div[data-baseweb="tab-list"] {
            gap: 8px !important;
            border-bottom: 1px solid #1e3a5f !important;
            margin-bottom: 1.2rem !important;
        }
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
            color: #94a3b8 !important;
            font-weight: 500 !important;
            padding: 8px 16px !important;
            border-radius: 6px 6px 0 0 !important;
            font-size: 0.95rem !important;
        }
        button[data-baseweb="tab"]:hover {
            color: #f1f5f9 !important;
            background-color: rgba(2, 132, 199, 0.08) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #38bdf8 !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #0284c7 !important;
        }

        /* Form Inputs & Selectboxes */
        div[data-baseweb="select"] > div {
            background-color: #0d1629 !important;
            border: 1px solid #1e3a5f !important;
            color: #f8fafc !important;
            border-radius: 6px !important;
        }
        div[data-baseweb="select"] > div:hover {
            border-color: #0284c7 !important;
        }
        div[data-baseweb="tag"] {
            background-color: #1e3a5f !important;
            color: #f1f5f9 !important;
        }

        /* DataTables */
        div[data-testid="stDataFrame"] {
            border: 1px solid #1e3a5f !important;
            border-radius: 6px !important;
            overflow: hidden !important;
        }

        /* Info Alert Styling */
        div[data-testid="stAlert"] {
            background-color: #0f1f38 !important;
            border: 1px solid #1e4a7a !important;
            border-left: 4px solid #0284c7 !important;
            color: #cbd5e1 !important;
            border-radius: 6px !important;
            padding: 12px 16px !important;
        }

        /* Subtle scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #0b1329;
        }
        ::-webkit-scrollbar-thumb {
            background: #1e3a5f;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #0284c7;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="TravelWise — Tourism & Weather Analytics",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_custom_styles()

    # Load Curated Datasets Directly from Parquet (no live DB required)
    try:
        tourism_df = load_tourism_data()
    except Exception as e:
        st.error(
            f"**Error Loading Tourism Dataset**: {e}\n\n"
            "Please ensure `data/processed/tourism/india_tourism_statewise_normalized.parquet` exists "
            "by executing the PySpark curation pipeline: `python -m src.pipeline.run_tourism_pipeline`"
        )
        tourism_df = None

    try:
        weather_df = load_weather_data()
    except Exception as e:
        st.error(
            f"**Error Loading Weather Forecast Dataset**: {e}\n\n"
            "Please ensure `data/processed/weather/daily_weather_forecast_curated.parquet` exists "
            "by executing the weather pipeline: `python -m src.pipeline.run_weather_pipeline`"
        )
        weather_df = None

    # Sidebar Navigation & Branding
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 4px 0 16px 0;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.4rem;">✈️</span>
                    <h2 style="color: #38bdf8; margin: 0; font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em;">
                        TravelWise
                    </h2>
                </div>
                <div style="color: #94a3b8; font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px;">
                    Data Engineering Platform
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("NAVIGATION")
        nav_choice = st.radio(
            "Navigate",
            options=[
                "Overview",
                "Tourism Analytics",
                "Weather Explorer",
                "Data Quality",
            ],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("<hr style='border: 0; height: 1px; background: #172540; margin: 20px 0 16px 0;'>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="background-color: #111c33; padding: 14px; border-radius: 8px; border: 1px solid #1e3a5f;">
                <div style="color: #38bdf8; font-size: 0.8rem; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">
                    Engine Specifications
                </div>
                <table style="width: 100%; font-size: 0.78rem; color: #cbd5e1; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 2px 0; color: #94a3b8;">ETL Engine:</td>
                        <td style="text-align: right; font-weight: 500;">PySpark 3.5.1</td>
                    </tr>
                    <tr>
                        <td style="padding: 2px 0; color: #94a3b8;">Lake Format:</td>
                        <td style="text-align: right; font-weight: 500;">Snappy Parquet</td>
                    </tr>
                    <tr>
                        <td style="padding: 2px 0; color: #94a3b8;">RDBMS Store:</td>
                        <td style="text-align: right; font-weight: 500;">PostgreSQL 18</td>
                    </tr>
                    <tr>
                        <td style="padding: 2px 0; color: #94a3b8;">ORM / Model:</td>
                        <td style="text-align: right; font-weight: 500;">SQLAlchemy 2.0</td>
                    </tr>
                    <tr>
                        <td style="padding: 2px 0; color: #94a3b8;">Tourism Series:</td>
                        <td style="text-align: right; font-weight: 500;">2018 – 2022</td>
                    </tr>
                    <tr>
                        <td style="padding: 2px 0; color: #94a3b8;">Weather Horizon:</td>
                        <td style="text-align: right; font-weight: 500;">7 Days (Daily)</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border: 0; height: 1px; background: #172540; margin: 16px 0 12px 0;'>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; color: #64748b; font-size: 0.74rem;">
                Academic Demonstration Edition<br>TravelWise Analytics v1.0
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Halt if datasets are missing
    if tourism_df is None or weather_df is None:
        st.stop()

    # Route navigation
    if nav_choice == "Overview":
        render_overview(tourism_df=tourism_df, weather_df=weather_df)
    elif nav_choice == "Tourism Analytics":
        render_tourism_analytics(df=tourism_df)
    elif nav_choice == "Weather Explorer":
        render_weather_explorer(weather_df=weather_df)
    elif nav_choice == "Data Quality":
        render_data_quality(tourism_df=tourism_df, weather_df=weather_df)


if __name__ == "__main__":
    main()
