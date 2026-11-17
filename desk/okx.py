"""Read-only OKX public market data. No API keys, no orders: paper trading only."""

import json
import time
import urllib.request

import pandas as pd

BASE = "https://www.okx.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (paper-trading-research-client)"}  # OKX's CDN rejects the default Python agent


def _get(path: str, tries: int = 4) -> list:
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.load(r)
            if body.get("code") == "0":
                return body["data"]
            raise RuntimeError(f"OKX error {body.get('code')}: {body.get('msg')}")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1 + 2 * i)
    return []


def candles_1h(inst: str, hours: int = 900) -> pd.DataFrame:
    """Last `hours` hourly candles (oldest first). Last row may be the bar in progress (confirmed=False)."""
    rows = _get(f"/api/v5/market/candles?instId={inst}&bar=1H&limit=300")
    while len(rows) < hours and rows:
        older = _get(f"/api/v5/market/history-candles?instId={inst}&bar=1H&limit=100&after={rows[-1][0]}")
        if not older:
            break
        rows += older
        time.sleep(0.15)  # stay well under the public rate limit
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "vol", "vol_ccy", "quote_volume", "confirm"])
    df.index = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df["confirmed"] = df["confirm"] == "1"
    df = df[["open", "high", "low", "close", "quote_volume", "confirmed"]]
    df[["open", "high", "low", "close", "quote_volume"]] = df[["open", "high", "low", "close", "quote_volume"]].astype(float)
    return df[~df.index.duplicated()].sort_index().iloc[-hours:]


def funding_history(inst: str, pages: int = 2) -> pd.Series:
    """Realized funding rates, stamped at the funding time (floored to the hour)."""
    rows, after = [], ""
    for _ in range(pages):
        page = _get(f"/api/v5/public/funding-rate-history?instId={inst}&limit=100{after}")
        if not page:
            break
        rows += page
        after = f"&after={page[-1]['fundingTime']}"
    s = pd.Series({pd.Timestamp(int(r["fundingTime"]), unit="ms", tz="UTC").floor("h"): float(r.get("realizedRate") or r["fundingRate"])
                   for r in rows})
    return s.sort_index()


def ticker_last(inst: str) -> float:
    return float(_get(f"/api/v5/market/ticker?instId={inst}")[0]["last"])
