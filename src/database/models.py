from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Boolean,
    DateTime,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TourismStatewiseAnnual(Base):
    """
    Normalized state-level annual tourism statistics (2018-2022).
    Includes domestic and foreign tourist visits, YoY growth, and aggregate classification.
    """
    __tablename__ = "tourism_statewise_annual"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(String(100), nullable=False, index=True)
    category = Column(String(20), nullable=False, index=True)  # 'Domestic' or 'Foreign'
    year = Column(Integer, nullable=False, index=True)
    visit_count = Column(BigInteger, nullable=True)  # Preserves genuine historical nulls
    is_aggregate = Column(Boolean, nullable=False, default=False, index=True)  # True for 'Total India'
    entity_type = Column(String(30), nullable=False, default="STATE_OR_UT")   # 'STATE_OR_UT' vs 'AGGREGATE_TOTAL'
    is_estimated = Column(Boolean, nullable=False, default=False)             # True for MH & DL 2022
    prev_year_visit_count = Column(BigInteger, nullable=True)
    yoy_growth_pct = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("state", "category", "year", name="uq_tourism_state_category_year"),
        Index("idx_tourism_state_category", "state", "category"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state,
            "category": self.category,
            "year": self.year,
            "visit_count": self.visit_count,
            "is_aggregate": self.is_aggregate,
            "entity_type": self.entity_type,
            "is_estimated": self.is_estimated,
            "prev_year_visit_count": self.prev_year_visit_count,
            "yoy_growth_pct": self.yoy_growth_pct,
        }

    def __repr__(self) -> str:
        return f"<TourismStatewiseAnnual(state='{self.state}', category='{self.category}', year={self.year}, visits={self.visit_count})>"

class WeatherDailyForecast(Base):
    """
    Daily aggregated numerical weather forecast metrics for travel destinations.
    Derived from Open-Meteo hourly forecasts.
    """
    __tablename__ = "weather_daily_forecast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    destination = Column(String(100), nullable=False, index=True)
    forecast_date = Column(String(10), nullable=False, index=True)  # 'YYYY-MM-DD'
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    temp_avg_c = Column(Float, nullable=True)
    total_precipitation_mm = Column(Float, nullable=True)
    max_precipitation_probability_pct = Column(Integer, nullable=True)
    avg_precipitation_probability_pct = Column(Float, nullable=True)
    avg_wind_speed_kmh = Column(Float, nullable=True)
    max_wind_speed_kmh = Column(Float, nullable=True)
    hourly_records_count = Column(Integer, nullable=False, default=24)
    metric_type = Column(String(60), nullable=False, default="7_DAY_HOURLY_FORECAST_DAILY_AGGREGATE")
    is_forecast = Column(Boolean, nullable=False, default=True)  # Clearly labels as forecast
    latest_retrieved_at_utc = Column(String(50), nullable=True)
    source_api = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("destination", "forecast_date", name="uq_weather_destination_date"),
        Index("idx_weather_destination_date", "destination", "forecast_date"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "destination": self.destination,
            "forecast_date": self.forecast_date,
            "temp_avg_c": self.temp_avg_c,
            "total_precipitation_mm": self.total_precipitation_mm,
            "max_precipitation_probability_pct": self.max_precipitation_probability_pct,
            "avg_wind_speed_kmh": self.avg_wind_speed_kmh,
            "is_forecast": self.is_forecast,
            "latest_retrieved_at_utc": self.latest_retrieved_at_utc,
        }

    def __repr__(self) -> str:
        return f"<WeatherDailyForecast(destination='{self.destination}', date='{self.forecast_date}', temp_avg={self.temp_avg_c}C, precip={self.total_precipitation_mm}mm)>"
