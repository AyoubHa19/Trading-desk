"""Features built ONLY from information known at the close of each hourly bar.

Rule: a value in row t may use bars up to and including t, never t+1.
The engine trades on the OPEN of bar t+1, so this is lookahead-free.
tests/test_no_lookahead.py checks it by cutting the data and comparing.
"""

import numpy as np
import pandas as pd

from desk.config import MARKETS

DATA = "data/processed"


def load_all(path: str = DATA) -> dict[str, pd.DataFrame]:
    return {m: pd.read_parquet(f"{path}/{m}.parquet") for m in MARKETS}


def atr(df: pd.DataFrame, n: int = 24) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def zscore(s: pd.Series, n: int) -> pd.Series:
    m = s.rolling(n, min_periods=n // 2).mean()
    sd = s.rolling(n, min_periods=n // 2).std()
    return (s - m) / sd.replace(0, np.nan)


def add_features(df: pd.DataFrame, btc: pd.DataFrame | None = None) -> pd.DataFrame:
    f = pd.DataFrame(index=df.index)
    c = df["close"]
    r1 = np.log(c).diff()
    f["ret_1h"] = r1
    f["atr"] = atr(df)
    f["vol_24h"] = r1.rolling(24).std()
    f["vol_30d"] = r1.rolling(720).std()
    f["ret_z"] = r1 / f["vol_30d"]
    for d in (5, 10, 20):
        f[f"mom_{d}d"] = np.log(c / c.shift(24 * d))
    f["hi_24"] = df["high"].rolling(24).max()
    f["lo_24"] = df["low"].rolling(24).min()
    f["quote_vol_24h"] = df["quote_volume"].rolling(24).mean()

    if "funding" in df:
        # funding prints every 8h; carry the last print forward until the next one
        fr = df["funding"].where(df["funding"] != 0).ffill()
        f["funding"] = fr
        f["funding_z"] = zscore(fr, 24 * 30)
    if "oi_usd" in df:
        oi = df["oi_usd"].ffill()
        f["oi_chg_1h"] = oi.pct_change(fill_method=None)
        f["oi_chg_24h"] = oi.pct_change(24, fill_method=None)
    if btc is not None:
        b1 = np.log(btc["close"]).diff().reindex(df.index)
        f["btc_ret_1h"] = b1
        # rolling beta of this market to BTC over 30 days
        cov = r1.rolling(720).cov(b1)
        var = b1.rolling(720).var()
        f["beta_btc"] = cov / var
        f["resid_vs_btc_1h"] = r1 - f["beta_btc"] * b1
    return f


def build_all(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    btc = data["BTC"]
    return {m: add_features(df, None if m == "BTC" else btc) for m, df in data.items()}


def to_4h(df: pd.DataFrame) -> pd.DataFrame:
    """Hourly -> 4h bars, re-stamped at the time each 4h bar is COMPLETE.

    A 4h bar covering 00:00-04:00 is only known at 04:00, so it is stamped 04:00.
    Forward-filling it onto hourly rows therefore never leaks the future.
    """
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "quote_volume": "sum"}
    out = df[list(agg)].resample("4h", label="left", closed="left").agg(agg).dropna()
    out.index = out.index + pd.Timedelta(hours=4) - pd.Timedelta(hours=1)  # = open time of the last hourly bar in the block
    return out
