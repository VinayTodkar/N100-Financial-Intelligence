"""
N100 Financial Intelligence - Data Normalisation Utilities.

Provides helpers for normalising financial years and stock tickers
before loading source data into the database.
"""

import re
from typing import Any


def normalize_year(value: Any) -> int:
    """
    Normalize a financial year into its starting year.

    Examples:
        2024       -> 2024
        "2024"     -> 2024
        "FY2024"   -> 2024
        "FY 2024"  -> 2024
        "2024-25"  -> 2024
        "FY24"     -> 2024
        "2024-2025"-> 2024

    Raises:
        ValueError: If the value cannot be converted to a valid year.
    """
    if value is None:
        raise ValueError("Year cannot be None")

    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid year")

    text = str(value).strip().upper()

    if not text or text in {"NAN", "NONE", "NULL", "NA", "N/A", "-"}:
        raise ValueError(f"Invalid year: {value}")

    # Remove common FY prefixes.
    text = re.sub(r"^F\.?\s*Y\.?\s*", "", text)

    # Extract first 4-digit year.
    match = re.search(r"(19\d{2}|20\d{2})", text)

    if match:
        year = int(match.group(1))
    else:
        # Handle two-digit FY values such as FY24.
        short_match = re.search(r"\b(\d{2})\b", text)

        if not short_match:
            raise ValueError(f"Invalid year: {value}")

        short_year = int(short_match.group(1))
        year = 2000 + short_year if short_year <= 50 else 1900 + short_year

    if year < 1900 or year > 2100:
        raise ValueError(f"Year out of valid range: {year}")

    return year


def normalize_ticker(value: Any) -> str:
    """
    Normalize an Indian stock ticker.

    Examples:
        "RELIANCE"       -> "RELIANCE"
        " reliance "     -> "RELIANCE"
        "reliance"       -> "RELIANCE"
        "RELIANCE.NS"    -> "RELIANCE"
        "RELIANCE.BO"    -> "RELIANCE"
        "TCS-IN"         -> "TCS"
        "M&M"            -> "M&M"

    Raises:
        ValueError: If the ticker is empty or invalid.
    """
    if value is None:
        raise ValueError("Ticker cannot be None")

    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid ticker")

    ticker = str(value).strip().upper()

    if not ticker or ticker in {"NAN", "NONE", "NULL", "NA", "N/A", "-"}:
        raise ValueError(f"Invalid ticker: {value}")

    # Remove common exchange suffixes.
    ticker = re.sub(r"\.(NS|BO|NSE|BSE)$", "", ticker)

    # Remove common trailing exchange separators.
    ticker = re.sub(r"[-_](NSE|BSE|NS|BO)$", "", ticker)

    # Remove spaces inside ticker.
    ticker = re.sub(r"\s+", "", ticker)

    # Keep letters, numbers, &, and hyphen.
    ticker = re.sub(r"[^A-Z0-9&-]", "", ticker)

    if not ticker:
        raise ValueError(f"Invalid ticker: {value}")

    if len(ticker) > 30:
        raise ValueError(f"Ticker is too long: {value}")

    return ticker
