from pathlib import Path
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "nifty100.db")
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATASET FILES
# ============================================================

FILES = {
    "companies": "companies_clean.parquet",
    "sectors": "sectors_clean.parquet",
    "profit_loss": "profit_loss_clean.parquet",
    "balance_sheet": "balance_sheet_clean.parquet",
    "cash_flow": "cash_flow_clean.parquet",
    "financial_ratios": "financial_ratios_clean.parquet",
    "market_cap": "market_cap_clean.parquet",
    "stock_prices": "stock_prices_clean.parquet",
    "documents": "documents_clean.parquet",
    "pros_cons": "pros_cons_clean.parquet",
    "peer_groups": "peer_groups_clean.parquet",
    "analysis": "analysis_clean.parquet",
}


# ============================================================
# HELPERS
# ============================================================

def load_parquet(name):
    path = PROCESSED_DIR / FILES[name]

    if not path.exists():
        raise FileNotFoundError(f"Missing processed file: {path}")

    return pd.read_parquet(path)


def clean_value(value):
    if pd.isna(value):
        return None

    return value


def safe_float(value):
    if pd.isna(value):
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value):
    if pd.isna(value):
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# COMPANY MAPPING
# ============================================================

def build_company_mapping(conn):
    """
    Load the current 92-company master and create:

        ticker -> integer company_id

    The source uses ticker strings while SQLite uses integer PKs.
    """

    df = load_parquet("companies")

    # Current master is the authoritative company universe.
    df = df.copy()

    # Normalize ticker identifiers.
    df["ticker"] = (
        df["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Remove accidental duplicates.
    df = df.drop_duplicates(subset=["ticker"])

    mapping = {}

    for _, row in df.iterrows():

        ticker = row["ticker"]

        cursor = conn.execute(
            """
            INSERT INTO companies (
                ticker,
                company_name,
                website
            )
            VALUES (?, ?, ?)
            """,
            (
                ticker,
                clean_value(row.get("company_name")),
                clean_value(row.get("website")),
            ),
        )

        company_id = cursor.lastrowid
        mapping[ticker] = company_id

    print(f"[OK] Companies loaded: {len(mapping)}")

    return mapping


# ============================================================
# SECTORS
# ============================================================

def load_sectors(conn, mapping):
    df = load_parquet("sectors")

    loaded = 0

    sectors = (
        df["broad_sector"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    for sector in sectors:
        conn.execute(
            """
            INSERT OR IGNORE INTO sectors (sector_name)
            VALUES (?)
            """,
            (sector,),
        )

    # Update company sector/industry.
    for _, row in df.iterrows():

        ticker = str(row["company_id"]).strip().upper()

        if ticker not in mapping:
            continue

        sector = clean_value(row.get("broad_sector"))
        industry = clean_value(row.get("sub_sector"))

        conn.execute(
            """
            UPDATE companies
            SET sector = ?,
                industry = ?
            WHERE company_id = ?
            """,
            (
                sector,
                industry,
                mapping[ticker],
            ),
        )

        loaded += 1

    print(f"[OK] Sector/company records processed: {loaded}")


# ============================================================
# PROFIT & LOSS
# ============================================================

def load_profit_loss(conn, mapping):
    df = load_parquet("profit_loss")

    loaded = 0
    skipped = 0

    for _, r in df.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        if ticker not in mapping:
            skipped += 1
            continue

        conn.execute(
            """
            INSERT OR IGNORE INTO profitandloss (
                company_id,
                year,
                sales,
                expenses,
                operating_profit,
                operating_margin,
                other_income,
                interest,
                depreciation,
                profit_before_tax,
                tax,
                net_profit,
                eps
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mapping[ticker],
                safe_int(r["year"]),
                safe_float(r["sales"]),
                safe_float(r["expenses"]),
                safe_float(r["operating_profit"]),
                safe_float(r["operating_profit_margin_pct"]),
                safe_float(r["other_income"]),
                safe_float(r["interest_expense"]),
                safe_float(r["depreciation"]),
                safe_float(r["profit_before_tax"]),
                safe_float(r["tax_percentage"]),
                safe_float(r["net_profit"]),
                safe_float(r["earnings_per_share"]),
            ),
        )

        loaded += 1

    print(
        f"[OK] Profit & Loss: {loaded} loaded, "
        f"{skipped} skipped"
    )


# ============================================================
# BALANCE SHEET
# ============================================================

def load_balance_sheet(conn, mapping):
    df = load_parquet("balance_sheet")

    loaded = 0
    skipped = 0

    for _, r in df.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        if ticker not in mapping:
            skipped += 1
            continue

        conn.execute(
            """
            INSERT OR IGNORE INTO balancesheet (
                company_id,
                year,
                total_assets,
                total_liabilities,
                equity,
                reserves,
                borrowings,
                cash,
                investments,
                receivables,
                inventory
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mapping[ticker],
                safe_int(r["year"]),
                safe_float(r["total_assets"]),
                safe_float(r["total_liabilities"]),
                safe_float(r["equity_capital"]),
                safe_float(r["reserves"]),
                safe_float(r["borrowings"]),
                None,
                safe_float(r["investments"]),
                None,
                None,
            ),
        )

        loaded += 1

    print(
        f"[OK] Balance Sheet: {loaded} loaded, "
        f"{skipped} skipped"
    )


# ============================================================
# CASH FLOW
# ============================================================

def load_cash_flow(conn, mapping):
    """
    net_cash_flow is deliberately NOT stored as free_cash_flow.
    Free cash flow comes from financial_ratios_clean.
    """

    cf = load_parquet("cash_flow")
    ratios = load_parquet("financial_ratios")

    # Build FCF lookup.
    fcf_lookup = {}

    for _, r in ratios.iterrows():

        ticker = str(r["company_id"]).strip().upper()
        year = safe_int(r["year"])

        fcf_lookup[(ticker, year)] = safe_float(
            r["free_cash_flow_cr"]
        )

    loaded = 0
    skipped = 0

    for _, r in cf.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        # Correct source typo.
        if ticker == "AGTL":
            ticker = "ATGL"

        if ticker not in mapping:
            skipped += 1
            continue

        year = safe_int(r["year"])

        free_cash_flow = fcf_lookup.get(
            (ticker, year)
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO cashflow (
                company_id,
                year,
                operating_cash_flow,
                investing_cash_flow,
                financing_cash_flow,
                free_cash_flow
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                mapping[ticker],
                year,
                safe_float(r["operating_cash_flow"]),
                safe_float(r["investing_cash_flow"]),
                safe_float(r["financing_cash_flow"]),
                free_cash_flow,
            ),
        )

        loaded += 1

    print(
        f"[OK] Cash Flow: {loaded} loaded, "
        f"{skipped} skipped"
    )


# ============================================================
# FINANCIAL RATIOS
# ============================================================

def load_financial_ratios(conn, mapping):
    ratios = load_parquet("financial_ratios")
    market = load_parquet("market_cap")

    # Lookup valuation metrics from market cap dataset.
    market_lookup = {}

    for _, r in market.iterrows():

        ticker = str(r["company_id"]).strip().upper()
        year = safe_int(r["year"])

        market_lookup[(ticker, year)] = {
            "pe": safe_float(r["pe_ratio"]),
            "pb": safe_float(r["pb_ratio"]),
            "dividend_yield": safe_float(
                r["dividend_yield_pct"]
            ),
        }

    loaded = 0
    skipped = 0

    for _, r in ratios.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        if ticker not in mapping:
            skipped += 1
            continue

        year = safe_int(r["year"])

        valuation = market_lookup.get(
            (ticker, year),
            {}
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO financial_ratios (
                company_id,
                year,
                pe_ratio,
                pb_ratio,
                roe,
                roce,
                debt_to_equity,
                current_ratio,
                dividend_yield,
                operating_margin,
                net_profit_margin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mapping[ticker],
                year,
                valuation.get("pe"),
                valuation.get("pb"),
                safe_float(r["return_on_equity_pct"]),
                None,
                safe_float(r["debt_to_equity"]),
                None,
                valuation.get("dividend_yield"),
                safe_float(r["operating_profit_margin_pct"]),
                safe_float(r["net_profit_margin_pct"]),
            ),
        )

        loaded += 1

    print(
        f"[OK] Financial Ratios: {loaded} loaded, "
        f"{skipped} skipped"
    )


# ============================================================
# STOCK PRICES
# ============================================================

def load_stock_prices(conn, mapping):
    df = load_parquet("stock_prices")

    loaded = 0
    skipped = 0

    for _, r in df.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        if ticker not in mapping:
            skipped += 1
            continue

        conn.execute(
            """
            INSERT OR IGNORE INTO stock_prices (
                company_id,
                trade_date,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mapping[ticker],
                str(r["date"]),
                safe_float(r["open_price"]),
                safe_float(r["high_price"]),
                safe_float(r["low_price"]),
                safe_float(r["close_price"]),
                safe_float(r["volume"]),
            ),
        )

        loaded += 1

    print(
        f"[OK] Stock Prices: {loaded} loaded, "
        f"{skipped} skipped"
    )


# ============================================================
# DOCUMENTS
# ============================================================

def load_documents(conn, mapping):
    df = load_parquet("documents")

    loaded = 0
    skipped = 0

    for _, r in df.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        if ticker not in mapping:
            skipped += 1
            continue

        year = safe_int(r["year"])

        document_date = (
            f"{year}-12-31"
            if year is not None
            else None
        )

        conn.execute(
            """
            INSERT INTO documents (
                company_id,
                document_type,
                document_url,
                document_date
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                mapping[ticker],
                "Annual Report",
                clean_value(r["annual_report"]),
                document_date,
            ),
        )

        loaded += 1

    print(
        f"[OK] Documents: {loaded} loaded, "
        f"{skipped} skipped"
    )


# ============================================================
# PROS & CONS
# ============================================================

def load_pros_cons(conn, mapping):
    df = load_parquet("pros_cons")

    loaded = 0
    skipped = 0

    for _, r in df.iterrows():

        ticker = str(r["company_id"]).strip().upper()

        if ticker not in mapping:
            skipped += 1
            continue

        pros = clean_value(r["pros"])
        cons = clean_value(r["cons"])

        if pros:
            conn.execute(
                """
                INSERT INTO prosandcons (
                    company_id,
                    item_type,
                    description
                )
                VALUES (?, ?, ?)
                """,
                (
                    mapping[ticker],
                    "PRO",
                    str(pros),
                ),
            )
            loaded += 1

        if cons:
            conn.execute(
                """
                INSERT INTO prosandcons (
                    company_id,
                    item_type,
                    description
                )
                VALUES (?, ?, ?)
                """,
                (
                    mapping[ticker],
                    "CON",
                    str(cons),
                ),
            )
            loaded += 1

    print(
        f"[OK] Pros & Cons: {loaded} items loaded, "
        f"{skipped} companies skipped"
    )


# ============================================================
# PEER GROUPS
# ============================================================

def load_peer_groups(conn, mapping):
    """
    The source contains group membership, not pairwise
    similarity scores.

    We therefore do NOT invent peer_company_id values.

    Instead, create safe pairwise relationships among
    companies belonging to the same peer group.

    similarity_score is left NULL because the source
    does not provide an actual similarity score.
    """

    df = load_parquet("peer_groups")

    loaded = 0

    groups = df.groupby("peer_group_name")

    for _, group in groups:

        tickers = [
            str(x).strip().upper()
            for x in group["company_id"].dropna()
        ]

        tickers = [
            t for t in tickers
            if t in mapping
        ]

        for company in tickers:

            for peer in tickers:

                if company == peer:
                    continue

                conn.execute(
                    """
                    INSERT OR IGNORE INTO peer_groups (
                        company_id,
                        peer_company_id,
                        similarity_score
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        mapping[company],
                        mapping[peer],
                        None,
                    ),
                )

                loaded += 1

    print(f"[OK] Peer relationships generated: {loaded}")


# ============================================================
# DATABASE VALIDATION
# ============================================================

def print_database_summary(conn):

    tables = [
        "companies",
        "sectors",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "stock_prices",
        "documents",
        "prosandcons",
        "peer_groups",
        "analysis",
    ]

    print("\n" + "=" * 60)
    print("DATABASE LOAD SUMMARY")
    print("=" * 60)

    for table in tables:

        result = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        print(
            f"{table:<20} {result[0]:>8,} rows"
        )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("N100 FINANCIAL INTELLIGENCE - DATABASE LOADER")
    print("=" * 60)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    print(f"Database: {DB_PATH}")
    print(f"Processed data: {PROCESSED_DIR}")

    conn = sqlite3.connect(DB_PATH)

    # Enforce foreign keys.
    conn.execute("PRAGMA foreign_keys = ON")

    try:

        print("\nLoading company master...")
        mapping = build_company_mapping(conn)

        print("\nLoading sectors...")
        load_sectors(conn, mapping)

        print("\nLoading Profit & Loss...")
        load_profit_loss(conn, mapping)

        print("\nLoading Balance Sheet...")
        load_balance_sheet(conn, mapping)

        print("\nLoading Cash Flow...")
        load_cash_flow(conn, mapping)

        print("\nLoading Financial Ratios...")
        load_financial_ratios(conn, mapping)

        print("\nLoading Stock Prices...")
        load_stock_prices(conn, mapping)

        print("\nLoading Documents...")
        load_documents(conn, mapping)

        print("\nLoading Pros & Cons...")
        load_pros_cons(conn, mapping)

        print("\nLoading Peer Groups...")
        load_peer_groups(conn, mapping)

        conn.commit()

        print_database_summary(conn)

        # Foreign-key validation.
        fk_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            print("\n[ERROR] Foreign-key violations:")
            for error in fk_errors:
                print(error)
        else:
            print("\n[OK] Foreign-key integrity check passed.")

        print("\n[OK] DATABASE LOAD COMPLETED.")

    except Exception as exc:

        conn.rollback()

        print("\n[ERROR] Database load failed.")
        print(f"Reason: {exc}")

        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()