# ASI Monument ETL Pipeline Quality Report

- **Input File**: `D:\Travel and tourism\data\raw\monuments\asi_monument_visitors.json`
- **Input Raw Rows**: 290
- **Output Curated Rows**: 290
- **Distinct Ticketed Monuments**: 145
- **Distinct ASI Circles**: 33
- **Distinct States/Regions**: 21
- **Financial Years Analyzed**: 2022-23, 2023-24
- **Output Parquet**: `D:\Travel and tourism\data\processed\monuments\asi_monument_visitors_normalized.parquet`
- **Duplicate Records**: 0
- **Negative Value Records**: 0
- **Null Domestic Counts**: 2 (Preserved historical nulls: Fort St. George 2022-23, Mattancherry 2023-24)
- **Null Foreign Counts**: 2
- **Null Total Footfall Counts**: 2
- **Null YoY Growth Records**: 148 (Base FY 2022-23 records + unrecorded prior period)

## Official Reconciled Totals
- **FY 2022-23 Footfall**: Domestic = 47,901,021, Foreign = 1,445,363, Total = 49,346,384
- **FY 2023-24 Footfall**: Domestic = 53,090,007, Foreign = 2,314,641, Total = 55,404,648
