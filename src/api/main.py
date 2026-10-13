import logging
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("n100-api")

app = FastAPI(
    title="N100 Financial Intelligence API",
    description="API for Nifty 100 financial company data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def query_db(sql, params=()):
    if not DB_PATH.exists():
        raise HTTPException(503, "SQLite database not found")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in conn.execute(sql, params).fetchall()
            ]
    except sqlite3.Error as exc:
        logger.exception("Database query failed")
        raise HTTPException(500, "Database query failed") from exc


def has_table(name):
    result = query_db(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return bool(result)


def rows_for(table, company_id=None, limit=500):
    if not has_table(table):
        return []

    columns = query_db(f'PRAGMA table_info("{table}")')
    column_names = {c["name"] for c in columns}

    if company_id is not None:
        if "company_id" not in column_names:
            return []
        return query_db(
            f'SELECT * FROM "{table}" WHERE company_id=? LIMIT ?',
            (company_id, limit),
        )

    return query_db(f'SELECT * FROM "{table}" LIMIT ?', (limit,))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_exists": DB_PATH.exists(),
    }


@app.get("/api/companies")
def companies(limit: int = Query(100, ge=1, le=500)):
    return rows_for("companies", limit=limit)


@app.get("/api/companies/{company_id}/profile")
def company_profile(company_id: int):
    result = query_db(
        "SELECT * FROM companies WHERE company_id=?",
        (company_id,),
    )
    if not result:
        raise HTTPException(404, "Company not found")
    return result[0]


@app.get("/api/companies/{company_id}/pnl")
def company_pnl(company_id: int):
    return rows_for("profitandloss", company_id)


@app.get("/api/companies/{company_id}/balance-sheet")
def balance_sheet(company_id: int):
    return rows_for("balancesheet", company_id)


@app.get("/api/companies/{company_id}/cashflow")
def cashflow(company_id: int):
    return rows_for("cashflow", company_id)


@app.get("/api/companies/{company_id}/ratios")
def ratios(company_id: int):
    return rows_for("financial_ratios", company_id)


@app.get("/api/companies/{company_id}/tearsheet")
def tearsheet(company_id: int):
    profile = company_profile(company_id)
    return {
        "company": profile,
        "profit_loss": rows_for("profitandloss", company_id),
        "balance_sheet": rows_for("balancesheet", company_id),
        "cashflow": rows_for("cashflow", company_id),
        "ratios": rows_for("financial_ratios", company_id),
    }


@app.get("/api/screener")
def screener(
    roe_min: float = 15,
    debt_to_equity_max: float = 1,
):
    if not has_table("financial_ratios"):
        raise HTTPException(503, "Financial ratios table unavailable")

    columns = {
        c["name"]
        for c in query_db("PRAGMA table_info(financial_ratios)")
    }
    required = {"company_id", "roe", "debt_to_equity"}
    if not required.issubset(columns):
        raise HTTPException(503, "Required KPI columns unavailable")

    return query_db(
        """
        SELECT c.company_id, c.ticker, c.company_name,
               r.year, r.roe, r.debt_to_equity
        FROM financial_ratios r
        JOIN companies c ON c.company_id = r.company_id
        WHERE r.roe > ? AND r.debt_to_equity < ?
        ORDER BY r.roe DESC
        LIMIT 500
        """,
        (roe_min, debt_to_equity_max),
    )


@app.get("/api/sectors")
def sectors():
    return rows_for("sectors")


@app.get("/api/companies/{company_id}/peers")
def peers(company_id: int):
    return rows_for("peer_groups", company_id)


@app.get("/api/market-cap")
def market_cap():
    if not has_table("market_cap"):
        return {
            "available": False,
            "message": "No dedicated market_cap table exists in this database.",
            "data": [],
        }
    return rows_for("market_cap")


@app.get("/api/portfolio-stats")
def portfolio_stats():
    result = query_db("SELECT COUNT(*) AS total FROM companies")
    return {"company_count": result[0]["total"]}


@app.get("/api/documents/{company_id}")
def documents(company_id: int):
    return rows_for("documents", company_id)


@app.get("/api/companies/{company_id}/stock-prices")
def stock_prices(company_id: int):
    return rows_for("stock_prices", company_id)


@app.get("/api/companies/{company_id}/pros-cons")
def pros_cons(company_id: int):
    return rows_for("prosandcons", company_id)


@app.get("/api/openapi.json")
def openapi_export():
    return app.openapi()


@app.get("/api/companies/{company_id}/tearsheet/download")
def download_tearsheet(company_id: int):
    from fastapi.responses import JSONResponse

    data = tearsheet(company_id)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition":
                f'attachment; filename="company_{company_id}_tearsheet.json"'
        },
    )
