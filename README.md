# TravelWise - Tourism and Weather Analytics Platform

TravelWise is a Data Engineering and Tourism Analytics platform designed to help travelers and tourism analysts evaluate travel destinations and optimize travel schedules. It integrates historical state-wise India Tourism statistics with live weather forecasts from the Open-Meteo API, processed through data engineering pipelines and presented in an interactive Streamlit executive dashboard.

---

## Technologies Used

- **Python 3.10+**: Core programming language.
- **Streamlit**: Interactive analytics dashboard and user interface.
- **Plotly Express & Graph Objects**: Interactive charts, multi-metric time series, and heatmaps.
- **Pandas & PyArrow**: High-performance data manipulation and Parquet columnar storage.
- **PySpark**: Scalable ETL transformations, data validation, and aggregations.
- **PostgreSQL & SQLAlchemy / psycopg2**: Relational database storage for analytics metrics.
- **Open-Meteo API (`requests` / `httpx`)**: Real-time weather forecasting and climate data ingestion.
- **pytest & pytest-cov**: Automated testing and validation suite.

---

## Project Structure

```text
TravelWise/
|-- app/                      # Streamlit dashboard application
|   |-- components/           # UI components (KPI cards, charts, tabs)
|   |-- data_loader.py        # Cached data access & filtering helpers
|   `-- main.py               # Streamlit application entry point
|-- src/                      # Backend & data engineering modules
|   |-- ingestion/            # Weather API client & tourism data ingestion
|   |-- pipeline/             # PySpark ETL transformations & data validation
|   |-- analytics/            # Travel suitability scoring & tourism analytics
|   `-- database/             # PostgreSQL connection logic & schema setup
|-- data/                     # Data storage (Curated datasets & raw CSVs)
|   |-- raw/                  # Source datasets (India Tourism CSVs & metadata)
|   `-- processed/            # Curated Parquet files for fast dashboard loading
|-- tests/                    # Unit and integration test suite
|-- .streamlit/               # Streamlit theme configuration (Dark Mode)
|-- .env.example              # Template for environment variables (safe for Git)
|-- .gitignore                # Git ignore rules for credentials, venv, and large files
|-- requirements.txt          # Python dependencies
`-- README.md                 # Project documentation
```

---

## How to Run the Streamlit Dashboard

Follow these steps to run the dashboard on Windows:

### 1. Open Terminal & Navigate to Project Directory
```powershell
cd "D:\Travel and tourism"
```

### 2. Activate the Virtual Environment
If you already have the virtual environment created:
```powershell
.\venv\Scripts\Activate.ps1
```
*(If you need to create a new one: `python -m venv venv` and install requirements: `pip install -r requirements.txt`)*

### 3. Configure Environment Variables (Optional)
Copy the template file to `.env`:
```powershell
copy .env.example .env
```
*(The dashboard is configured to read directly from curated Parquet data, so you can preview the dashboard immediately even without an active PostgreSQL instance).*

### 4. Launch the Streamlit Dashboard
```powershell
streamlit run app/main.py
```

Once started, Streamlit will open automatically in your browser at:
`http://localhost:8501`

---

## Dashboard Features

- **Executive Overview**: High-level KPI summary cards (Total Domestic & Foreign Tourist Visits, Year-over-Year Growth, Average Destination Temperatures).
- **Tourism Analytics**: State-wise tourist trends, top visiting states, and historical growth patterns (2018-2022).
- **Weather Explorer**: 7-day live weather forecast curves, precipitation probabilities, and travel suitability scores for top travel destinations.
- **Data Quality & Pipeline Health**: Completeness, null-rate checks, and schema validation metrics for raw and processed datasets.

---

## Running Tests

To run the automated test suite:
```powershell
pytest tests/
```