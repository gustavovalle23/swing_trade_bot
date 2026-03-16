import time
from config_loader import load_config
from logger import get_logger
from market_data import download_history, fetch_news
from sec_data import SecClient
from technicals import build_technical_snapshot
from fundamentals import build_fundamental_snapshot
from scoring import build_ranked_rows


def run():
    config = load_config()
    log = get_logger()
    sec = SecClient(config["sec_user_agent"])
    tickers = config["tickers"]
    while True:
        history = download_history(
            tickers=tickers,
            period=config["market"]["history_period"],
            interval=config["market"]["history_interval"],
        )
        rows = []
        for ticker in tickers:
            prices = history.get(ticker)
            if prices is None or prices.empty:
                continue
            technical = build_technical_snapshot(prices, config["technical"])
            fundamentals = build_fundamental_snapshot(sec, ticker, config["fundamental"])
            news = fetch_news(ticker, config["news"]["headline_limit"])
            rows.append(
                {
                    "ticker": ticker,
                    "technical": technical,
                    "fundamental": fundamentals,
                    "news": news,
                }
            )
        ranked = build_ranked_rows(rows, config)
        log.info("top ideas")
        for row in ranked[: config["output"]["top_n"]]:
            log.info(row)
        time.sleep(config["loop_seconds"])


if __name__ == "__main__":
    run()