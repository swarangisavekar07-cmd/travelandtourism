# Metadata: India Tourism State/UT-wise Statistics (2018–2022)

## 📌 Dataset Overview
- **File Name**: `india_tourism_statewise_2018_2022.csv`
- **Location**: `data/raw/tourism/india_tourism_statewise_2018_2022.csv`
- **Backup File**: `data/raw/tourism/india_tourism_statewise_2018_2022.csv.bak`
- **Temporal Coverage**: 2018 – 2022 (5 calendar years)
- **Geographic Coverage**: **All 36 Indian Administrative Entities** (28 States + 8 Union Territories) plus `Total India` (37 entities total)
- **Dimensions**:
  - `State/UT`: Name of the State or Union Territory, or `Total India`
  - `Category`: `Domestic` or `Foreign` tourist visits
  - `2018`, `2019`, `2020`, `2021`, `2022`: Annual visit counts

---

## 🏛️ Official Primary Sources & Publication Lineage

All figures are extracted directly from official publications compiled by the **Market Research Division (MRD), Ministry of Tourism, Government of India**:

1. **Tourism Statistics for year 2019**:
   - **Source Portal**: [data.tourism.gov.in/rawdata](https://data.tourism.gov.in/rawdata)
   - **Document**: `Tourism Statistics for year 2019_0.doc`
   - **Table**: **Table 5.1.2** — *State/UTs wise Domestic and Foreign Tourist Visits, 2018-19*
   - **Units**: Integer visitor count

2. **Tourism Statistics for year 2020**:
   - **Source Portal**: [data.tourism.gov.in/rawdata](https://data.tourism.gov.in/rawdata)
   - **Document**: `Tourism Statistics for year 2020.doc`
   - **Table**: **Table 5.1.2** — *State/UTs wise Domestic and Foreign Tourist Visits, 2019-20*
   - **Units**: Integer visitor count

3. **Tourism Statistics for year 2021**:
   - **Source Portal**: [data.tourism.gov.in/rawdata](https://data.tourism.gov.in/rawdata)
   - **Document**: `Tourism Statistics for year 2021.doc`
   - **Table**: **Table 5.1.2** — *State/UTs wise Domestic and Foreign Tourist Visits, 2020 & 2021*
   - **Units**: Integer visitor count

4. **India Tourism Statistics 2023**:
   - **Source Portal**: [data.tourism.gov.in/tourismdata](https://data.tourism.gov.in/tourismdata)
   - **Document Download URL**: `https://data.tourism.gov.in/mrd/Uploads/tourism_data/India%20Tourism%20Statistics%202023-English%20(1).pdf`
   - **Local Archive**: `data/raw/tourism/India_Tourism_Statistics_2023.pdf`
   - **Table**: **Table 5.1.2** — *State/UT-wise Domestic and Foreign Tourist Visits, 2021 & 2022* (Pages 144–145 / Printed pages 131–132)
   - **Units**: In Lakhs (1 Lakh = 100,000 visits)

5. **India Tourism Data Compendium 2024**:
   - **Source Portal**: [data.tourism.gov.in/tourismdata](https://data.tourism.gov.in/tourismdata)
   - **Document Download URL**: `https://data.tourism.gov.in/mrd/Uploads/tourism_data/India%20Tourism%20Data%20Compendium%202024.pdf`
   - **Local Archive**: `data/raw/tourism/India_Tourism_Data_Compendium_2024.pdf`
   - **Table**: **Table 4.1.2** — *State/UT-wise Domestic and Foreign Tourist Visits, 2022 & 2023* (Pages 139–140 / Printed pages 121–122)
   - **Units**: In Millions (1 Million = 1,000,000 visits)

---

## 🗺️ Administrative & Historical Boundary Notes

1. **Ladakh**:
   - Formed as an independent Union Territory on 31 October 2019 under the *Jammu and Kashmir Reorganisation Act, 2019*.
   - In 2018, Ladakh was not a separate reporting entity; its numbers were recorded under the undivided State of Jammu and Kashmir.
   - Per requirements, 2018 for Ladakh is left strictly as an **unavailable entry (empty / null)**, not zero or fabricated.

2. **Dadra and Nagar Haveli and Daman and Diu**:
   - The two Union Territories were merged into a single administrative entity on 26 January 2020 (*The Dadra and Nagar Haveli and Daman and Diu (Merger of Union Territories) Act, 2019*).
   - In the compiled dataset, the standardized canonical entity `Dadra and Nagar Haveli and Daman and Diu` is used, summing the two historical constituent returns for 2018–2021 to ensure seamless time-series continuity.

3. **Official Estimations by Ministry**:
   - In the official Ministry report for 2022 (Table 5.1.2 and Table 4.1.2), figures for **Maharashtra** (DTV: 111,297,600, FTV: 1,511,600) and **Delhi** (DTV: 27,186,200, FTV: 815,700) were estimated by the Ministry of Tourism by applying the All-India 2022/2019 growth rate to their 2019 base data due to late return submissions by those State/UT departments.

---

## 📊 Dataset Quality Summary

- **Total Rows**: 74 (37 entities × 2 categories: Domestic & Foreign)
- **Total Columns**: 7 (`State/UT`, `Category`, `2018`, `2019`, `2020`, `2021`, `2022`)
- **Missing Values**:
  - `2018`: Exactly 2 missing values (Domestic and Foreign for Ladakh, representing the genuine administrative reality prior to UT formation).
  - `2019` to `2022`: 0 missing values across all columns.
- **Duplicate Rows**: 0
