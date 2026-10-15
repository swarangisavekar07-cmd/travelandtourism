"""
Ingestion module for weather API and tourism data.
"""
from src.ingestion.destinations import Destination, DESTINATIONS, get_destination
from src.ingestion.weather_client import OpenMeteoClient, WeatherIngestionError, ingest_destination_weather
from src.ingestion.tourism_client import TourismDataIngestion, TourismIngestionError, load_and_inspect_tourism_data

__all__ = [
    "Destination",
    "DESTINATIONS",
    "get_destination",
    "OpenMeteoClient",
    "WeatherIngestionError",
    "ingest_destination_weather",
    "TourismDataIngestion",
    "TourismIngestionError",
    "load_and_inspect_tourism_data",
]
