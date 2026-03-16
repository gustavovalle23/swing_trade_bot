import requests


class SecClient:
    def __init__(self, user_agent):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "data.sec.gov",
            }
        )
        self._ticker_map = None

    def _get_json(self, url):
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.json()

    def ticker_map(self):
        if self._ticker_map is None:
            raw = self._get_json("https://www.sec.gov/files/company_tickers.json")
            mapped = {}
            for item in raw.values():
                mapped[item["ticker"].upper()] = str(item["cik_str"]).zfill(10)
            self._ticker_map = mapped
        return self._ticker_map

    def cik_for(self, ticker):
        return self.ticker_map().get(ticker.upper())

    def submissions(self, cik):
        return self._get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")

    def companyfacts(self, cik):
        return self._get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
