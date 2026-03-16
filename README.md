# Swing

A **swing-trading screener** that scans a large universe of stocks (e.g. 3000) with **parallel processing**, scores them using technicals, fundamentals, SEC filings, and news, **detects breakouts** automatically, and ranks the **top swing trades of the day**. It does **not** place orders itself: it writes qualified setups to a **structured JSON file** (signals) with ticker, score, setup type, entry, stop loss, and target. A separate **execution engine** reads those signals and applies strict rules (market hours, position limits, capital, risk) before any order is sent to a broker. That keeps analysis and execution isolated so bugs or bad data in the screener cannot directly trigger trades.

---

## Project goal

- **Scan at scale** — Use a ticker file (e.g. 3000 symbols) or the config watchlist; history is downloaded in chunks and each symbol is evaluated in parallel.
- **Detect breakouts** — Technically: price at or above the N-day high with volume confirmation; RSI in range; trend (SMA 20 &gt; 50). Setups are classified as `breakout` or `pullback`.
- **Rank and qualify** — Each ticker gets a total score (0–100). Only those above a minimum score become “opportunities” with **trade parameters**: entry, stop loss, target.
- **Structured output** — Results are written to **signals JSON** (path in config), not just logged. The file includes `generated_at`, and for each opportunity: `ticker`, `score`, `setup_type`, `entry`, `stop_loss`, `target`, plus technical/fundamental detail.
- **Execution is separate** — An **execution engine** reads the signals file, checks market hours, position limits, available capital, risk per trade, and whether the symbol is already held. Only then does it call a broker API (you implement the broker adapter). This prevents analysis bugs from directly moving money and makes the flow auditable and scalable.

---

## How to make money from it

1. **Run the screener** — Use a 3000-ticker file (see below) or a smaller watchlist. Set `loop_seconds` (e.g. 300) or `0` for a single “top of day” run. The screener writes the best setups to `signals.json`.
2. **Use the signals as a watchlist** — Open the JSON; trade only names you’re comfortable with. Entry/stop/target are suggestions; you can override with your own rules.
3. **Optionally automate execution** — Run the execution engine (e.g. after market open). It validates each opportunity against your risk and capital rules and, if you’ve wired a broker, can place orders. By default it runs in **dry-run** (log only).
4. **Tune config** — Adjust `signals.min_score`, ATR multiples, and execution limits so the written opportunities and any auto-execution match your style and risk.

---

## Setup

1. **Python** — 3.8+ and a virtualenv recommended.

2. **Dependencies**
   ```bash
   pip install pandas requests yfinance
   ```

3. **SEC User-Agent** — Set in `config.json` or env:
   ```json
   "sec_user_agent": "YourName YourApp contact@example.com"
   ```
   Or: `export SEC_USER_AGENT="..."`

4. **Config** — Key sections:
   - **Tickers** — `tickers`: list for a small watchlist. For ~3000 stocks, set `ticker_file` to a path (one symbol per line). Use the script below to generate that file from SEC.
   - **Market** — `market.history_period`, `history_interval`, `market.download_chunk_size` (e.g. 200) for chunked downloads.
   - **Parallel** — `parallel.max_workers` (e.g. 8).
   - **Output** — `output.top_n` (log lines), `output.signals_path` (e.g. `signals.json`).
   - **Signals** — `signals.min_score`, `max_opportunities`, `atr_multiple_stop`, `atr_multiple_target`, `stop_below_recent_low_pct`.
   - **Execution** — `execution.market_hours`, `max_positions`, `available_capital`, `max_capital_per_trade_pct`, `max_risk_per_trade_pct`.

---

## Getting a 3000-ticker file

Export SEC tickers to a text file (one per line), then optionally trim to 3000:

```bash
# From repo root; requires SEC_USER_AGENT or set in script
export SEC_USER_AGENT="YourName YourApp contact@example.com"
python scripts/export_sec_tickers.py

# Optional: limit to first 3000 and custom path
TICKER_LIMIT=3000 TICKER_OUTPUT=./tickers_3k.txt python scripts/export_sec_tickers.py
```

Then in `config.json` set `"ticker_file": "tickers_3k.txt"` (or the path you used). If `ticker_file` is set, it overrides `tickers`.

---

## Run

**Screener (analysis only; writes signals):**

```bash
python -m swing_bot.main
```

- Uses `ticker_file` if set, else `tickers`.
- Downloads history in chunks, evaluates in parallel, ranks, builds opportunities with entry/stop/target, and writes `output.signals_path` (e.g. `signals.json`).
- Set `loop_seconds` to `0` (or omit/negative) for a single run (e.g. “top swing trades of the day”).

**Execution engine (read signals → apply rules → optional broker):**

```bash
# Dry run (default): no orders, only validation and logs
python -m swing_bot.execution_engine

# Custom signals file
python -m swing_bot.execution_engine --signals path/to/signals.json

# Intended for live orders (only if you implement the broker)
python -m swing_bot.execution_engine --no-dry-run
```

The engine loads the latest signals, checks market hours, position limits, capital, risk per trade, and whether the symbol is already held. It then calls the broker interface (default is a no-op/dry-run). Implement a subclass of `BrokerInterface` in `execution_engine.py` and use it in `run_engine()` to plug in your broker API.

---

## Signals JSON (structure)

Written by the screener; read by the execution engine.

```json
{
  "generated_at": "2026-03-16T18:30:00Z",
  "opportunities": [
    {
      "ticker": "AAPL",
      "score": 78.5,
      "setup_type": "breakout",
      "entry": 175.50,
      "stop_loss": 168.20,
      "target": 190.10,
      "technical_score": 80,
      "fundamental_score": 75,
      "news_score": 60,
      "admin_score": 50,
      "close": 175.50,
      "rsi": 55.2,
      "atr_pct": 1.8,
      "breakout": true,
      "revenue_growth_pct": 8.5,
      "net_income_growth_pct": 12.1
    }
  ]
}
```

---

## Execution engine: rules and broker

- **Rules** — Market hours (UTC), weekday, max open positions, “not already in position,” max capital per trade, max risk per trade. Share size is derived from risk (entry − stop_loss) and `max_risk_per_trade_pct` of `available_capital`.
- **Broker** — Replace or extend `BrokerInterface` in `execution_engine.py` with your broker’s API (e.g. Alpaca, Interactive Brokers). The engine only places an order when all checks pass and `dry_run` is False.

By keeping **analysis (screener)** and **execution (engine)** separate, you get:

- No direct path from a screener bug to a live order.
- One place to validate and enforce risk and capital rules.
- A clear, file-based signal feed that you can monitor, replay, or feed into other tools.
