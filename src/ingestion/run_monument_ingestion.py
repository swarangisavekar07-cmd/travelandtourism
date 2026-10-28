import logging
from src.ingestion.monument_client import MonumentDataIngestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    print("Ingesting raw official ASI Centrally Protected Ticketed Monuments dataset...")
    ingestor = MonumentDataIngestion()
    records = ingestor.load_raw_dataset()
    report = ingestor.inspect_data_quality(records)

    print("\n--- Monument Dataset Quality Report ---")
    print(f"Total Records:           {report['total_records']}")
    print(f"Distinct Monuments:      {report['distinct_monuments']}")
    print(f"Distinct Circles:        {report['distinct_circles']}")
    print(f"Distinct States/Regions: {report['distinct_states']}")
    print(f"Financial Years:         {report['financial_years']}")
    print(f"Duplicate Natural Keys:  {report['duplicate_natural_keys']}")
    print(f"Missing Values:          {report['missing_values']}")
    print("\nSample Data (First record):")
    print(records[0])

if __name__ == "__main__":
    main()
