import logging
from src.ingestion.tourism_client import TourismDataIngestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    print("Ingesting raw official India Tourism Statistics dataset...")
    ingestor = TourismDataIngestion()
    df = ingestor.load_raw_dataset()
    report = ingestor.inspect_data_quality(df)

    print("\n--- Tourism Dataset Quality Report ---")
    print(f"Total Rows: {report['total_rows']}")
    print(f"Total Columns: {report['total_columns']}")
    print(f"Columns: {report['columns']}")
    print(f"Duplicate Rows: {report['duplicate_rows']}")
    print(f"Missing Values per Column: {report['missing_values']}")
    print(f"Column Data Types: {report['column_dtypes']}")
    print("\nSample Data (First 5 records):")
    print(df.head(5))

if __name__ == "__main__":
    main()
