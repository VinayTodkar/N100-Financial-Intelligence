"""
N100 Financial Intelligence - Data Quality Validator.

Implements the 16 Sprint-1 data quality rules.
The validator works on pandas DataFrames and produces
structured validation failures suitable for CSV reporting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


CRITICAL = "CRITICAL"
WARNING = "WARNING"


def _failure(
    rule: str,
    severity: str,
    message: str,
    rows: int = 0,
) -> dict[str, Any]:
    return {
        "rule": rule,
        "severity": severity,
        "message": message,
        "rows": rows,
    }


def _column(df: pd.DataFrame, *names: str) -> str | None:
    """Find a column ignoring case, spaces and underscores."""
    lookup = {
        str(c).strip().lower().replace(" ", "_"): c
        for c in df.columns
    }

    for name in names:
        key = name.strip().lower().replace(" ", "_")
        if key in lookup:
            return lookup[key]

    return None


# ---------------------------------------------------------------------
# DQ-01 — Primary-key uniqueness
# ---------------------------------------------------------------------

def dq01_pk_uniqueness(
    df: pd.DataFrame,
    columns: list[str],
) -> list[dict[str, Any]]:
    if not columns or any(c not in df.columns for c in columns):
        return []

    duplicate_count = int(df.duplicated(subset=columns).sum())

    if duplicate_count:
        return [
            _failure(
                "DQ-01",
                CRITICAL,
                f"Duplicate primary-key values found for {columns}.",
                duplicate_count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-02 — Company/year uniqueness
# ---------------------------------------------------------------------

def dq02_company_year_uniqueness(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    company = _column(df, "company_id", "company", "ticker")
    year = _column(df, "year", "financial_year", "fy")

    if not company or not year:
        return []

    duplicate_count = int(df.duplicated(subset=[company, year]).sum())

    if duplicate_count:
        return [
            _failure(
                "DQ-02",
                CRITICAL,
                f"Duplicate ({company}, {year}) combinations found.",
                duplicate_count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-03 — Foreign-key integrity
# ---------------------------------------------------------------------

def dq03_fk_integrity(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    child_column: str,
    parent_column: str,
) -> list[dict[str, Any]]:
    if child_column not in child_df.columns:
        return []

    if parent_column not in parent_df.columns:
        return []

    parent_values = set(parent_df[parent_column].dropna())

    invalid = ~child_df[child_column].isin(parent_values)
    count = int(invalid.sum())

    if count:
        return [
            _failure(
                "DQ-03",
                CRITICAL,
                f"{count} foreign-key values do not exist in parent table.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-04 — Balance sheet balance
# ---------------------------------------------------------------------

def dq04_balance_sheet_balance(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    assets = _column(df, "total_assets", "assets")
    liabilities = _column(
        df,
        "total_liabilities",
        "liabilities",
        "total_liabilities_and_equity",
    )

    if not assets or not liabilities:
        return []

    a = pd.to_numeric(df[assets], errors="coerce")
    l = pd.to_numeric(df[liabilities], errors="coerce")

    denominator = a.abs().replace(0, pd.NA)
    difference_pct = ((a - l).abs() / denominator) * 100

    invalid = difference_pct > 1
    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-04",
                WARNING,
                "Balance sheet difference exceeds 1%.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-05 — Operating margin cross-check
# ---------------------------------------------------------------------

def dq05_opm_crosscheck(
    df: pd.DataFrame,
    tolerance: float = 1.0,
) -> list[dict[str, Any]]:
    sales = _column(df, "sales", "revenue", "total_sales")
    op_profit = _column(
        df,
        "operating_profit",
        "operating_profit_loss",
        "op_profit",
    )
    opm = _column(
        df,
        "opm",
        "operating_margin",
        "operating_profit_margin",
    )

    if not sales or not op_profit or not opm:
        return []

    sales_values = pd.to_numeric(df[sales], errors="coerce")
    profit_values = pd.to_numeric(df[op_profit], errors="coerce")
    reported = pd.to_numeric(df[opm], errors="coerce")

    calculated = (profit_values / sales_values) * 100

    difference = (calculated - reported).abs()
    invalid = difference > tolerance

    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-05",
                WARNING,
                "Reported OPM differs from calculated OPM.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-06 — Positive sales
# ---------------------------------------------------------------------

def dq06_positive_sales(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    sales = _column(df, "sales", "revenue", "total_sales")

    if not sales:
        return []

    values = pd.to_numeric(df[sales], errors="coerce")
    invalid = values <= 0
    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-06",
                WARNING,
                "Sales/revenue contains zero or negative values.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-07 — Net cash calculation
# ---------------------------------------------------------------------

def dq07_net_cash(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    cash = _column(df, "cash", "cash_and_equivalents")
    debt = _column(df, "debt", "total_debt")
    net_cash = _column(df, "net_cash")

    if not cash or not debt or not net_cash:
        return []

    c = pd.to_numeric(df[cash], errors="coerce")
    d = pd.to_numeric(df[debt], errors="coerce")
    reported = pd.to_numeric(df[net_cash], errors="coerce")

    difference = (c - d - reported).abs()
    invalid = difference > 1

    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-07",
                WARNING,
                "Net cash does not match cash minus debt.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-08 — Tax rate
# ---------------------------------------------------------------------

def dq08_tax_rate(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    tax = _column(df, "tax_rate", "tax_percent", "tax_pct")

    if not tax:
        return []

    values = pd.to_numeric(df[tax], errors="coerce")
    invalid = (values < -100) | (values > 100)
    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-08",
                WARNING,
                "Tax rate is outside the valid -100% to 100% range.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-09 — Dividend cap
# ---------------------------------------------------------------------

def dq09_dividend_cap(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    dividend = _column(df, "dividend", "dividend_per_share")
    eps = _column(df, "eps", "earnings_per_share")

    if not dividend or not eps:
        return []

    d = pd.to_numeric(df[dividend], errors="coerce")
    e = pd.to_numeric(df[eps], errors="coerce")

    invalid = (e > 0) & (d > e)
    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-09",
                WARNING,
                "Dividend exceeds EPS.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-10 — Valid company URL
# ---------------------------------------------------------------------

def dq10_company_url(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    url = _column(df, "url", "website", "company_url")

    if not url:
        return []

    values = df[url].fillna("").astype(str).str.strip()

    invalid = (
        (values != "")
        & ~values.str.lower().str.startswith(
            ("http://", "https://")
        )
    )

    count = int(invalid.sum())

    if count:
        return [
            _failure(
                "DQ-10",
                WARNING,
                "Company URL does not use HTTP or HTTPS.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-11 — EPS sign consistency
# ---------------------------------------------------------------------

def dq11_eps_sign(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    profit = _column(
        df,
        "net_profit",
        "net_profit_loss",
        "profit_after_tax",
        "pat",
    )
    eps = _column(df, "eps", "earnings_per_share")

    if not profit or not eps:
        return []

    p = pd.to_numeric(df[profit], errors="coerce")
    e = pd.to_numeric(df[eps], errors="coerce")

    invalid = ((p > 0) & (e < 0)) | ((p < 0) & (e > 0))
    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-11",
                WARNING,
                "EPS sign is inconsistent with net profit sign.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-12 — BSE balance
# ---------------------------------------------------------------------

def dq12_bse_balance(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    bse_assets = _column(df, "bse_assets")
    bse_liabilities = _column(df, "bse_liabilities")

    if not bse_assets or not bse_liabilities:
        return []

    assets = pd.to_numeric(df[bse_assets], errors="coerce")
    liabilities = pd.to_numeric(df[bse_liabilities], errors="coerce")

    invalid = (assets - liabilities).abs() > 1
    count = int(invalid.fillna(False).sum())

    if count:
        return [
            _failure(
                "DQ-12",
                WARNING,
                "BSE balance sheet values do not reconcile.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-13 — Required fields
# ---------------------------------------------------------------------

def dq13_required_fields(
    df: pd.DataFrame,
    required_columns: list[str],
) -> list[dict[str, Any]]:
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        return [
            _failure(
                "DQ-13",
                CRITICAL,
                f"Required columns missing: {missing_columns}.",
                len(missing_columns),
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-14 — Year coverage
# ---------------------------------------------------------------------

def dq14_year_coverage(
    df: pd.DataFrame,
    minimum_years: int = 5,
) -> list[dict[str, Any]]:
    company = _column(df, "company_id", "company", "ticker")
    year = _column(df, "year", "financial_year", "fy")

    if not company or not year:
        return []

    coverage = df.groupby(company)[year].nunique()
    insufficient = coverage < minimum_years
    count = int(insufficient.sum())

    if count:
        return [
            _failure(
                "DQ-14",
                WARNING,
                f"{count} companies have fewer than {minimum_years} years.",
                count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-15 — Null-value check
# ---------------------------------------------------------------------

def dq15_null_values(
    df: pd.DataFrame,
    required_columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    columns = required_columns or list(df.columns)

    existing = [c for c in columns if c in df.columns]

    if not existing:
        return []

    null_count = int(df[existing].isna().sum().sum())

    if null_count:
        return [
            _failure(
                "DQ-15",
                WARNING,
                f"Required data contains {null_count} null values.",
                null_count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# DQ-16 — Duplicate records
# ---------------------------------------------------------------------

def dq16_duplicate_records(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    duplicate_count = int(df.duplicated().sum())

    if duplicate_count:
        return [
            _failure(
                "DQ-16",
                WARNING,
                "Completely duplicated records found.",
                duplicate_count,
            )
        ]

    return []


# ---------------------------------------------------------------------
# Run all rules
# ---------------------------------------------------------------------

def validate_dataframe(
    df: pd.DataFrame,
    *,
    primary_key: list[str] | None = None,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Execute all 16 DQ rules against a DataFrame.

    Rules that require unavailable columns simply skip themselves.
    """

    failures: list[dict[str, Any]] = []

    if primary_key:
        failures.extend(dq01_pk_uniqueness(df, primary_key))

    failures.extend(dq02_company_year_uniqueness(df))
    failures.extend(dq04_balance_sheet_balance(df))
    failures.extend(dq05_opm_crosscheck(df))
    failures.extend(dq06_positive_sales(df))
    failures.extend(dq07_net_cash(df))
    failures.extend(dq08_tax_rate(df))
    failures.extend(dq09_dividend_cap(df))
    failures.extend(dq10_company_url(df))
    failures.extend(dq11_eps_sign(df))
    failures.extend(dq12_bse_balance(df))

    if required_columns:
        failures.extend(
            dq13_required_fields(df, required_columns)
        )

    failures.extend(dq14_year_coverage(df))
    failures.extend(dq15_null_values(df, required_columns))
    failures.extend(dq16_duplicate_records(df))

    # DQ-03 requires parent/child DataFrames, so it is intentionally
    # exposed as a separate function rather than inferred here.

    columns = [
        "rule",
        "severity",
        "message",
        "rows",
    ]

    return pd.DataFrame(failures, columns=columns)


def save_validation_report(
    failures: pd.DataFrame,
    output_path: str | Path = "output/validation_failures.csv",
) -> Path:
    """Save validation failures to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    failures.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    print("=" * 60)
    print("N100 FINANCIAL INTELLIGENCE - DATA QUALITY VALIDATOR")
    print("=" * 60)
    print("Validator loaded successfully.")
    print("Implemented rules: DQ-01 through DQ-16")
