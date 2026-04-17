#!/usr/bin/env python3
"""
fetch_stocks.py
yfinance を使って stocks_list.csv の銘柄データを取得し、
data/stocks.json として保存する。
"""
import os
import csv
import json
import math
from datetime import datetime

import yfinance as yf


def safe_float(val, multiplier=1.0):
    try:
        if val is None:
            return None
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f * multiplier, 4)
    except (TypeError, ValueError):
        return None


def read_stocks_list(csv_path):
    stocks = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            row = [c.strip() for c in row]
            if not row or not row[0]:
                continue
            code = row[0]
            name = row[1] if len(row) >= 2 else code
            stocks.append({"code": code, "name": name})
    return stocks


def _get_field(df, *keys):
    """DataFrame の index から複数候補キーを順に試す。最初にヒットした行の最初の値を返す。"""
    for k in keys:
        if k in df.index:
            val = df.loc[k].iloc[0]
            return safe_float(val)
    return None


def _get_row(df, *keys):
    """DataFrame から候補キーの行全体を返す (safe_float 変換済みリスト)。"""
    for k in keys:
        if k in df.index:
            return [safe_float(v) for v in df.loc[k].tolist()[:4]]
    return []


def fetch_stock_data(code):
    ticker = yf.Ticker(code)
    info = ticker.info

    price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    if price is None:
        raise ValueError(f"price が取得できません: {code}")

    prev_close = safe_float(
        info.get("previousClose") or info.get("regularMarketPreviousClose")
    )
    day_change = (
        round((price - prev_close) / prev_close * 100, 2)
        if prev_close
        else None
    )

    # yfinance 1.x は dividendYield をすでに % で返す（例: 2.16 = 2.16%）
    dy_raw = info.get("dividendYield")
    if dy_raw is not None:
        dy_val = float(dy_raw)
        # 旧版（< 1.0）は小数で返していたため、0.2 未満なら × 100 に補正
        dividend_yield = round(dy_val if dy_val >= 0.2 else dy_val * 100, 2)
    else:
        dividend_yield = None

    annual_dividend = safe_float(info.get("dividendRate") or info.get("trailingAnnualDividendRate"))
    sector = info.get("sector", "") or ""
    market_cap = info.get("marketCap")

    per = safe_float(info.get("trailingPE"))
    pbr = safe_float(info.get("priceToBook"))
    operating_margin = safe_float(info.get("operatingMargins"), 100)
    payout_ratio = safe_float(info.get("payoutRatio"), 100)
    roe = safe_float(info.get("returnOnEquity"), 100)

    # ── Balance Sheet ─────────────────────────────────────────────
    equity_ratio = None
    cash_trend = []
    try:
        bs = ticker.balance_sheet
        if bs is not None and not bs.empty:
            ta = _get_field(
                bs,
                "Total Assets",
                "TotalAssets",
            )
            se = _get_field(
                bs,
                "Stockholders Equity",
                "Total Stockholder Equity",
                "CommonStockEquity",
                "Stockholders' Equity",
            )
            if ta and se and ta != 0:
                equity_ratio = round(float(se) / float(ta) * 100, 2)

            cash_trend = _get_row(
                bs,
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "CashAndCashEquivalents",
                "Cash",
            )
            cash_trend = [v for v in cash_trend if v is not None]
    except Exception:
        pass

    # ── Cash Flow ─────────────────────────────────────────────────
    operating_cf = None
    try:
        cf = ticker.cashflow
        if cf is not None and not cf.empty:
            operating_cf = _get_field(
                cf,
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "OperatingCashFlow",
            )
    except Exception:
        pass

    # ── Income Statement ──────────────────────────────────────────
    revenue_trend = []
    eps_trend = []
    try:
        fin = ticker.financials
        if fin is not None and not fin.empty:
            revenue_trend = _get_row(fin, "Total Revenue", "TotalRevenue")
            revenue_trend = [v for v in revenue_trend if v is not None]
            eps_trend = _get_row(fin, "Basic EPS", "Diluted EPS", "BasicEPS")
            eps_trend = [v for v in eps_trend if v is not None]
    except Exception:
        pass

    # ── Technical ─────────────────────────────────────────────────
    week52_high = safe_float(info.get("fiftyTwoWeekHigh"))
    week52_low = safe_float(info.get("fiftyTwoWeekLow"))
    ma25 = None
    ma75 = None
    try:
        hist = ticker.history(period="4mo")
        if hist is not None and len(hist) >= 25:
            ma25 = round(float(hist["Close"].tail(25).mean()), 2)
        if hist is not None and len(hist) >= 75:
            ma75 = round(float(hist["Close"].tail(75).mean()), 2)
    except Exception:
        pass

    # ── Dividend History ──────────────────────────────────────────
    div_history = []
    try:
        divs = ticker.dividends
        if divs is not None and not divs.empty:
            for dt, amount in divs.tail(12).items():
                div_history.append({
                    "date": str(dt.date()),
                    "amount": round(float(amount), 4),
                })
    except Exception:
        pass

    return {
        "code": code,
        "name": info.get("longName", code),
        "sector": sector,
        "price": price,
        "prev_close": prev_close,
        "day_change": day_change,
        "dividend_yield": dividend_yield,
        "annual_dividend": annual_dividend,
        "market_cap": market_cap,
        "per": per,
        "pbr": pbr,
        "operating_margin": operating_margin,
        "payout_ratio": payout_ratio,
        "roe": roe,
        "equity_ratio": equity_ratio,
        "operating_cf": operating_cf,
        "week52_high": week52_high,
        "week52_low": week52_low,
        "ma25": ma25,
        "ma75": ma75,
        "revenue_trend": revenue_trend,
        "eps_trend": eps_trend,
        "cash_trend": cash_trend,
        "div_history": div_history,
        "error": None,
    }


def fetch_vix():
    try:
        ticker = yf.Ticker("^VIX")
        info = ticker.info
        vix = info.get("regularMarketPrice") or info.get("currentPrice")
        return safe_float(vix)
    except Exception:
        return None


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "stocks_list.csv")
    json_path = os.path.join(base_dir, "data", "stocks.json")

    stocks_list = read_stocks_list(csv_path)
    print(f"銘柄数: {len(stocks_list)}")

    results = []
    for s in stocks_list:
        code = s["code"]
        print(f"  取得中: {code} ({s['name']}) ...", end=" ", flush=True)
        try:
            data = fetch_stock_data(code)
            results.append(data)
            print(f"OK  price={data['price']}  yield={data['dividend_yield']}%")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "code": code,
                "name": s["name"],
                "sector": "",
                "price": None,
                "prev_close": None,
                "day_change": None,
                "dividend_yield": None,
                "annual_dividend": None,
                "market_cap": None,
                "per": None,
                "pbr": None,
                "operating_margin": None,
                "payout_ratio": None,
                "roe": None,
                "equity_ratio": None,
                "operating_cf": None,
                "week52_high": None,
                "week52_low": None,
                "ma25": None,
                "ma75": None,
                "revenue_trend": [],
                "eps_trend": [],
                "cash_trend": [],
                "div_history": [],
                "error": str(e),
            })

    vix = fetch_vix()
    now_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    output = {
        "updated": now_utc,
        "vix": vix,
        "vix_updated": now_utc,
        "stocks": results,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n完了: {len(results)} 銘柄 → {json_path}")
    print(f"VIX: {vix}")


if __name__ == "__main__":
    main()
