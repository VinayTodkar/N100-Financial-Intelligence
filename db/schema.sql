PRAGMA foreign_keys = ON;

-- ============================================================
-- N100 FINANCIAL INTELLIGENCE DATABASE SCHEMA
-- ============================================================

CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    isin TEXT UNIQUE,
    bse_code TEXT,
    nse_code TEXT,
    website TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sectors (
    sector_id INTEGER PRIMARY KEY,
    sector_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS profitandloss (
    pl_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    operating_margin REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax REAL,
    net_profit REAL,
    eps REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, year)
);

CREATE TABLE IF NOT EXISTS balancesheet (
    bs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    total_assets REAL,
    total_liabilities REAL,
    equity REAL,
    reserves REAL,
    borrowings REAL,
    cash REAL,
    investments REAL,
    receivables REAL,
    inventory REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, year)
);

CREATE TABLE IF NOT EXISTS cashflow (
    cf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    operating_cash_flow REAL,
    investing_cash_flow REAL,
    financing_cash_flow REAL,
    free_cash_flow REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, year)
);

CREATE TABLE IF NOT EXISTS analysis (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    health_score REAL,
    growth_score REAL,
    profitability_score REAL,
    valuation_score REAL,
    risk_score REAL,
    investment_view TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, year)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    document_type TEXT,
    document_url TEXT,
    document_date TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS prosandcons (
    proscons_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    description TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS stock_prices (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, trade_date)
);

CREATE TABLE IF NOT EXISTS financial_ratios (
    ratio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pe_ratio REAL,
    pb_ratio REAL,
    roe REAL,
    roce REAL,
    debt_to_equity REAL,
    current_ratio REAL,
    dividend_yield REAL,
    operating_margin REAL,
    net_profit_margin REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, year)
);

CREATE TABLE IF NOT EXISTS peer_groups (
    peer_group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    peer_company_id INTEGER NOT NULL,
    similarity_score REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (peer_company_id) REFERENCES companies(company_id),
    UNIQUE(company_id, peer_company_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_pl_company
ON profitandloss(company_id);

CREATE INDEX IF NOT EXISTS idx_bs_company
ON balancesheet(company_id);

CREATE INDEX IF NOT EXISTS idx_cf_company
ON cashflow(company_id);

CREATE INDEX IF NOT EXISTS idx_prices_company
ON stock_prices(company_id);

CREATE INDEX IF NOT EXISTS idx_prices_date
ON stock_prices(trade_date);

CREATE INDEX IF NOT EXISTS idx_ratios_company
ON financial_ratios(company_id);

CREATE INDEX IF NOT EXISTS idx_analysis_company
ON analysis(company_id);

CREATE INDEX IF NOT EXISTS idx_documents_company
ON documents(company_id);

CREATE INDEX IF NOT EXISTS idx_prosandcons_company
ON prosandcons(company_id);

CREATE INDEX IF NOT EXISTS idx_peer_groups_company
ON peer_groups(company_id);
