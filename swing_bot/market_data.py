import pandas as pd
import yfinance as yf


def download_history(tickers, period, interval, chunk_size=None):
    """Download OHLCV for tickers. If chunk_size is set, download in chunks and merge (for large universes)."""
    if not chunk_size or len(tickers) <= chunk_size:
        return _download_one(tickers, period, interval)
    out = {}
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        out.update(_download_one(chunk, period, interval))
    return out


def _download_one(tickers, period, interval):
    data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    if isinstance(data.columns, pd.MultiIndex):
        return {
            ticker: data[ticker].dropna().copy()
            for ticker in tickers
            if ticker in data.columns.get_level_values(0)
        }
    if len(tickers) == 1:
        return {tickers[0]: data.dropna().copy()}
    return {}


def fetch_news(ticker, limit):
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        items = []
    rows = []
    for item in items[:limit]:
        rows.append(
            {
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "published": item.get("providerPublishTime"),
                "link": item.get("link", ""),
            }
        )
    return rows