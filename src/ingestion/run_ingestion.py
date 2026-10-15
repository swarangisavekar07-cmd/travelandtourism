import argparse
import logging
from src.ingestion.weather_client import ingest_destination_weather, DESTINATIONS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    parser = argparse.ArgumentParser(description="TravelWise Weather Ingestion CLI")
    parser.add_argument(
        "--destination",
        type=str,
        choices=list(DESTINATIONS.keys()) + ["all"],
        default="all",
        help="Destination name to fetch weather for (default: all)"
    )
    args = parser.parse_args()

    if args.destination == "all":
        targets = list(DESTINATIONS.keys())
    else:
        targets = [args.destination]

    for dest in targets:
        print(f"Fetching live weather forecast for {dest.capitalize()}...")
        try:
            filepath = ingest_destination_weather(dest)
            print(f"[SUCCESS] Successfully ingested weather data saved to: {filepath}\n")
        except Exception as e:
            print(f"[ERROR] Failed to ingest weather for {dest}: {e}\n")

if __name__ == "__main__":
    main()
