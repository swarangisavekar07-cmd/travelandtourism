import argparse
import logging
import sys
from pathlib import Path

from src.pipeline.spark_session import get_spark_session
from src.pipeline.tourism_pipeline import run_tourism_pipeline
from src.pipeline.weather_pipeline import run_weather_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TravelWise-Pipeline-CLI")

def main():
    parser = argparse.ArgumentParser(description="TravelWise PySpark ETL Pipeline Runner")
    parser.add_argument(
        "--pipeline",
        choices=["tourism", "weather", "all"],
        default="all",
        help="Pipeline to execute (default: all)"
    )
    args = parser.parse_args()

    spark = get_spark_session("TravelWise-Unified-Pipeline")
    try:
        if args.pipeline in ["tourism", "all"]:
            logger.info(">>> Starting Tourism ETL Pipeline...")
            curated_tourism_df, tourism_report = run_tourism_pipeline(spark=spark)
            print("\n================ TOURISM ETL REPORT ================")
            print(f"Input File:        {tourism_report['input_csv']}")
            print(f"Input Raw Rows:    {tourism_report['input_rows']}")
            print(f"Curated Rows:      {tourism_report['output_rows']}")
            print(f"Distinct Entities: {tourism_report['distinct_states']}")
            print(f"Aggregate Rows:    {tourism_report['aggregate_records']}")
            print(f"Estimated Records: {tourism_report['estimated_records']}")
            print(f"Null Visits:       {tourism_report['null_visit_counts']}")
            print(f"Duplicates:        {tourism_report['duplicate_records']}")
            print(f"Output Directory:  {tourism_report['output_dir']}")
            print("===================================================\n")

        if args.pipeline in ["weather", "all"]:
            logger.info(">>> Starting Weather ETL Pipeline...")
            daily_weather_df, weather_report = run_weather_pipeline(spark=spark)
            print("\n================ WEATHER ETL REPORT ================")
            print(f"Raw Files Read:    {weather_report['raw_json_files_found']}")
            print(f"Hourly Records:    {weather_report['hourly_records_parsed']}")
            print(f"Daily Aggregates:  {weather_report['total_daily_forecast_records']}")
            print(f"Destinations:      {', '.join(weather_report['destinations_covered'])}")
            print(f"Null Temperature:  {weather_report['null_temperature_records']}")
            print(f"Output Directory:  {weather_report['output_dir']}")
            print("====================================================\n")

        logger.info("Pipeline execution completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
