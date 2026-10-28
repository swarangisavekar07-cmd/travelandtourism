# Metadata: Centrally Protected Ticketed ASI Monuments Visitor Statistics

## Provenance & Attribution

- **Source Authority**: Ministry of Tourism, Government of India & Archaeological Survey of India (ASI)
- **Primary Publication**: *India Tourism Data Compendium 2024*, Chapter 4 (*Domestic Tourism*)
- **Specific Table**: Table 4.2.3: *Number of Visitors to Centrally Protected Ticketed Monuments, 2022-23 & 2023-24* (pp. 127–135)
- **Archive File**: [`data/raw/tourism/India_Tourism_Data_Compendium_2024.pdf`](../tourism/India_Tourism_Data_Compendium_2024.pdf)
- **Derived JSON File**: [`data/raw/monuments/asi_monument_visitors.json`](asi_monument_visitors.json)
- **Reporting Period**: Financial Years 2022-23 (1 April 2022 – 31 March 2023) and 2023-24 (1 April 2023 – 31 March 2024)
- **Retrieval & Conversion Date**: 2026-10-28

---

## Dataset Schema

| Field Name | Type | Nullable | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `serial_number` | Integer | No | Original official sequential index (1 to 145) | `1` |
| `monument_name` | String | No | Official centrally protected ticketed monument name | `Taj Mahal` |
| `circle` | String | No | ASI Archaeological Circle jurisdiction | `Agra` |
| `state_or_region` | String | No | Mapped Indian State or Union Territory | `Uttar Pradesh` |
| `financial_year` | String | No | Financial Year reporting period | `2023-24` |
| `domestic_visitors` | BigInteger | Yes | Annual domestic ticketed visitor footfall | `6098876` |
| `foreign_visitors` | BigInteger | Yes | Annual foreign ticketed visitor footfall | `681339` |
| `total_visitors` | BigInteger | Yes | Combined annual ticketed footfall | `6780215` |
| `source` | String | No | Full provenance and citation | `Ministry of Tourism, Government of India...` |

---

## Official Grand Total Reconciliation

| Financial Year | Category | Official Target | Extracted JSON Sum | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FY 2022-23** | Domestic Visitors | 47,901,021 | 47,901,021 | Exact Match (0 diff) |
| **FY 2022-23** | Foreign Visitors | 1,445,363 | 1,445,363 | Exact Match (0 diff) |
| **FY 2022-23** | Total Visitors | 49,346,384 | 49,346,384 | Exact Match (0 diff) |
| **FY 2023-24** | Domestic Visitors | 53,090,007 | 53,090,007 | Exact Match (0 diff) |
| **FY 2023-24** | Foreign Visitors | 2,314,641 | 2,314,641 | Exact Match (0 diff) |
| **FY 2023-24** | Total Visitors | 55,404,648 | 55,404,648 | Exact Match (0 diff) |

---

## Known Scope & Limitations

1. **Centrally Protected Monuments Only**: Only covers monuments ticketed and administered by the Archaeological Survey of India (145 ticketed sites). Does not include non-ticketed national monuments or state-protected heritage sites.
2. **Financial Year Reporting**: Data is compiled on Indian fiscal year cycles (April 1 to March 31) rather than calendar years.
3. **Genuine Null Values**: Monuments with temporary closures or transition to ticketless entry contain legitimate nulls (e.g., Mattancherry Palace Museum in Kochi was closed/ticketless in 2023-24; Fort St. George in Chennai was newly ticketed in 2023-24). Legitimate nulls are preserved as `null` rather than converted to `0`.
