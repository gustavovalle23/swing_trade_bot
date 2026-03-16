"""
Execution engine: reads signals from JSON, applies strict trading rules,
then places orders via a broker API. Isolated from the analysis layer so
bugs or bad data do not directly trigger trades.
"""

import json
import os
from datetime import datetime, timezone

from logger import get_logger


def _utcnow():
    return datetime.now(timezone.utc)


def is_market_hours(config):
    """True if within configured market hours (UTC)."""
    hours = config.get("execution", {}).get("market_hours", {})
    if not hours:
        return True
    t = _utcnow().time()
    start = hours.get("start_utc", "14:30")  # 9:30 ET
    end = hours.get("end_utc", "21:00")     # 16:00 ET
    # Parse "HH:MM"
    def to_minutes(s):
        h, m = s.split(":")[:2]
        return int(h) * 60 + int(m)
    now_m = t.hour * 60 + t.minute
    return to_minutes(start) <= now_m <= to_minutes(end)


def is_weekday(config):
    """True if today is a weekday (config can override)."""
    return _utcnow().weekday() < 5  # Mon=0 .. Fri=4


def load_signals(path):
    """Load opportunities from signals JSON. Returns payload or None."""
    if not path or not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class ExecutionRules:
    """Checks that must pass before placing an order."""

    def __init__(self, config):
        self.config = config
        self.exec_cfg = config.get("execution", {})
        self.max_positions = self.exec_cfg.get("max_positions", 10)
        self.max_capital_per_trade_pct = self.exec_cfg.get("max_capital_per_trade_pct", 10.0) / 100.0
        self.max_risk_per_trade_pct = self.exec_cfg.get("max_risk_per_trade_pct", 1.0) / 100.0
        self.available_capital = self.exec_cfg.get("available_capital", 0.0)
        self.current_positions = set()  # tickers; in production load from broker
        self.positions_value = {}       # ticker -> notional; in production from broker

    def check_market_hours(self):
        if not is_market_hours(self.config):
            return False, "outside market hours"
        if not is_weekday(self.config):
            return False, "weekend"
        return True, None

    def check_position_limit(self):
        if len(self.current_positions) >= self.max_positions:
            return False, f"max positions ({self.max_positions}) reached"
        return True, None

    def check_already_held(self, ticker):
        if ticker.upper() in self.current_positions:
            return False, "already in position"
        return True, None

    def check_capital(self, entry, stop_loss, shares):
        if self.available_capital <= 0:
            return False, "no available capital configured"
        notional = entry * shares
        max_notional = self.available_capital * self.max_capital_per_trade_pct
        if notional > max_notional:
            return False, f"notional {notional:.0f} > max per trade {max_notional:.0f}"
        return True, None

    def check_risk_per_trade(self, entry, stop_loss, shares):
        risk_dollars = (entry - stop_loss) * shares
        max_risk = self.available_capital * self.max_risk_per_trade_pct
        if risk_dollars > max_risk:
            return False, f"risk {risk_dollars:.0f} > max risk per trade {max_risk:.0f}"
        return True, None

    def run_all_checks(self, opportunity, shares):
        ticker = opportunity["ticker"]
        entry = opportunity["entry"]
        stop_loss = opportunity["stop_loss"]

        ok, msg = self.check_market_hours()
        if not ok:
            return False, msg
        ok, msg = self.check_position_limit()
        if not ok:
            return False, msg
        ok, msg = self.check_already_held(ticker)
        if not ok:
            return False, msg
        ok, msg = self.check_capital(entry, stop_loss, shares)
        if not ok:
            return False, msg
        ok, msg = self.check_risk_per_trade(entry, stop_loss, shares)
        if not ok:
            return False, msg
        return True, None


class BrokerInterface:
    """Abstract broker: implement place_order for your broker API."""

    def place_order(self, opportunity, shares, dry_run=True):
        """
        Place a single order. Override in subclass.
        opportunity: dict with ticker, entry, stop_loss, target, setup_type
        shares: int
        dry_run: if True, log only and do not send to broker
        Returns (success: bool, message: str)
        """
        if dry_run:
            return True, f"dry_run: would buy {shares} {opportunity['ticker']} @ {opportunity['entry']}"
        return False, "no broker configured"


def compute_shares(opportunity, available_capital, max_risk_pct):
    """Compute share size from risk: risk_per_share = entry - stop_loss; size so risk = capital * max_risk_pct."""
    entry = opportunity["entry"]
    stop = opportunity["stop_loss"]
    if entry <= stop:
        return 0
    risk_per_share = entry - stop
    risk_dollars = available_capital * max_risk_pct
    return max(0, int(risk_dollars / risk_per_share))


def run_engine(config_path=None, signals_path=None, dry_run=True):
    """
    Load config and signals, apply rules, and optionally place orders.
    dry_run=True: only validate and log; do not call broker.
    """
    from config_loader import load_config
    config = load_config() if config_path is None else _load_config_path(config_path)
    path = signals_path or config.get("output", {}).get("signals_path", "signals.json")
    log = get_logger()

    payload = load_signals(path)
    if not payload:
        log.warning("No signals file at %s; nothing to execute.", path)
        return
    opportunities = payload.get("opportunities", [])
    generated = payload.get("generated_at", "")
    log.info("Loaded %d opportunities from %s (generated %s)", len(opportunities), path, generated)

    rules = ExecutionRules(config)
    broker = BrokerInterface()

    for opp in opportunities:
        ticker = opp["ticker"]
        shares = compute_shares(
            opp,
            rules.available_capital,
            rules.max_risk_per_trade_pct,
        )
        if shares <= 0:
            log.info("Skip %s: zero shares from risk sizing", ticker)
            continue
        ok, msg = rules.run_all_checks(opp, shares)
        if not ok:
            log.info("Skip %s: %s", ticker, msg)
            continue
        success, result = broker.place_order(opp, shares, dry_run=dry_run)
        if success:
            log.info("Order %s: %s", ticker, result)
            rules.current_positions.add(ticker.upper())
        else:
            log.warning("Order %s failed: %s", ticker, result)


def _load_config_path(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Execution engine: read signals, apply rules, place orders")
    parser.add_argument("--signals", default=None, help="Path to signals.json")
    parser.add_argument("--no-dry-run", action="store_true", help="Actually place orders (if broker implemented)")
    args = parser.parse_args()
    run_engine(signals_path=args.signals, dry_run=not args.no_dry_run)
