"""
Module initialization for app components.
Exports modular view rendering functions for Streamlit.
"""

from app.components.overview import render_overview
from app.components.state_explorer import render_state_explorer
from app.components.tourism import render_tourism_analytics
from app.components.architecture import render_architecture
from app.components.weather import render_weather_explorer
from app.components.data_quality import render_data_quality
from app.components.monument_analysis import render_monument_analysis

__all__ = [
    "render_overview",
    "render_state_explorer",
    "render_tourism_analytics",
    "render_architecture",
    "render_weather_explorer",
    "render_data_quality",
    "render_monument_analysis",
]
