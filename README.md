# N100 Financial Intelligence Platform

A production-oriented financial data engineering and analytics platform for the **Nifty 100**, designed to transform raw financial datasets into a validated SQLite database for financial analysis, screening, reporting, and downstream analytics.

## Project Overview

The N100 Financial Intelligence Platform processes financial and market datasets for **92 Nifty 100 companies**.

The platform covers:

* Company master data
* Sector and industry information
* Profit & Loss
* Balance Sheet
* Cash Flow
* Financial Ratios
* Stock Prices
* Annual Reports
* Pros & Cons
* Peer Groups

The project follows an ETL and data-quality workflow:

```text
Raw Excel Files
       │
       ▼
Data Cleaning & Standardization
       │
       ▼
Processed CSV / Parquet Data
       │
       ▼
Data Validation
       │
       ▼
SQLite Database
       │
       ▼
Testing & Exploratory SQL
       │
       ▼
Final QA
```

---

# Sprint 1 — Data Foundation

## Sprint Objective

Build and validate the data foundation required for the N100 Financial Intelligence Platform.

The Sprint 1 workflow includes:

1. Raw data inspection
2. Data cleaning and standardization
3. Data validation
4. SQLite database creation
5. ETL loading
6. Data-quality checks
7. Automated testing
8. Exploratory SQL analysis
9. Manual company-level QA
10. Final database integrity verification

---

# Dataset Coverage

The project uses **12 raw Excel source files**:

| Dataset          | Source File             |
| ---------------- | ----------------------- |
| Analysis         | `analysis.xlsx`         |
| Balance Sheet    | `balancesheet.xlsx`     |
| Cash Flow        | `cashflow.xlsx`         |
| Companies        | `companies.xlsx`        |
| Documents        | `documents.xlsx`        |
| Financial Ratios | `financial_ratios.xlsx` |
| Market Cap       | `market_cap.xlsx`       |
| Peer Groups      | `peer_groups.xlsx`      |
| Profit & Loss    | `profitandloss.xlsx`    |
| Pros & Cons      | `prosandcons.xlsx`      |
| Sectors          | `sectors.xlsx`          |
| Stock Prices     | `stock_prices.xlsx`     |

The raw files are cleaned and standardized before being loaded into the database.

---

# Database

The final SQLite database is:

```text
nifty100.db
```

The database contains the following tables:

```text
companies
sectors
profitandloss
balancesheet
cashflow
analysis
documents
prosandcons
stock_prices
financial_ratios
peer_groups
```

The database schema is defined in:

```text
db/schema.sql
```

SQLite foreign-key enforcement is enabled and was verified during final QA.

---

# Final Database Statistics

| Table            | Records |
| ---------------- | ------: |
| Companies        |      92 |
| Sectors          |      10 |
| Profit & Loss    |   1,073 |
| Balance Sheet    |   1,058 |
| Cash Flow        |   1,064 |
| Financial Ratios |   1,041 |
| Stock Prices     |   5,520 |
| Documents        |   1,456 |
| Pros & Cons      |      24 |
| Peer Groups      |     248 |
| Analysis         |       0 |

> `analysis` is currently a derived/placeholder table in the database schema and is not populated by the current Sprint 1 loader.

---

# ETL Pipeline

The ETL pipeline is organized under:

```text
src/etl/
```

Main components:

### `normaliser.py`

Responsible for standardizing fields such as:

* Years
* Tickers
* Text fields
* Numeric values
* Dates

### `validator.py`

Implements the Sprint 1 data-quality framework containing **DQ-01 through DQ-16**.

Validation areas include:

* Primary-key uniqueness
* Company/year uniqueness
* Foreign-key integrity
* Balance-sheet consistency
* Operating-margin checks
* Sales validation
* Net-cash validation
* Tax-rate validation
* Dividend validation
* URL validation
* EPS consistency
* Required fields
* Year coverage
* Null detection
* Duplicate detection

### `loader.py`

Loads the processed datasets into:

```text
nifty100.db
```

The loader also handles identifier normalization and relationships between source datasets.

---

# Data Quality Results

The master data validation report is stored at:

```text
data/reports/master_data_validation_report.json
```

The final DQ validation produced:

```text
Total failures: 7
Critical failures: 0
Warnings: 7
```

The validation results are stored at:

```text
output/validation_failures.csv
```

## Current warnings

The warnings include:

* One zero/negative sales record
* Three EPS sign-consistency warnings
* Limited P&L history for one company
* Limited Balance Sheet history
* Limited Cash Flow history
* Limited Financial Ratio history
* Null-related records associated with source data

These are documented as **warnings rather than critical failures**.

---

# Historical Coverage

The database was checked for companies with fewer than five years of financial history.

Result:

```text
Companies with fewer than 5 P&L years: 1

JIOFIN — Jio Financial Services Ltd
Available P&L years: 2
```

This is a documented historical-coverage limitation of the source data.

---

# TTM Records

The raw Profit & Loss dataset contains **TTM (Trailing Twelve Months)** records.

The source inspection identified:

```text
Raw TTM records: 100
Unique companies with TTM records: 99
```

TTM records are not treated as normal calendar/financial years. They are therefore not assigned artificial year values during standardization.

This prevents TTM data from being incorrectly represented as historical annual data.

---

# Automated Testing

Sprint 1 required automated ETL testing.

Final test result:

```text
35 passed in 0.18s
```

Therefore:

```text
35 / 35 tests passed
```

The test suite covers normalization and ETL-related functionality, including year and ticker normalization.

Run the test suite with:

```
```
