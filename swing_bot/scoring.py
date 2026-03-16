POSITIVE = {
    "beat",
    "beats",
    "upgrade",
    "upgrades",
    "buyback",
    "raises",
    "growth",
    "record",
    "strong",
    "surge",
    "breakout",
    "expands",
}
NEGATIVE = {
    "miss",
    "misses",
    "downgrade",
    "downgrades",
    "lawsuit",
    "probe",
    "fraud",
    "cuts",
    "cut",
    "weak",
    "falls",
    "drop",
    "decline",
}


def sentiment_score(news):
    if not news:
        return 50.0
    score = 0
    for item in news:
        title = item.get("title", "").lower()
        pos = sum(1 for word in POSITIVE if word in title)
        neg = sum(1 for word in NEGATIVE if word in title)
        score += pos - neg
    normalized = 50 + (score * 10)
    return max(0.0, min(100.0, float(normalized)))


def admin_score(fundamental):
    forms = fundamental.get("recent_forms", {})
    form4 = forms.get("4", 0)
    form8k = forms.get("8-K", 0)
    raw = 50 + min(form4 * 5, 20) - min(form8k * 3, 20)
    return max(0.0, min(100.0, float(raw)))


def build_ranked_rows(rows, config):
    weights = config["weights"]
    out = []
    for row in rows:
        tech = row["technical"]["score"]
        fund = row["fundamental"]["score"]
        news = sentiment_score(row["news"])
        admin = admin_score(row["fundamental"])
        total = (
            tech * weights["technical"]
            + fund * weights["fundamental"]
            + news * weights["news"]
            + admin * weights["admin"]
        )
        out.append(
            {
                "ticker": row["ticker"],
                "total_score": round(total, 2),
                "technical_score": tech,
                "fundamental_score": fund,
                "news_score": round(news, 2),
                "admin_score": round(admin, 2),
                "close": row["technical"]["close"],
                "rsi": row["technical"]["rsi"],
                "atr_pct": row["technical"]["atr_pct"],
                "breakout": row["technical"]["breakout"],
                "revenue_growth_pct": row["fundamental"]["revenue_growth_pct"],
                "net_income_growth_pct": row["fundamental"]["net_income_growth_pct"],
                "debt_to_assets": row["fundamental"]["debt_to_assets"],
                "current_ratio": row["fundamental"]["current_ratio"],
                "recent_forms": row["fundamental"]["recent_forms"],
                "headline_count": len(row["news"]),
            }
        )
    out.sort(key=lambda x: x["total_score"], reverse=True)
    return out