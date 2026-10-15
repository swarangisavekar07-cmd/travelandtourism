import pytest
import pandas as pd
from pathlib import Path
from src.ingestion.tourism_client import TourismDataIngestion, TourismIngestionError

@pytest.fixture
def synthetic_tourism_csv(tmp_path):
    """
    Synthetic fixture for unit testing ingestion and quality reporting logic.
    Clearly labeled: SYNTHETIC DATA FOR TESTING ONLY.
    """
    csv_content = (
        "State/UT,Category,2018,2019,2020\n"
        "StateA,Domestic,1000,1200,800\n"
        "StateA,Foreign,100,150,50\n"
        "StateB,Domestic,2000,2100,1900\n"
        "StateB,Domestic,2000,2100,1900\n"  # Intentional duplicate
        "StateC,Domestic,3000,,2500\n"        # Intentional missing value
    )
    file_path = tmp_path / "synthetic_tourism_test.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    return file_path

def test_tourism_ingestion_synthetic_data(synthetic_tourism_csv):
    ingestor = TourismDataIngestion(filepath=str(synthetic_tourism_csv))
    df = ingestor.load_raw_dataset()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert list(df.columns) == ["State/UT", "Category", "2018", "2019", "2020"]

    report = ingestor.inspect_data_quality(df)
    assert report["total_rows"] == 5
    assert report["total_columns"] == 5
    assert report["duplicate_rows"] == 1
    assert report["missing_values"]["2019"] == 1

def test_tourism_ingestion_file_not_found(tmp_path):
    non_existent = tmp_path / "missing.csv"
    ingestor = TourismDataIngestion(filepath=str(non_existent))

    with pytest.raises(TourismIngestionError, match="Tourism dataset file not found"):
        ingestor.load_raw_dataset()

def test_real_raw_tourism_dataset_ingestion():
    """Verify that the official stored raw dataset loads successfully and passes schema check."""
    ingestor = TourismDataIngestion()
    df = ingestor.load_raw_dataset()

    assert not df.empty
    assert "State/UT" in df.columns
    assert "Category" in df.columns
    assert "2018" in df.columns
    assert "2022" in df.columns

    report = ingestor.inspect_data_quality(df)
    assert report["total_rows"] > 0
    assert report["duplicate_rows"] == 0
