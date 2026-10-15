# Tourism ETL Pipeline Quality Report

- **Input File**: `D:\Travel and tourism\data\raw\tourism\india_tourism_statewise_2018_2022.csv`
- **Input Raw Rows**: 74
- **Output Curated Rows**: 370
- **Distinct Entities**: 37 (28 States + 8 UTs + 1 Total India)
- **Output Parquet**: `D:\Travel and tourism\data\processed\tourism\india_tourism_statewise_normalized.parquet`
- **Duplicate Records**: 0
- **Negative Value Records**: 0
- **Null Visit Counts**: 2 (Expected: Ladakh 2018 Domestic & Foreign only)
- **Null YoY Growth Records**: 76 (All 2018 records + Ladakh 2019)
- **Official Aggregate Records (Total India)**: 10
- **Estimated Records (Maharashtra & Delhi 2022)**: 4
