import json
import os


def load_config():
    path = os.getenv("SWING_CONFIG_PATH", "config.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["sec_user_agent"] = (
        os.getenv("SEC_USER_AGENT", "").strip() or data.get("sec_user_agent", "")
    ).strip()
    if not data["sec_user_agent"]:
        raise ValueError("SEC_USER_AGENT or config sec_user_agent is required")
    return data


def load_tickers(config):
    """Resolve ticker list: ticker_file (one per line) or config tickers."""
    path = config.get("ticker_file") or os.getenv("SWING_TICKER_FILE")
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            tickers = [line.strip().upper() for line in f if line.strip()]
        return tickers
    return [t.upper() for t in config.get("tickers", [])]
