import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from src.ingestion.destinations import Destination, DESTINATIONS, get_destination

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

class WeatherIngestionError(Exception):
    """Custom exception raised when weather ingestion fails."""
    pass

class OpenMeteoClient:
    """Client for fetching live weather forecast from Open-Meteo API."""

    def __init__(self, base_url: str = OPEN_METEO_URL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    def fetch_hourly_forecast(self, destination: Destination) -> Dict[str, Any]:
        """
        Fetches hourly weather forecast for a given destination.
        Params requested: temperature_2m, precipitation_probability, precipitation, wind_speed_10m.
        """
        params = {
            "latitude": destination.latitude,
            "longitude": destination.longitude,
            "hourly": [
                "temperature_2m",
                "precipitation_probability",
                "precipitation",
                "wind_speed_10m",
            ],
            "timezone": "auto"
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"HTTP request error fetching weather for {destination.name}: {e}")
            raise WeatherIngestionError(f"Failed to retrieve weather data for {destination.name}: {e}") from e
        except ValueError as e:
            logger.error(f"Failed to parse JSON response for {destination.name}: {e}")
            raise WeatherIngestionError(f"Invalid JSON received for {destination.name}: {e}") from e

        # Validate structure
        if "hourly" not in data or not isinstance(data["hourly"], dict):
            raise WeatherIngestionError(f"Missing 'hourly' forecast section in API response for {destination.name}")

        hourly_data = data["hourly"]
        required_fields = ["time", "temperature_2m", "precipitation_probability", "precipitation", "wind_speed_10m"]
        missing_fields = [field for field in required_fields if field not in hourly_data]
        if missing_fields:
            raise WeatherIngestionError(
                f"API response missing required hourly fields for {destination.name}: {missing_fields}"
            )

        # Enrich with metadata
        retrieval_time = datetime.now(timezone.utc).isoformat()
        enriched_response = {
            "metadata": {
                "destination_name": destination.name,
                "latitude": destination.latitude,
                "longitude": destination.longitude,
                "retrieved_at_utc": retrieval_time,
                "source_api": self.base_url
            },
            "raw_response": data
        }
        return enriched_response

    def save_raw_response(
        self,
        enriched_data: Dict[str, Any],
        output_dir: Optional[str] = None
    ) -> Path:
        """Saves enriched raw weather payload to data/raw/ directory as JSON."""
        if output_dir is None:
            # Default to project data/raw directory
            base_path = Path(__file__).resolve().parents[2]
            output_dir_path = base_path / "data" / "raw"
        else:
            output_dir_path = Path(output_dir)

        output_dir_path.mkdir(parents=True, exist_ok=True)

        dest_name = enriched_data["metadata"]["destination_name"].lower().replace(" ", "_")
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"weather_{dest_name}_{timestamp_str}.json"
        filepath = output_dir_path / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(enriched_data, f, indent=2)
            logger.info(f"Saved raw weather forecast to {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Failed to write weather JSON file to {filepath}: {e}")
            raise WeatherIngestionError(f"File write error: {e}") from e

def ingest_destination_weather(destination_name: str, output_dir: Optional[str] = None) -> Path:
    """Helper function to fetch and save weather for a destination by name."""
    destination = get_destination(destination_name)
    client = OpenMeteoClient()
    enriched_data = client.fetch_hourly_forecast(destination)
    return client.save_raw_response(enriched_data, output_dir=output_dir)
