-- ============================================================
-- N100 FINANCIAL INTELLIGENCE
-- Sprint 1 - Exploratory SQL Queries
-- ============================================================

-- Q1. Company master overview
SELECT
    company_id,
    ticker,
    company_name,
    sector,
    industry,
    nse_code,
    bse_code
FROM companies
ORDER BY company_name;


-- Q2. Companies with the highest latest net profit
WITH latest AS (
    SELECT
        company_id,
        MAX(year) AS latest_year
    FROM profitandloss
    GROUP BY company_id
)
SELECT
    c.ticker,
    c.company_name,
    p.year,
    p.net_profit
FROM profitandloss p
JOIN latest l
    ON p.company_id = l.company_id
   AND p.year = l.latest_year
JOIN companies c
    ON c.company_id = p.company_id
ORDER BY p.net_profit DESC
LIMIT 10;


-- Q3. Companies with the highest latest revenue
WITH latest AS (
    SELECT
        company_id,
        MAX(year) AS latest_year
    FROM profitandloss
    GROUP BY company_id
)
SELECT
    c.ticker,
    c.company_name,
    p.year,
    p.sales
FROM profitandloss p
JOIN latest l
    ON p.company_id = l.company_id
   AND p.year = l.latest_year
JOIN companies c
    ON c.company_id = p.company_id
ORDER BY p.sales DESC
LIMIT 10;


-- Q4. Latest financial ratios for each company
WITH latest AS (
    SELECT
        company_id,
        MAX(year) AS latest_year
    FROM financial_ratios
    GROUP BY company_id
)
SELECT
    c.ticker,
    c.company_name,
    r.year,
    r.roe,
    r.debt_to_equity,
    r.net_profit_margin,
    r.operating_margin,
    r.roce
FROM financial_ratios r
JOIN latest l
    ON r.company_id = l.company_id
   AND r.year = l.latest_year
JOIN companies c
    ON c.company_id = r.company_id
ORDER BY r.roe DESC
LIMIT 20;


-- Q5. Companies with the highest operating cash flow
WITH latest AS (
    SELECT
        company_id,
        MAX(year) AS latest_year
    FROM cashflow
    GROUP BY company_id
)
SELECT
    c.ticker,
    c.company_name,
    cf.year,
    cf.operating_cash_flow
FROM cashflow cf
JOIN latest l
    ON cf.company_id = l.company_id
   AND cf.year = l.latest_year
JOIN companies c
    ON c.company_id = cf.company_id
ORDER BY cf.operating_cash_flow DESC
LIMIT 10;


-- Q6. Companies with the highest debt-to-equity ratio
WITH latest AS (
    SELECT
        company_id,
        MAX(year) AS latest_year
    FROM financial_ratios
    GROUP BY company_id
)
SELECT
    c.ticker,
    c.company_name,
    r.year,
    r.debt_to_equity
FROM financial_ratios r
JOIN latest l
    ON r.company_id = l.company_id
   AND r.year = l.latest_year
JOIN companies c
    ON c.company_id = r.company_id
WHERE r.debt_to_equity IS NOT NULL
ORDER BY r.debt_to_equity DESC
LIMIT 10;


-- Q7. Financial history coverage by company
SELECT
    c.ticker,
    c.company_name,
    COUNT(DISTINCT p.year) AS pnl_years,
    COUNT(DISTINCT b.year) AS balance_sheet_years,
    COUNT(DISTINCT cf.year) AS cashflow_years,
    COUNT(DISTINCT r.year) AS ratio_years
FROM companies c
LEFT JOIN profitandloss p
    ON c.company_id = p.company_id
LEFT JOIN balancesheet b
    ON c.company_id = b.company_id
LEFT JOIN cashflow cf
    ON c.company_id = cf.company_id
LEFT JOIN financial_ratios r
    ON c.company_id = r.company_id
GROUP BY c.company_id, c.ticker, c.company_name
ORDER BY pnl_years ASC, c.ticker;


-- Q8. Companies with fewer than 5 years of P&L history
SELECT
    c.ticker,
    c.company_name,
    COUNT(DISTINCT p.year) AS available_years
FROM companies c
LEFT JOIN profitandloss p
    ON c.company_id = p.company_id
GROUP BY c.company_id, c.ticker, c.company_name
HAVING COUNT(DISTINCT p.year) < 5
ORDER BY available_years ASC;


-- Q9. Latest market price information
WITH latest AS (
    SELECT
        company_id,
        MAX(trade_date) AS latest_date
    FROM stock_prices
    GROUP BY company_id
)
SELECT
    c.ticker,
    c.company_name,
    s.trade_date,
    s.close,
    s.volume
FROM stock_prices s
JOIN latest l
    ON s.company_id = l.company_id
   AND s.trade_date = l.latest_date
JOIN companies c
    ON c.company_id = s.company_id
ORDER BY s.close DESC
LIMIT 20;


-- Q10. Number of companies by sector
SELECT
    sector,
    COUNT(*) AS company_count
FROM companies
WHERE sector IS NOT NULL
  AND TRIM(sector) <> ''
GROUP BY sector
ORDER BY company_count DESC, sector;
