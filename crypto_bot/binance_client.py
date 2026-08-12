import requests

from .config import BINANCE_BASE_URL, COINS


class BinanceClient:
    def __init__(self):
        self.session = requests.Session()

    def get_ticker(self, symbol):
        url = f"{BINANCE_BASE_URL}/ticker/24hr"
        params = {"symbol": symbol}
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "symbol": symbol,
            "last_price": float(data.get("lastPrice", 0)),
            "price_change_pct": float(data.get("priceChangePercent", 0)),
            "high_price": float(data.get("highPrice", 0)),
            "low_price": float(data.get("lowPrice", 0)),
            "volume": float(data.get("quoteVolume", 0)),
        }

    def get_klines(self, symbol, interval="1d", limit=30):
        url = f"{BINANCE_BASE_URL}/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        bars = resp.json()
        closes = [float(bar[4]) for bar in bars]
        return closes

    def compute_7d_change(self, symbol):
        closes = self.get_klines(symbol, interval="1d", limit=8)
        if len(closes) < 8:
            return 0.0
        first = closes[0]
        last = closes[-1]
        if first == 0:
            return 0.0
        return ((last - first) / first) * 100.0

    def get_market_snapshot(self, coins=None):
        coins = coins or COINS
        snapshot = {}
        for symbol in coins:
            ticker = self.get_ticker(symbol)
            ticker["change_7d_pct"] = self.compute_7d_change(symbol)
            snapshot[symbol] = ticker
        return snapshot
