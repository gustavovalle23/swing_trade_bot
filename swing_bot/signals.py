"""
Builds qualified swing setups from ranked rows and defines trade parameters:
ticker, score, setup_type, entry, stop_loss, target. Only rows that meet
min_score and setup criteria are emitted as opportunities.
"""


def _trade_params(row, cfg):
    """Compute entry, stop_loss, target from technicals and config."""
    close = row["close"]
    atr_abs = row.get("atr_abs")
    recent_high = row.get("recent_high") or close
    recent_low = row.get("recent_low") or close

    atr_stop = cfg.get("atr_multiple_stop", 1.5)
    atr_target = cfg.get("atr_multiple_target", 3.0)
    stop_below_low_pct = cfg.get("stop_below_recent_low_pct", 0.005)  # 0.5% below recent low

    if row["breakout"]:
        setup_type = "breakout"
        entry = round(close, 2)
        # Stop: below recent low (with buffer) or entry - ATR, whichever is tighter
        stop_from_low = recent_low * (1 - stop_below_low_pct)
        stop_from_atr = (entry - atr_stop * atr_abs) if atr_abs else stop_from_low
        stop_loss = round(min(stop_from_low, stop_from_atr), 2)
        target = round(entry + (atr_target * atr_abs) if atr_abs else entry * 1.05, 2)
    else:
        setup_type = "pullback"
        entry = round(close, 2)
        stop_from_low = recent_low * (1 - stop_below_low_pct)
        stop_from_atr = (entry - atr_stop * atr_abs) if atr_abs else stop_from_low
        stop_loss = round(min(stop_from_low, stop_from_atr), 2)
        target = round(entry + (atr_target * atr_abs) if atr_abs else entry * 1.05, 2)

    return {
        "setup_type": setup_type,
        "entry": entry,
        "stop_loss": round(stop_loss, 2),
        "target": round(target, 2),
    }


def build_opportunities(ranked_rows, config):
    """
    From ranked rows, keep only those that qualify as setups and attach
    trade parameters. Returns list of opportunity dicts for JSON output.
    """
    sig_cfg = config.get("signals", {})
    min_score = sig_cfg.get("min_score", 50.0)
    max_opportunities = sig_cfg.get("max_opportunities", 50)

    opportunities = []
    for row in ranked_rows:
        if row["total_score"] < min_score:
            continue
        params = _trade_params(row, sig_cfg)

        iv = row.get("intrinsic_value")
        close = row["close"]
        margin_of_safety_pct = None
        price_iv_ratio = None
        price_iv_warning = False
        if iv is not None and iv > 0 and close is not None and close > 0:
            margin_of_safety_pct = round((iv - close) / iv * 100, 2)
            price_iv_ratio = round(close / iv, 2)
            if price_iv_ratio > 3.0 or price_iv_ratio < 0.33:
                price_iv_warning = True

        opp = {
            "ticker": row["ticker"],
            "score": row["total_score"],
            "setup_type": params["setup_type"],
            "entry": params["entry"],
            "stop_loss": params["stop_loss"],
            "target": params["target"],
            "technical_score": row["technical_score"],
            "fundamental_score": row["fundamental_score"],
            "news_score": row["news_score"],
            "admin_score": row["admin_score"],
            "close": row["close"],
            "rsi": row["rsi"],
            "atr_pct": row["atr_pct"],
            "breakout": row["breakout"],
            "revenue_growth_pct": row.get("revenue_growth_pct"),
            "net_income_growth_pct": row.get("net_income_growth_pct"),
            "eps": row.get("eps"),
            "intrinsic_value": iv,
            "margin_of_safety_pct": margin_of_safety_pct,
            "price_iv_ratio": price_iv_ratio,
            "price_iv_warning": price_iv_warning,
        }
        opportunities.append(opp)
        if len(opportunities) >= max_opportunities:
            break

    return opportunities
