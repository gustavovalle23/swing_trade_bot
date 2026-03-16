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

    log.info("Swing screener starting | tickers=%s | loop_seconds=%s", tickers, config["loop_seconds"])

    while True:
        log.info("--- Run starting ---")
        log.info("Downloading history | period=%s interval=%s", config["market"]["history_period"], config["market"]["history_interval"])
        history = download_history(
            tickers=tickers,
            period=config["market"]["history_period"],
            interval=config["market"]["history_interval"],
        )
        fetched = [t for t in tickers if history.get(t) is not None and not history.get(t).empty]
        if len(fetched) < len(tickers):
            skipped = [t for t in tickers if t not in fetched]
            log.warning("Skipped (no history): %s", skipped)
        log.info("Testing opportunities: %s", fetched)

        rows = []
        for ticker in tickers:
            prices = history.get(ticker)
            if prices is None or prices.empty:
                continue
            log.info("  Evaluating %s ...", ticker)
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
            log.info(
                "    %s tech=%.1f fund=%.1f news_count=%d",
                ticker,
                technical["score"],
                fundamentals["score"],
                len(news),
            )

        ranked = build_ranked_rows(rows, config)
        log.info("Ranked %d opportunities", len(ranked))

        top_n = config["output"]["top_n"]
        log.info("--- Top %d ideas ---", top_n)
        for i, row in enumerate(ranked[:top_n], 1):
            log.info(
                "  #%d %s total=%.2f (tech=%.1f fund=%.1f news=%.1f admin=%.1f) close=%.2f rsi=%s",
                i,
                row["ticker"],
                row["total_score"],
                row["technical_score"],
                row["fundamental_score"],
                row["news_score"],
                row["admin_score"],
                row["close"],
                row["rsi"],
            )
        log.info("Sleeping %s seconds until next run", config["loop_seconds"])
        time.sleep(config["loop_seconds"])


if __name__ == "__main__":
    run()