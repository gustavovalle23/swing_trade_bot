import pandas as pd
import yfinance as yf


def download_history(tickers, period, interval):
    data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        auto_adjust=False,
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
    return {tickers[0]: data.dropna().copy()}


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