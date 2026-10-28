import argparse
import logging
import sys
from pathlib import Path

from src.pipeline.spark_session import get_spark_session
from src.pipeline.tourism_pipeline import run_tourism_pipeline
from src.pipeline.weather_pipeline import run_weather_pipeline
from src.pipeline.monument_pipeline import run_monument_pipeline
from src.database.loader import (
    create_all_tables,
    load_curated_tourism_to_db,
    load_curated_weather_to_db,
    load_curated_monuments_to_db,
    get_engine,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TravelWise-Pipeline-CLI")

def main():
    parser = argparse.ArgumentParser(description="TravelWise PySpark ETL Pipeline Runner")
    parser.add_argument(
        "--pipeline",
        choices=["tourism", "weather", "monuments", "all"],
        default="all",
        help="Pipeline to execute (default: all)"
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Also load curated outputs into database with idempotent upsert"
    )
    args = parser.parse_args()

    spark = get_spark_session("TravelWise-Unified-Pipeline")
    results = {}

    try:
        if args.pipeline in ["tourism", "all"]:
            logger.info(">>> Starting Tourism ETL Pipeline (CSV Ingestion & Windowing)...")
            curated_tourism_df, tourism_report = run_tourism_pipeline(spark=spark)
            results["tourism"] = tourism_report
            print("\n================ TOURISM ETL REPORT ================")
            print(f"Dataset:           State-wise Annual Tourism (Ministry of Tourism)")
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
            logger.info(">>> Starting Weather ETL Pipeline (Live Feed Aggregation)...")
            daily_weather_df, weather_report = run_weather_pipeline(spark=spark)
            results["weather"] = weather_report
            print("\n================ WEATHER ETL REPORT ================")
            print(f"Dataset:           Open-Meteo Hourly Destinations Forecast")
            print(f"Raw Files Read:    {weather_report['raw_json_files_found']}")
            print(f"Hourly Records:    {weather_report['hourly_records_parsed']}")
            print(f"Daily Aggregates:  {weather_report['total_daily_forecast_records']}")
            print(f"Destinations:      {', '.join(weather_report['destinations_covered'])}")
            print(f"Null Temperature:  {weather_report['null_temperature_records']}")
            print(f"Output Directory:  {weather_report['output_dir']}")
            print("====================================================\n")

        if args.pipeline in ["monuments", "all"]:
            logger.info(">>> Starting Monument ETL Pipeline (ASI Centrally Protected Ticketed Monuments)...")
            curated_monument_df, monument_report = run_monument_pipeline(spark=spark)
            results["monuments"] = monument_report
            print("\n================ ASI MONUMENT ETL REPORT ================")
            print(f"Dataset:           ASI Centrally Protected Ticketed Monuments (Ministry of Tourism)")
            print(f"Input File:        {monument_report['input_json']}")
            print(f"Input Raw Rows:    {monument_report['input_rows']}")
            print(f"Curated Rows:      {monument_report['output_rows']}")
            print(f"Distinct Sites:    {monument_report['distinct_monuments']}")
            print(f"Distinct Circles:  {monument_report['distinct_circles']}")
            print(f"Distinct States:   {monument_report['distinct_states']}")
            print(f"Financial Years:   {', '.join(monument_report['financial_years'])}")
            print(f"Duplicate Keys:    {monument_report['duplicate_records']}")
            print(f"Negative Records:  {monument_report['negative_records']}")
            print(f"Null Domestic:     {monument_report['null_domestic_records']}")
            print(f"Null Foreign:      {monument_report['null_foreign_records']}")
            print(f"Null Footfall:     {monument_report['null_total_records']}")
            reconcil = monument_report.get('reconciliation', {})
            for fy, totals in reconcil.items():
                print(f"FY {fy} Totals:   Domestic={totals.get('domestic_visitors', 0):,}, Foreign={totals.get('foreign_visitors', 0):,}, Total={totals.get('total_visitors', 0):,}")
            print(f"Output Directory:  {monument_report['output_dir']}")
            print("=========================================================\n")

        if args.load_db:
            logger.info(">>> Loading curated outputs into database...")
            engine = get_engine()
            create_all_tables(engine)
            if "tourism" in results:
                t_loaded = load_curated_tourism_to_db(engine=engine)
                print(f"Database Load: Ingested {t_loaded} rows into tourism_statewise_annual")
            if "weather" in results:
                w_loaded = load_curated_weather_to_db(engine=engine)
                print(f"Database Load: Ingested {w_loaded} rows into weather_daily_forecast")
            if "monuments" in results:
                m_loaded = load_curated_monuments_to_db(engine=engine)
                print(f"Database Load: Ingested {m_loaded} rows into asi_monument_visitors")

        logger.info("Pipeline execution completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
