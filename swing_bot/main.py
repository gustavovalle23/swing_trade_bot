import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from config_loader import load_config, load_tickers
from logger import get_logger
from market_data import download_history, fetch_news
from sec_data import SecClient
from technicals import build_technical_snapshot
from fundamentals import build_fundamental_snapshot
from scoring import build_ranked_rows
from signals import build_opportunities


def _evaluate_one(ticker, prices, config):
    """Evaluate one ticker; returns row dict or None. Creates its own SEC client for thread safety."""
    if prices is None or prices.empty:
        return None
    sec = SecClient(config["sec_user_agent"])
    technical = build_technical_snapshot(prices, config["technical"])
    fundamentals = build_fundamental_snapshot(sec, ticker, config["fundamental"])
    news = fetch_news(ticker, config["news"]["headline_limit"])
    return {
        "ticker": ticker,
        "technical": technical,
        "fundamental": fundamentals,
        "news": news,
    }


def run():
    config = load_config()
    log = get_logger()
    tickers = load_tickers(config)
    download_chunk = config.get("market", {}).get("download_chunk_size", 200)
    max_workers = config.get("parallel", {}).get("max_workers", 8)
    signals_path = config.get("output", {}).get("signals_path", "signals.json")

    log.info(
        "Swing screener starting | tickers=%d | chunk=%d | workers=%d | loop_seconds=%s",
        len(tickers),
        download_chunk,
        max_workers,
        config.get("loop_seconds"),
    )

    while True:
        log.info("--- Run starting ---")
        log.info(
            "Downloading history | period=%s interval=%s (chunked by %d)",
            config["market"]["history_period"],
            config["market"]["history_interval"],
            download_chunk,
        )
        history = download_history(
            tickers=tickers,
            period=config["market"]["history_period"],
            interval=config["market"]["history_interval"],
            chunk_size=download_chunk,
        )
        fetched = [t for t in tickers if history.get(t) is not None and not history.get(t).empty]
        if len(fetched) < len(tickers):
            skipped_count = len(tickers) - len(fetched)
            log.warning("Skipped %d tickers (no history)", skipped_count)
        log.info("Testing %d opportunities in parallel (workers=%d)", len(fetched), max_workers)

        rows = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(
                    _evaluate_one,
                    ticker,
                    history.get(ticker),
                    config,
                ): ticker
                for ticker in fetched
            }
            done = 0
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                done += 1
                if done % 500 == 0 or done <= 10:
                    log.info("  Evaluated %d / %d ...", done, len(fetched))
                try:
                    row = future.result()
                    if row is not None:
                        rows.append(row)
                except Exception as e:
                    log.warning("  %s failed: %s", ticker, e)

        log.info("Ranked %d opportunities", len(rows))
        ranked = build_ranked_rows(rows, config)
        opportunities = build_opportunities(ranked, config)
        opportunities.sort(key=lambda o: o["score"], reverse=True)
        log.info("Qualified setups: %d (written to %s, ordered by score)", len(opportunities), signals_path)

        out_payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "opportunities": opportunities,
        }
        out_dir = os.path.dirname(signals_path)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(signals_path, "w", encoding="utf-8") as f:
            json.dump(out_payload, f, indent=2)

        top_n = config.get("output", {}).get("top_n", 10)
        log.info("--- Top %d ideas ---", top_n)
        for i, row in enumerate(ranked[:top_n], 1):
            log.info(
                "  #%d %s total=%.2f %s (tech=%.1f fund=%.1f) close=%.2f rsi=%s",
                i,
                row["ticker"],
                row["total_score"],
                "breakout" if row["breakout"] else "pullback",
                row["technical_score"],
                row["fundamental_score"],
                row["close"],
                row["rsi"],
            )

        loop_seconds = config.get("loop_seconds")
        if loop_seconds is None or loop_seconds <= 0:
            log.info("Single run (loop_seconds=%s); exiting.", loop_seconds)
            break
        log.info("Sleeping %s seconds until next run", loop_seconds)
        time.sleep(loop_seconds)


if __name__ == "__main__":
    run()
