import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

EXPECTED_MONUMENT_FIELDS = [
    "monument_name",
    "circle",
    "state_or_region",
    "financial_year",
    "domestic_visitors",
    "foreign_visitors",
    "total_visitors",
    "source",
]

class MonumentIngestionError(Exception):
    """Custom exception raised for monument data ingestion failures."""
    pass

class MonumentDataIngestion:
    """Ingests and validates raw ASI monument visitor JSON datasets."""

    def __init__(self, filepath: Optional[str] = None):
        if filepath is None:
            base_dir = Path(__file__).resolve().parents[2]
            self.filepath = base_dir / "data" / "raw" / "monuments" / "asi_monument_visitors.json"
        else:
            self.filepath = Path(filepath)

    def load_raw_dataset(self) -> List[Dict[str, Any]]:
        """
        Loads raw JSON monument records without mutating fields.
        """
        if not self.filepath.exists():
            raise MonumentIngestionError(f"Monument JSON dataset file not found at: {self.filepath}")

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list) or len(data) == 0:
                raise MonumentIngestionError("Monument JSON file must contain a non-empty array of records.")

            logger.info(f"Loaded {len(data)} raw monument records from {self.filepath}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON structure in {self.filepath}: {e}")
            raise MonumentIngestionError(f"Corrupted or invalid JSON dataset: {e}") from e
        except Exception as e:
            logger.error(f"Error reading monument JSON at {self.filepath}: {e}")
            raise MonumentIngestionError(f"Failed to load monument dataset: {e}") from e

    def inspect_data_quality(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates structure and computes quality metrics for ingested raw records:
        - Total record count
        - Required field presence
        - Unique monuments and administrative circles
        - Null counts across fields
        - Duplicate natural key check (monument_name, financial_year)
        """
        if not records:
            return {"total_records": 0, "status": "EMPTY"}

        df = pd.DataFrame(records)
        missing_fields = [f for f in EXPECTED_MONUMENT_FIELDS if f not in df.columns]
        if missing_fields:
            raise MonumentIngestionError(f"Missing required fields in monument JSON: {missing_fields}")

        # Check natural key duplicates
        dupes = int(df.duplicated(subset=["monument_name", "financial_year"]).sum())
        missing_values = df.isnull().sum().to_dict()

        report = {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "distinct_monuments": int(df["monument_name"].nunique()),
            "distinct_circles": int(df["circle"].nunique()),
            "distinct_states": int(df["state_or_region"].nunique()),
            "financial_years": sorted(df["financial_year"].unique().tolist()),
            "duplicate_natural_keys": dupes,
            "missing_values": missing_values,
        }
        return report

def load_and_inspect_monument_data(filepath: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Helper function to load raw dataset and report quality statistics."""
    ingestor = MonumentDataIngestion(filepath=filepath)
    records = ingestor.load_raw_dataset()
    quality_report = ingestor.inspect_data_quality(records)
    return records, quality_report
