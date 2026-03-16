from datetime import datetime, timezone


USD_TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
}


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def extract_series(facts, tags):
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        node = us_gaap.get(tag, {})
        units = node.get("units", {})
        items = units.get("USD", [])
        if items:
            rows = []
            for item in items:
                end = item.get("end")
                val = item.get("val")
                form = item.get("form")
                if end and val is not None and form in {"10-K", "10-Q", "20-F", "6-K"}:
                    rows.append({"end": end, "val": float(val), "form": form})
            rows.sort(key=lambda x: x["end"])
            if rows:
                dedup = {}
                for row in rows:
                    dedup[row["end"]] = row
                return list(dedup.values())
    return []


def growth_from_last_two(series):
    if len(series) < 2:
        return None
    prev = series[-2]["val"]
    curr = series[-1]["val"]
    if prev == 0:
        return None
    return ((curr - prev) / abs(prev)) * 100


def recent_form_counts(submissions, days):
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    now = datetime.now(timezone.utc)
    out = {"8-K": 0, "10-Q": 0, "10-K": 0, "4": 0}
    for form, date_str in zip(forms, dates):
        age = (now - parse_date(date_str)).days
        if age <= days and form in out:
            out[form] += 1
    return out


def build_fundamental_snapshot(sec, ticker, cfg):
    cik = sec.cik_for(ticker)
    if not cik:
        return {
            "score": 0,
            "cik": None,
            "revenue_growth_pct": None,
            "net_income_growth_pct": None,
            "debt_to_assets": None,
            "current_ratio": None,
            "recent_forms": {},
        }

    facts = sec.companyfacts(cik)
    submissions = sec.submissions(cik)

    revenue = extract_series(facts, USD_TAGS["revenue"])
    net_income = extract_series(facts, USD_TAGS["net_income"])
    assets = extract_series(facts, USD_TAGS["assets"])
    liabilities = extract_series(facts, USD_TAGS["liabilities"])
    current_assets = extract_series(facts, USD_TAGS["current_assets"])
    current_liabilities = extract_series(facts, USD_TAGS["current_liabilities"])

    revenue_growth = growth_from_last_two(revenue)
    net_income_growth = growth_from_last_two(net_income)

    debt_to_assets = None
    if assets and liabilities and assets[-1]["val"] != 0:
        debt_to_assets = liabilities[-1]["val"] / assets[-1]["val"]

    current_ratio = None
    if current_assets and current_liabilities and current_liabilities[-1]["val"] != 0:
        current_ratio = current_assets[-1]["val"] / current_liabilities[-1]["val"]

    forms = recent_form_counts(submissions, cfg["recent_form_window_days"])

    checks = [
        revenue_growth is not None and revenue_growth >= cfg["revenue_growth_min_pct"],
        net_income_growth is not None and net_income_growth >= cfg["net_income_growth_min_pct"],
        debt_to_assets is not None and debt_to_assets <= cfg["debt_to_assets_max"],
        current_ratio is not None and current_ratio >= cfg["current_ratio_min"],
        forms.get("10-Q", 0) + forms.get("10-K", 0) >= cfg["fresh_report_min_count"],
    ]
    passed = sum(1 for x in checks if x)
    score = round((passed / len(checks)) * 100, 2)

    return {
        "score": score,
        "cik": cik,
        "revenue_growth_pct": round(revenue_growth, 2) if revenue_growth is not None else None,
        "net_income_growth_pct": round(net_income_growth, 2) if net_income_growth is not None else None,
        "debt_to_assets": round(debt_to_assets, 4) if debt_to_assets is not None else None,
        "current_ratio": round(current_ratio, 4) if current_ratio is not None else None,
        "recent_forms": forms,
    }