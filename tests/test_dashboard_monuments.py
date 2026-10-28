import pytest
import pandas as pd
from app.data_loader import (
    load_monuments_from_sql,
    load_monuments_data,
    get_monument_kpis,
    get_top_monuments,
    get_circle_footfall_summary,
    get_monument_comparison,
)

def test_load_monuments_from_sql():
    df, engine_name = load_monuments_from_sql()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) == 290
    assert "monument_name" in df.columns
    assert "financial_year" in df.columns
    assert "total_visitors" in df.columns

def test_load_monuments_data_parquet():
    df = load_monuments_data()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 290
    assert "circle" in df.columns
    assert "domestic_visitors" in df.columns

def test_get_monument_kpis():
    df = load_monuments_data()
    # Test for FY 2023-24
    kpis_23 = get_monument_kpis(df, financial_year="2023-24")
    assert kpis_23["monuments_count"] == 145
    assert kpis_23["circles_count"] == 33
    assert kpis_23["domestic_visitors"] == 53090007
    assert kpis_23["foreign_visitors"] == 2314641
    assert kpis_23["total_visitors"] == 55404648
    assert kpis_23["top_monument_name"] == "Taj Mahal"
    assert kpis_23["foreign_share_pct"] > 0

    # Test for Cumulative (All Years)
    kpis_all = get_monument_kpis(df, financial_year="All Years")
    assert kpis_all["total_visitors"] == 104751032

def test_get_monument_kpis_empty_df():
    empty_df = pd.DataFrame()
    kpis = get_monument_kpis(empty_df)
    assert kpis["total_visitors"] == 0
    assert kpis["monuments_count"] == 0
    assert kpis["top_monument_name"] == "N/A"

def test_get_top_monuments():
    df = load_monuments_data()
    top10 = get_top_monuments(df, financial_year="2023-24", top_n=10)
    assert len(top10) == 10
    assert top10.iloc[0]["monument_name"] == "Taj Mahal"
    assert list(top10["rank"]) == list(range(1, 11))

    # Test filtering by circle
    delhi_top = get_top_monuments(df, financial_year="2023-24", circle="Delhi", top_n=5)
    assert len(delhi_top) > 0
    assert all(delhi_top["circle"] == "Delhi")

def test_get_circle_footfall_summary():
    df = load_monuments_data()
    summary = get_circle_footfall_summary(df, financial_year="2023-24")
    assert not summary.empty
    assert len(summary) == 33  # 33 circles
    assert "total_visitors" in summary.columns
    assert "foreign_share_pct" in summary.columns
    # Agra circle should be #1
    assert summary.iloc[0]["circle"] == "Agra"

def test_get_monument_comparison():
    df = load_monuments_data()
    taj_info = get_monument_comparison(df, "Taj Mahal")
    assert taj_info["monument_name"] == "Taj Mahal"
    assert taj_info["circle"] == "Agra"
    assert len(taj_info["records"]) == 2  # FY 2022-23 and FY 2023-24

    missing_info = get_monument_comparison(df, "Non Existent Site")
    assert missing_info == {}
