import json
import pytest
from pathlib import Path
from src.ingestion.monument_client import (
    MonumentDataIngestion,
    MonumentIngestionError,
    load_and_inspect_monument_data,
)

@pytest.fixture
def synthetic_monument_json(tmp_path):
    """
    Synthetic fixture for unit testing ingestion and quality reporting logic.
    Clearly labeled: SYNTHETIC DATA FOR TESTING ONLY.
    """
    records = [
        {
            "serial_number": 1,
            "monument_name": "Monument Alpha",
            "circle": "Agra",
            "state_or_region": "Uttar Pradesh",
            "financial_year": "2022-23",
            "domestic_visitors": 100000,
            "foreign_visitors": 5000,
            "total_visitors": 105000,
            "source": "Synthetic Source",
        },
        {
            "serial_number": 1,
            "monument_name": "Monument Alpha",
            "circle": "Agra",
            "state_or_region": "Uttar Pradesh",
            "financial_year": "2023-24",
            "domestic_visitors": 120000,
            "foreign_visitors": 8000,
            "total_visitors": 128000,
            "source": "Synthetic Source",
        },
        {
            "serial_number": 2,
            "monument_name": "Monument Beta",
            "circle": "Delhi",
            "state_or_region": "Delhi",
            "financial_year": "2022-23",
            "domestic_visitors": None,  # Legitimate null
            "foreign_visitors": None,
            "total_visitors": None,
            "source": "Synthetic Source",
        },
        {
            "serial_number": 2,
            "monument_name": "Monument Beta",
            "circle": "Delhi",
            "state_or_region": "Delhi",
            "financial_year": "2023-24",
            "domestic_visitors": 50000,
            "foreign_visitors": 2000,
            "total_visitors": 52000,
            "source": "Synthetic Source",
        },
    ]
    file_path = tmp_path / "synthetic_monuments.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(records, f)
    return file_path

def test_monument_ingestion_synthetic_success(synthetic_monument_json):
    ingestor = MonumentDataIngestion(filepath=str(synthetic_monument_json))
    records = ingestor.load_raw_dataset()

    assert isinstance(records, list)
    assert len(records) == 4

    report = ingestor.inspect_data_quality(records)
    assert report["total_records"] == 4
    assert report["distinct_monuments"] == 2
    assert report["distinct_circles"] == 2
    assert report["duplicate_natural_keys"] == 0
    assert report["missing_values"]["domestic_visitors"] == 1

def test_monument_ingestion_file_not_found(tmp_path):
    missing_path = tmp_path / "non_existent_monuments.json"
    ingestor = MonumentDataIngestion(filepath=str(missing_path))

    with pytest.raises(MonumentIngestionError, match="Monument JSON dataset file not found"):
        ingestor.load_raw_dataset()

def test_monument_ingestion_invalid_json(tmp_path):
    bad_json = tmp_path / "corrupted.json"
    bad_json.write_text("{ this is not valid json }", encoding="utf-8")
    ingestor = MonumentDataIngestion(filepath=str(bad_json))

    with pytest.raises(MonumentIngestionError, match="Corrupted or invalid JSON dataset"):
        ingestor.load_raw_dataset()

def test_monument_ingestion_empty_array(tmp_path):
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]", encoding="utf-8")
    ingestor = MonumentDataIngestion(filepath=str(empty_json))

    with pytest.raises(MonumentIngestionError, match="non-empty array"):
        ingestor.load_raw_dataset()

def test_monument_ingestion_missing_required_fields(tmp_path):
    incomplete_json = tmp_path / "incomplete.json"
    records = [{"some_random_key": "val"}]
    with open(incomplete_json, "w", encoding="utf-8") as f:
        json.dump(records, f)

    ingestor = MonumentDataIngestion(filepath=str(incomplete_json))
    data = ingestor.load_raw_dataset()
    with pytest.raises(MonumentIngestionError, match="Missing required fields"):
        ingestor.inspect_data_quality(data)

def test_monument_ingestion_duplicate_natural_keys(tmp_path):
    dupe_json = tmp_path / "dupes.json"
    records = [
        {
            "monument_name": "Monument Alpha",
            "circle": "Agra",
            "state_or_region": "Uttar Pradesh",
            "financial_year": "2023-24",
            "domestic_visitors": 100,
            "foreign_visitors": 10,
            "total_visitors": 110,
            "source": "Source",
        },
        {
            "monument_name": "Monument Alpha",
            "circle": "Agra",
            "state_or_region": "Uttar Pradesh",
            "financial_year": "2023-24",  # Duplicate key!
            "domestic_visitors": 200,
            "foreign_visitors": 20,
            "total_visitors": 220,
            "source": "Source",
        },
    ]
    with open(dupe_json, "w", encoding="utf-8") as f:
        json.dump(records, f)

    ingestor = MonumentDataIngestion(filepath=str(dupe_json))
    data = ingestor.load_raw_dataset()
    report = ingestor.inspect_data_quality(data)
    assert report["duplicate_natural_keys"] == 1

def test_real_raw_monument_dataset_ingestion():
    """Verifies that the official stored raw ASI monument JSON dataset loads and passes all checks."""
    records, report = load_and_inspect_monument_data()

    assert len(records) == 290
    assert report["total_records"] == 290
    assert report["distinct_monuments"] == 145
    assert report["distinct_circles"] == 33
    assert report["duplicate_natural_keys"] == 0
    assert report["financial_years"] == ["2022-23", "2023-24"]
