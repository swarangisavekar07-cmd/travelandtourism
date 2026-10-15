import json
import pytest
import requests
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingestion.destinations import DESTINATIONS, get_destination
from src.ingestion.weather_client import OpenMeteoClient, WeatherIngestionError, ingest_destination_weather

@pytest.fixture
def mock_open_meteo_response():
    return {
        "latitude": 18.75,
        "longitude": 73.41,
        "timezone": "Asia/Kolkata",
        "hourly": {
            "time": ["2026-10-10T00:00", "2026-10-10T01:00"],
            "temperature_2m": [22.4, 21.8],
            "precipitation_probability": [10, 5],
            "precipitation": [0.0, 0.0],
            "wind_speed_10m": [8.5, 7.2]
        }
    }

def test_supported_destinations():
    assert "lonavala" in DESTINATIONS
    assert "mahabaleshwar" in DESTINATIONS
    assert "matheran" in DESTINATIONS

    lonavala = get_destination("Lonavala")
    assert lonavala.latitude == 18.7557
    assert lonavala.longitude == 73.4091

def test_invalid_destination():
    with pytest.raises(ValueError, match="Unknown destination"):
        get_destination("NonExistentCity")

@patch("requests.get")
def test_fetch_hourly_forecast_success(mock_get, mock_open_meteo_response):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = mock_open_meteo_response
    mock_get.return_value = mock_resp

    client = OpenMeteoClient()
    dest = get_destination("Lonavala")
    result = client.fetch_hourly_forecast(dest)

    assert "metadata" in result
    assert result["metadata"]["destination_name"] == "Lonavala"
    assert "retrieved_at_utc" in result["metadata"]
    assert "hourly" in result["raw_response"]
    assert len(result["raw_response"]["hourly"]["temperature_2m"]) == 2

@patch("requests.get")
def test_fetch_hourly_forecast_http_error(mock_get):
    mock_get.side_effect = requests.RequestException("Network timeout")

    client = OpenMeteoClient()
    dest = get_destination("Mahabaleshwar")

    with pytest.raises(WeatherIngestionError, match="Failed to retrieve weather data"):
        client.fetch_hourly_forecast(dest)

@patch("requests.get")
def test_fetch_hourly_forecast_missing_fields(mock_get):
    incomplete_response = {
        "latitude": 17.92,
        "hourly": {
            "time": ["2026-10-10T00:00"],
            "temperature_2m": [20.0]
            # missing precipitation, precipitation_probability, wind_speed_10m
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = incomplete_response
    mock_get.return_value = mock_resp

    client = OpenMeteoClient()
    dest = get_destination("Mahabaleshwar")

    with pytest.raises(WeatherIngestionError, match="API response missing required hourly fields"):
        client.fetch_hourly_forecast(dest)

def test_save_raw_response(tmp_path, mock_open_meteo_response):
    client = OpenMeteoClient()
    enriched_data = {
        "metadata": {
            "destination_name": "Matheran",
            "latitude": 18.9867,
            "longitude": 73.2679,
            "retrieved_at_utc": "2026-10-10T12:00:00Z",
            "source_api": "https://api.open-meteo.com/v1/forecast"
        },
        "raw_response": mock_open_meteo_response
    }

    saved_file = client.save_raw_response(enriched_data, output_dir=str(tmp_path))
    assert saved_file.exists()

    with open(saved_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    assert content["metadata"]["destination_name"] == "Matheran"
    assert content["raw_response"]["hourly"]["temperature_2m"] == [22.4, 21.8]
