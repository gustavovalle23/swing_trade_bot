"""
Export SEC company tickers to a text file (one per line) for use as ticker_file.
Use this to build a ~3000+ stock universe. Optional: filter by exchange or take first N.
"""

import os
import requests

USER_AGENT = os.getenv("SEC_USER_AGENT", "SwingBot contact@example.com")
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "tickers_sec.txt")
URL = "https://www.sec.gov/files/company_tickers.json"


def main():
    limit = int(os.getenv("TICKER_LIMIT", "0"))
    r = requests.get(URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    data = r.json()
    tickers = sorted({str(v["ticker"]).strip().upper() for v in data.values() if v.get("ticker")})
    if limit > 0:
        tickers = tickers[:limit]
    out_path = os.getenv("TICKER_OUTPUT", OUTPUT)
    with open(out_path, "w", encoding="utf-8") as f:
        for t in tickers:
            f.write(t + "\n")
    print(f"Wrote {len(tickers)} tickers to {out_path}")


if __name__ == "__main__":
    main()
