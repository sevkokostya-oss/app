"""
LangChain tools for the Investment Idea Analyzer.

Financial data: yfinance (free).
News: SerpAPI if SERPAPI_API_KEY is set, otherwise yfinance news (free).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf
from langchain_core.tools import tool

# Optional SerpAPI — only used when key is present
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None  # type: ignore[misc, assignment]


def _get_secret(key: str) -> str | None:
    """Read non-empty key from Streamlit secrets or environment."""
    val: str | None = None
    try:
        import streamlit as st

        if key in st.secrets:
            val = str(st.secrets[key])
    except Exception:
        pass
    if not val:
        val = os.getenv(key)
    if val and str(val).strip():
        return str(val).strip().strip('"').strip("'")
    return None


def calculate_cagr(values: list[float | int]) -> float | None:
    """
    Compound annual growth rate for a series of annual values.
    values: oldest -> newest (at least 2 points).
    """
    if not values or len(values) < 2:
        return None
    clean = [float(v) for v in values if v is not None and pd.notna(v)]
    if len(clean) < 2 or clean[0] <= 0:
        return None
    n_years = len(clean) - 1
    if n_years <= 0:
        return None
    return (clean[-1] / clean[0]) ** (1 / n_years) - 1


def _resolve_ticker(query: str) -> tuple[str | None, str | None]:
    """
    Resolve user input to a Yahoo Finance ticker.
    Returns (ticker, error_message).
    """
    raw = (query or "").strip().upper()
    if not raw:
        return None, "Введите тикер или название компании."

    # Direct ticker guess (letters, optional dot for BRK.B style)
    if len(raw) <= 6 and raw.replace(".", "").isalnum():
        t = yf.Ticker(raw)
        try:
            info = t.info
            if info and (info.get("symbol") or info.get("shortName")):
                return info.get("symbol", raw), None
        except Exception:
            pass

    # Search by name via yfinance
    try:
        import urllib.parse
        import urllib.request

        q = urllib.parse.quote(query.strip())
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=5"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        quotes = data.get("quotes") or []
        for item in quotes:
            sym = item.get("symbol")
            if sym and item.get("quoteType") in ("EQUITY", "ETF", None):
                return sym, None
        if quotes:
            return quotes[0].get("symbol"), None
    except Exception:
        pass

    return None, f"Тикер «{query}» не найден. Проверьте написание (например, AAPL, NVDA)."


def _revenue_cagr_3y(ticker: yf.Ticker) -> float | None:
    """3-year revenue CAGR from annual financials."""
    try:
        fin = ticker.financials
        if fin is None or fin.empty:
            fin = ticker.get_income_stmt(freq="yearly")
        if fin is None or fin.empty:
            return None
        row = None
        for name in ("Total Revenue", "TotalRevenue", "Revenue"):
            if name in fin.index:
                row = fin.loc[name]
                break
        if row is None:
            return None
        vals = [float(row.iloc[i]) for i in range(min(4, len(row))) if pd.notna(row.iloc[i])]
        vals = list(reversed(vals))  # oldest first
        if len(vals) < 2:
            return None
        return calculate_cagr(vals[-4:] if len(vals) >= 4 else vals)
    except Exception:
        return None


@tool
def get_stock_financials(ticker: str) -> str:
    """
    Download stock fundamentals via yfinance for the given ticker symbol.
    Returns JSON with price, P/E, P/B, market cap, dividend yield,
    3Y revenue CAGR, ROE, debt/equity, and related metrics.
    """
    sym, err = _resolve_ticker(ticker)
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)

    try:
        t = yf.Ticker(sym)
        info = t.info or {}
    except Exception as e:
        return json.dumps(
            {"error": f"Не удалось загрузить данные для {sym}: {e}"},
            ensure_ascii=False,
        )

    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        return json.dumps(
            {"error": f"Финансовые данные для «{sym}» недоступны."},
            ensure_ascii=False,
        )

    revenue_cagr = _revenue_cagr_3y(t)
    pe = info.get("trailingPE") or info.get("forwardPE")
    pb = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    if roe is not None and abs(roe) < 5:
        roe = roe * 100  # yfinance often returns decimal

    debt_eq = info.get("debtToEquity")
    if debt_eq is not None and debt_eq > 10:
        debt_eq = debt_eq / 100  # sometimes scaled

    profit_margin = info.get("profitMargins")
    if profit_margin is not None and abs(profit_margin) < 2:
        profit_margin = profit_margin * 100

    payload: dict[str, Any] = {
        "ticker": sym,
        "company_name": info.get("longName") or info.get("shortName") or sym,
        "currency": info.get("currency", "USD"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": round(pe, 2) if pe is not None else None,
        "pb_ratio": round(pb, 2) if pb is not None else None,
        "dividend_yield_pct": (
            round((info.get("dividendYield") or 0) * 100, 2)
            if info.get("dividendYield")
            else None
        ),
        "revenue_growth_3y_cagr_pct": (
            round(revenue_cagr * 100, 2) if revenue_cagr is not None else None
        ),
        "roe_pct": round(roe, 2) if roe is not None else None,
        "debt_to_equity": round(debt_eq, 2) if debt_eq is not None else None,
        "profit_margin_pct": round(profit_margin, 2) if profit_margin is not None else None,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "beta": info.get("beta"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _search_news_serpapi(query: str, api_key: str) -> list[dict[str, str]]:
    """Google News via SerpAPI (free tier: ~100 searches/month)."""
    if GoogleSearch is None:
        return []
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": api_key,
        "gl": "us",
        "hl": "en",
    }
    results = GoogleSearch(params).get_dict()
    items = []
    for entry in (results.get("news_results") or [])[:5]:
        items.append(
            {
                "title": entry.get("title", ""),
                "snippet": entry.get("snippet") or entry.get("description", ""),
                "source": entry.get("source", {}).get("name")
                if isinstance(entry.get("source"), dict)
                else str(entry.get("source", "")),
                "date": entry.get("date", ""),
                "link": entry.get("link", ""),
            }
        )
    return items


def _search_news_yfinance(ticker: str) -> list[dict[str, str]]:
    """Free fallback: recent headlines from yfinance."""
    sym, err = _resolve_ticker(ticker)
    if err:
        return []
    try:
        t = yf.Ticker(sym)
        news = t.news or []
    except Exception:
        return []

    cutoff = datetime.utcnow() - timedelta(days=7)
    items = []
    for n in news[:15]:
        ts = n.get("providerPublishTime") or n.get("pubDate")
        date_str = ""
        if ts:
            try:
                dt = datetime.utcfromtimestamp(int(ts))
                if dt < cutoff:
                    continue
                date_str = dt.strftime("%Y-%m-%d")
            except (TypeError, ValueError, OSError):
                date_str = str(ts)
        items.append(
            {
                "title": n.get("title", ""),
                "snippet": n.get("summary", "")[:300],
                "source": n.get("publisher", "Yahoo Finance"),
                "date": date_str,
                "link": n.get("link", n.get("url", "")),
            }
        )
        if len(items) >= 5:
            break
    return items


@tool
def search_news(query: str) -> str:
    """
    Search recent stock news (last ~7 days).
    Query example: 'NVDA stock news last 7 days'.
    Returns JSON list of up to 5 articles with title, snippet, source, date, link.
    """
    api_key = _get_secret("SERPAPI_API_KEY")
    articles: list[dict[str, str]] = []
    source_note = ""

    if api_key and GoogleSearch is not None:
        try:
            articles = _search_news_serpapi(query, api_key)
            source_note = "serpapi_google_news"
        except Exception as e:
            source_note = f"serpapi_error: {e}"

    if not articles:
        # Extract likely ticker from query
        parts = query.upper().split()
        ticker_guess = parts[0] if parts else query
        articles = _search_news_yfinance(ticker_guess)
        source_note = "yfinance_news_free"

    if not articles:
        return json.dumps(
            {
                "articles": [],
                "message": "Новости за последнюю неделю не найдены. "
                "Добавьте SERPAPI_API_KEY (бесплатный лимит на serpapi.com) или проверьте тикер.",
                "source": source_note,
            },
            ensure_ascii=False,
            indent=2,
        )

    return json.dumps(
        {"articles": articles, "source": source_note, "count": len(articles)},
        ensure_ascii=False,
        indent=2,
    )


def get_all_tools() -> list:
    """Return LangChain tools for the agent."""
    return [get_stock_financials, search_news]
