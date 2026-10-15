import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class TourismIngestionError(Exception):
    """Custom exception raised for tourism ingestion failures."""
    pass

class TourismDataIngestion:
    """Ingests and validates raw Ministry of Tourism CSV datasets."""

    def __init__(self, filepath: Optional[str] = None):
        if filepath is None:
            base_dir = Path(__file__).resolve().parents[2]
            self.filepath = base_dir / "data" / "raw" / "tourism" / "india_tourism_statewise_2018_2022.csv"
        else:
            self.filepath = Path(filepath)

    def load_raw_dataset(self) -> pd.DataFrame:
        """
        Loads the raw CSV dataset into a pandas DataFrame without modifying records.
        """
        if not self.filepath.exists():
            raise TourismIngestionError(f"Tourism dataset file not found at: {self.filepath}")

        try:
            df = pd.read_csv(self.filepath)
            logger.info(f"Loaded raw tourism dataset with shape {df.shape} from {self.filepath}")
            return df
        except Exception as e:
            logger.error(f"Error reading tourism CSV file at {self.filepath}: {e}")
            raise TourismIngestionError(f"Failed to load CSV: {e}") from e

    def inspect_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyses the dataset and returns data quality metrics:
        - Total row count & column count
        - Missing values per column
        - Duplicate row count
        - Data types per column
        """
        missing_values = df.isnull().sum().to_dict()
        duplicate_rows = int(df.duplicated().sum())
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

        report = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "missing_values": missing_values,
            "duplicate_rows": duplicate_rows,
            "column_dtypes": dtypes
        }
        return report

def load_and_inspect_tourism_data(filepath: Optional[str] = None) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Helper function to load raw dataset and report quality stats."""
    ingestor = TourismDataIngestion(filepath=filepath)
    df = ingestor.load_raw_dataset()
    quality_report = ingestor.inspect_data_quality(df)
    return df, quality_report
