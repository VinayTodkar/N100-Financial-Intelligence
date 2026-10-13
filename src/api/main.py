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


@app.middleware("http")
async def log_requests(request, call_next):
    logger.info("Request started: %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        logger.info(
            "Request completed: %s %s -> %s",
            request.method, request.url.path, response.status_code
        )
        return response
    except Exception:
        logger.exception("Request failed: %s %s", request.method, request.url.path)
        raise


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
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from fastapi.responses import StreamingResponse

    data = tearsheet(company_id)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4
    x, y = 50, page_height - 55

    def write_line(text):
        nonlocal y
        text = str(text).encode("latin-1", "replace").decode("latin-1")
        while len(text) > 95:
            pdf.drawString(x, y, text[:95])
            text = text[95:]
            y -= 15
            if y < 55:
                pdf.showPage()
                y = page_height - 55
        pdf.drawString(x, y, text)
        y -= 17
        if y < 55:
            pdf.showPage()
            y = page_height - 55

    write_line("N100 Financial Intelligence - Company Tearsheet")
    write_line("=" * 55)
    write_line("Company profile")
    for key, value in data["company"].items():
        write_line(f"{key}: {value}")
    for section in ("profit_loss", "balance_sheet", "cashflow", "ratios"):
        write_line("")
        write_line(section.replace("_", " ").title())
        records = data.get(section, [])
        if not records:
            write_line("No records available.")
        for record in records:
            write_line(" | ".join(f"{k}: {v}" for k, v in record.items()))
    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="company_{company_id}_tearsheet.pdf"'
        },
    )
