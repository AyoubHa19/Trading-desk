"""Turn the raw zip files into clean hourly tables and check them.

Output: data/processed/<MARKET>.parquet with columns
  open, high, low, close, volume, quote_volume, trades, taker_buy_quote
  (+ funding, oi_usd, top_ls, taker_ls for the perps)
Index: hourly UTC timestamp (bar OPEN time).

Run:  python -m desk.build
"""

import io
import json
import zipfile
from pathlib import Path

import pandas as pd

from desk.config import MARKETS

RAW = Path("data/raw")
OUT = Path("data/processed")
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "trades", "taker_buy_volume", "taker_buy_quote", "ignore"]


def read_zip_csv(path: Path, names=None) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    has_header = not first[:1].isdigit()  # some Binance files have a header row, some don't
    return pd.read_csv(io.StringIO(raw), header=0 if has_header else None, names=names if not has_header else None)


def to_utc(ms_or_us: pd.Series) -> pd.DatetimeIndex:
    # Binance spot files switched from milliseconds to microseconds in 2025.
    s = ms_or_us.astype("int64")
    s = s.where(s < 10**14, s // 1000)
    return pd.to_datetime(s, unit="ms", utc=True)


def load_klines(market: str, symbol: str) -> pd.DataFrame:
    files = sorted((RAW / market / "klines").glob(f"{symbol}-1h-*.zip"))
    parts = []
    for f in files:
        df = read_zip_csv(f)
        df.columns = KLINE_COLS[: len(df.columns)]
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    df.index = pd.DatetimeIndex(to_utc(df["open_time"]))
    df = df[["open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy_quote"]].astype(float)
    return df[~df.index.duplicated(keep="first")].sort_index()


def load_funding(symbol: str) -> pd.Series:
    parts = [read_zip_csv(f) for f in sorted((RAW / "funding").glob(f"{symbol}-fundingRate-*.zip"))]
    df = pd.concat(parts, ignore_index=True)
    ts = pd.DatetimeIndex(to_utc(df["calc_time"])).floor("h")
    s = pd.Series(df["last_funding_rate"].astype(float).values, index=ts)
    return s[~s.index.duplicated()].sort_index()


def load_metrics(symbol: str) -> pd.DataFrame:
    parts = [read_zip_csv(f) for f in sorted((RAW / "metrics").glob(f"{symbol}-metrics-*.zip"))]
    df = pd.concat(parts, ignore_index=True)
    df.index = pd.to_datetime(df["create_time"], utc=True)
    df = df.rename(columns={"sum_open_interest_value": "oi_usd",
                            "sum_toptrader_long_short_ratio": "top_ls",
                            "sum_taker_long_short_vol_ratio": "taker_ls"})
    df = df[["oi_usd", "top_ls", "taker_ls"]].apply(pd.to_numeric, errors="coerce")
    df = df[~df.index.duplicated()].sort_index()
    # Last 5-minute snapshot INSIDE each hour (stamped hh:55), so it is known
    # before the hourly bar closes: no lookahead when we trade at the next open.
    df.loc[df["oi_usd"] <= 0, "oi_usd"] = float("nan")  # a few zero rows are bad prints
    return df.resample("1h").last()


def check(name: str, df: pd.DataFrame) -> dict:
    """Data-quality report: gaps, bad bars, extreme moves."""
    full = pd.date_range(df.index[0], df.index[-1], freq="1h")
    missing = full.difference(df.index)
    bad = ((df["high"] < df[["open", "close"]].max(axis=1)) |
           (df["low"] > df[["open", "close"]].min(axis=1)) | (df["close"] <= 0)).sum()
    ret = df["close"].pct_change().abs()
    return {
        "market": name,
        "first_bar_utc": str(df.index[0]),
        "last_bar_utc": str(df.index[-1]),
        "bars": len(df),
        "missing_hours": len(missing),
        "missing_examples": [str(x) for x in missing[:5]],
        "bad_ohlc_bars": int(bad),
        "max_abs_1h_move_pct": round(100 * float(ret.max()), 2),
        "max_move_at_utc": str(ret.idxmax()),
        "zero_volume_bars": int((df["volume"] == 0).sum()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for name, spec in MARKETS.items():
        market, symbol = spec["hist"]
        df = load_klines(market, symbol)
        if symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            fr = load_funding(symbol)
            # funding is paid at the hour it is stamped; put it on that bar, 0 elsewhere
            df["funding"] = fr.reindex(df.index).fillna(0.0)
            df = df.join(load_metrics(symbol))
        df.to_parquet(OUT / f"{name}.parquet")
        report.append(check(name, df))
        print(json.dumps(report[-1]))
    xau = load_klines("futures/um", "XAUUSDT")
    xau.to_parquet(OUT / "XAU_PERP.parquet")
    report.append(check("XAU_PERP", xau))
    print(json.dumps(report[-1]))
    Path("reports").mkdir(exist_ok=True)
    Path("reports/data_quality.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
