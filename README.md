# Swing

A **swing-trading idea screener** that ranks a watchlist of stocks using technicals, fundamentals, SEC filings, and news sentiment. It runs in a loop and logs the top ideas so you can focus on the best candidates instead of scanning everything by hand.

## Project goal

Swing helps you **find and rank swing-trade ideas** by:

- **Technicals** — Trend (SMA 20/50), RSI in a healthy range, breakouts, volume confirmation, and volatility (ATR)
- **Fundamentals** — Revenue and net income growth, debt-to-assets, current ratio, and recent 10-Q/10-K from SEC data
- **News** — Simple sentiment from headline keywords (e.g. “upgrade”, “surge” vs “downgrade”, “cuts”)
- **Admin** — Recent SEC activity: Form 4 (insider buying) and 8-K (material events) to tilt the score

Each ticker gets a **total score** (0–100) from weighted subscores. The bot prints the top N ideas every loop so you can decide what to trade.

**What it is not:** It does not place trades or manage risk. It is a **research and screening tool** — you still choose entries, size, and exits.

---

## How to make money from it

1. **Use the top ideas as your watchlist**  
   Run the bot (e.g. every 5 minutes via `loop_seconds`). The ranked output is a short list of names that pass your technical, fundamental, and news filters. Treat these as **candidates**, not automatic buys.

2. **Swing trade the high scorers**  
   When a name stays near the top and the setup fits your style:
   - **Breakout style:** Enter when price breaks above the lookback high with volume; use ATR or a fixed stop.
   - **Pullback style:** Wait for a dip in an uptrend (e.g. toward the fast SMA or in a healthy RSI zone), then enter with a stop below the swing low.

3. **Use the metrics for timing and risk**  
   The log includes RSI, ATR%, breakout flag, and fundamental stats. Use them to:
   - Avoid overbought entries (e.g. RSI &gt; 70) or confirm strength (RSI in your preferred range).
   - Size and place stops using ATR% so volatility is reflected in position risk.
   - Prefer names with strong revenue/income growth and reasonable debt if you care about fundamentals.

4. **Combine with your own rules**  
   Add filters you care about (e.g. sector, market cap, earnings dates). Use the score as one input; your rules for entry, size, and exit are what actually drive P&amp;L.

5. **Tune the config**  
   Adjust `config.json`: tickers, technical/fundamental thresholds, and score weights so the top ideas match the kind of swings you want (e.g. more growth vs more value, more breakout vs more trend-following).

**Summary:** The bot surfaces **ranked swing ideas**; you make money by trading those ideas with clear entries, position sizing, and stops — not by running it on autopilot.

---

## Setup

1. **Python**  
   Use Python 3.8+ and a virtualenv if you like.

2. **Dependencies**  
   From the project root:
   ```bash
   pip install pandas requests yfinance
   ```

3. **SEC API**  
   The SEC asks for a descriptive User-Agent. Set it in `config.json`:
   ```json
   "sec_user_agent": "YourName YourApp contact@example.com"
   ```

4. **Config**  
   Edit `config.json`:
   - `tickers` — Symbols to screen (default: AAPL, MSFT, NVDA, etc.).
   - `loop_seconds` — How often to re-run (e.g. 300 = every 5 minutes).
   - `market`, `technical`, `fundamental`, `news` — Periods, thresholds, and limits.
   - `weights` — technical / fundamental / news / admin (default 0.4 / 0.35 / 0.15 / 0.1).
   - `output.top_n` — Number of top ideas to log each run.

---

## Run

From the project root:

```bash
python -m swing_bot.main
```

The process runs until you stop it. Each loop it downloads history (yfinance), pulls SEC data and news, scores every ticker, and logs the top N ideas with scores and key metrics.

---

## Output

Each run logs the top ideas with:

- `ticker`, `total_score`
- `technical_score`, `fundamental_score`, `news_score`, `admin_score`
- `close`, `rsi`, `atr_pct`, `breakout`
- `revenue_growth_pct`, `net_income_growth_pct`, `debt_to_assets`, `current_ratio`
- `recent_forms` (e.g. 10-Q, 10-K, 4, 8-K), `headline_count`

Use these to pick and manage swing trades with your own entry/exit and risk rules.
