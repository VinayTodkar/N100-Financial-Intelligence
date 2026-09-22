import pytest

from src.etl.normaliser import normalize_year, normalize_ticker


# ============================================================
# normalize_year - 20 tests
# ============================================================

def test_year_integer():
    assert normalize_year(2024) == 2024


def test_year_string():
    assert normalize_year("2024") == 2024


def test_year_with_spaces():
    assert normalize_year(" 2024 ") == 2024


def test_year_fy_prefix():
    assert normalize_year("FY2024") == 2024


def test_year_fy_space():
    assert normalize_year("FY 2024") == 2024


def test_year_lowercase_fy():
    assert normalize_year("fy2024") == 2024


def test_year_financial_range():
    assert normalize_year("2024-25") == 2024


def test_year_full_financial_range():
    assert normalize_year("2024-2025") == 2024


def test_year_fy_short():
    assert normalize_year("FY24") == 2024


def test_year_fy_short_23():
    assert normalize_year("FY23") == 2023


def test_year_fy_short_22():
    assert normalize_year("FY22") == 2022


def test_year_2000():
    assert normalize_year("2000") == 2000


def test_year_1999():
    assert normalize_year("1999") == 1999


def test_year_with_text():
    assert normalize_year("Financial Year 2024") == 2024


def test_year_with_dash():
    assert normalize_year("FY-2024") == 2024


def test_year_with_slash():
    assert normalize_year("2024/25") == 2024


def test_year_none_raises():
    with pytest.raises(ValueError):
        normalize_year(None)


def test_year_empty_raises():
    with pytest.raises(ValueError):
        normalize_year("")


def test_year_invalid_text_raises():
    with pytest.raises(ValueError):
        normalize_year("ABC")


def test_year_out_of_range_raises():
    with pytest.raises(ValueError):
        normalize_year("1800")


# ============================================================
# normalize_ticker - 15 tests
# ============================================================

def test_ticker_uppercase():
    assert normalize_ticker("RELIANCE") == "RELIANCE"


def test_ticker_lowercase():
    assert normalize_ticker("reliance") == "RELIANCE"


def test_ticker_spaces():
    assert normalize_ticker(" RELIANCE ") == "RELIANCE"


def test_ticker_internal_spaces():
    assert normalize_ticker("RELI ANCE") == "RELIANCE"


def test_ticker_ns_suffix():
    assert normalize_ticker("RELIANCE.NS") == "RELIANCE"


def test_ticker_bo_suffix():
    assert normalize_ticker("RELIANCE.BO") == "RELIANCE"


def test_ticker_nse_suffix():
    assert normalize_ticker("TCS-NSE") == "TCS"


def test_ticker_bse_suffix():
    assert normalize_ticker("TCS-BSE") == "TCS"


def test_ticker_ampersand():
    assert normalize_ticker("M&M") == "M&M"


def test_ticker_numeric():
    assert normalize_ticker("ABC123") == "ABC123"


def test_ticker_mixed_case():
    assert normalize_ticker("TaTaMoToRs") == "TATAMOTORS"


def test_ticker_none_raises():
    with pytest.raises(ValueError):
        normalize_ticker(None)


def test_ticker_empty_raises():
    with pytest.raises(ValueError):
        normalize_ticker("")


def test_ticker_invalid_raises():
    with pytest.raises(ValueError):
        normalize_ticker("N/A")


def test_ticker_too_long_raises():
    with pytest.raises(ValueError):
        normalize_ticker("A" * 31)
