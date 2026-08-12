import requests

from .config import SECTOR_INDICES, SECTOR_LABELS, INDICES, INDICES_LABELS, YAHOO_BASE_URL


class YahooClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def get_quote(self, symbol, range_str="1mo"):
        url = f"{YAHOO_BASE_URL}/{symbol}"
        params = {"range": range_str, "interval": "1d"}
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        j = resp.json()["chart"]["result"][0]
        meta = j.get("meta", {})
        quote = j["indicators"]["quote"][0]

        closes = [c for c in quote.get("close", []) if c is not None]
        opens = [o for o in quote.get("open", []) if o is not None]
        highs = [h for h in quote.get("high", []) if h is not None]
        lows = [l for l in quote.get("low", []) if l is not None]

        price = meta.get("regularMarketPrice") or (closes[-1] if closes else 0)
        prev_close = meta.get("chartPreviousClose") or (closes[-2] if len(closes) > 1 else price)

        change_pct = 0.0
        if prev_close:
            change_pct = ((price - prev_close) / prev_close) * 100.0

        change_5d_pct = 0.0
        if len(closes) >= 2 and closes[-1]:
            base_idx = max(0, len(closes) - 6)
            base = closes[base_idx]
            if base:
                change_5d_pct = ((closes[-1] - base) / base) * 100.0

        return {
            "symbol": symbol,
            "price": float(price),
            "change_pct": float(change_pct),
            "change_5d_pct": float(change_5d_pct),
            "open": float(opens[-1]) if opens else 0.0,
            "high": float(highs[-1]) if highs else 0.0,
            "low": float(lows[-1]) if lows else 0.0,
            "prev_close": float(prev_close),
            "currency": meta.get("currency", "INR"),
        }

    def get_market_snapshot(self, symbols):
        snapshot = {}
        for sym in symbols:
            try:
                snapshot[sym] = self.get_quote(sym)
            except Exception:
                snapshot[sym] = None
        return snapshot

    def get_indices_snapshot(self):
        return self.get_market_snapshot(INDICES)

    def get_sector_snapshot(self):
        return self.get_market_snapshot(SECTOR_INDICES)

    @staticmethod
    def label(symbol):
        if symbol in INDICES_LABELS:
            return INDICES_LABELS[symbol]
        if symbol in SECTOR_LABELS:
            return SECTOR_LABELS[symbol]
        return symbol.replace(".NS", "").replace("^", "")

    def full_snapshot(self):
        snapshot = self.get_market_snapshot(INDICES + SECTOR_INDICES)
        return {
            sym: {
                **data,
                "label": self.label(sym),
                "is_index": sym in INDICES,
                "is_sector": sym in SECTOR_INDICES,
            }
            for sym, data in snapshot.items()
            if data
        }