"""Strategy ideas. Each one returns a TARGET direction per hourly bar:
+1 long, -1 short, 0 flat, decided at the close of bar t (traded at the open of t+1).

Every idea comes with a cause (why the market is wrong) and who is on the
other side, so we never trade a pattern without a reason.
"""

import itertools

import numpy as np
import pandas as pd

from desk.features import to_4h


def hold(events: pd.Series, bars: int) -> pd.Series:
    """Turn one-bar events (+1/-1) into a position held for `bars` hours."""
    long = (events == 1).astype(float).rolling(bars, min_periods=1).max()
    short = (events == -1).astype(float).rolling(bars, min_periods=1).max()
    return (long - short).fillna(0.0)


# ---------------------------------------------------------------- trend (4h)
def trend_4h(df, f, lookback_4h: int, **_):
    c4 = to_4h(df)["close"]
    sig = np.sign(np.log(c4 / c4.shift(lookback_4h)))
    return sig.reindex(df.index).ffill().fillna(0.0)


# ------------------------------------------------- funding extremes (perps)
def funding_reversion(df, f, z: float, hold_h: int, **_):
    ev = pd.Series(0.0, index=df.index)
    ev[f["funding_z"] > z] = -1   # longs crowded and paying a lot -> fade them
    ev[f["funding_z"] < -z] = 1   # shorts crowded and paying -> fade them
    return hold(ev, hold_h)


# ------------------------------------- forced sellers / liquidations (perps)
def liquidation_reversal(df, f, k: float, oi_drop: float, hold_h: int, **_):
    flush = f["oi_chg_1h"] < -oi_drop          # positions were closed during the move
    ev = pd.Series(0.0, index=df.index)
    ev[(f["ret_z"] < -k) & flush] = 1           # longs liquidated -> buy the forced selling
    ev[(f["ret_z"] > k) & flush] = -1           # shorts squeezed -> sell the forced buying
    return hold(ev, hold_h)


# ------------------------------------------- slow alt follows fast BTC (1h)
def lead_lag(df, f, k: float, hold_h: int, **_):
    if "btc_ret_1h" not in f:
        return pd.Series(0.0, index=df.index)
    btc_z = f["btc_ret_1h"] / f["btc_ret_1h"].rolling(720).std()
    ev = pd.Series(0.0, index=df.index)
    ev[(btc_z > k) & (f["resid_vs_btc_1h"] < 0)] = 1
    ev[(btc_z < -k) & (f["resid_vs_btc_1h"] > 0)] = -1
    return hold(ev, hold_h)


# ------------------------------------------ volatility compression breakout
def vol_breakout(df, f, ratio: float, hold_h: int, **_):
    quiet = (f["vol_24h"] / f["vol_30d"]).shift(1) < ratio
    ev = pd.Series(0.0, index=df.index)
    ev[quiet & (df["close"] > f["hi_24"].shift(1))] = 1
    ev[quiet & (df["close"] < f["lo_24"].shift(1))] = -1
    return hold(ev, hold_h)


# --------------------------------------- short-term mean reversion (proxies)
def mean_reversion(df, f, k: float, hold_h: int, **_):
    c = df["close"]
    z = (c - c.rolling(24).mean()) / c.rolling(24).std()
    ev = pd.Series(0.0, index=df.index)
    ev[z < -k] = 1
    ev[z > k] = -1
    return hold(ev, hold_h)


def grid(**axes):
    keys = list(axes)
    return [dict(zip(keys, v)) for v in itertools.product(*axes.values())]


# name -> function, markets, parameter grid, stop distance in ATRs, the story
STRATEGIES = {
    "trend_4h": {
        "fn": trend_4h,
        "markets": ["BTC", "ETH", "SOL", "GOLD", "EUR"],
        "grid": grid(lookback_4h=[30, 60, 120], stop_atr=[4.0, 8.0]),
        "idea": "Prices under-react to news, so a move over the last 5-20 days tends to continue.",
        "losing_side": "Early profit-takers and slow money (funds, treasuries) that buy or sell late.",
        "cause": "slow markets following fast ones / under-reaction",
    },
    "funding_reversion": {
        "fn": funding_reversion,
        "markets": ["BTC", "ETH", "SOL"],
        "grid": grid(z=[1.5, 2.5], hold_h=[24, 72], stop_atr=[3.0]),
        "idea": "When funding is extreme, one side is crowded and over-paying; fade them.",
        "losing_side": "Leveraged traders paying extreme funding who get forced out.",
        "cause": "funding extremes",
    },
    "liquidation_reversal": {
        "fn": liquidation_reversal,
        "markets": ["BTC", "ETH", "SOL"],
        "grid": grid(k=[3.0, 4.0], oi_drop=[0.01, 0.02], hold_h=[12], stop_atr=[3.0]),
        "idea": "A violent 1h move with open interest collapsing is forced selling (or buying); it overshoots and bounces.",
        "losing_side": "Liquidated traders whose positions are closed at any price.",
        "cause": "forced sellers",
    },
    "lead_lag": {
        "fn": lead_lag,
        "markets": ["ETH", "SOL"],
        "grid": grid(k=[2.0, 3.0], hold_h=[2, 4], stop_atr=[3.0]),
        "idea": "After a big BTC hour, ETH/SOL that lagged catch up.",
        "losing_side": "Slow liquidity providers in the alt books.",
        "cause": "slow markets following fast ones",
    },
    "vol_breakout": {
        "fn": vol_breakout,
        "markets": ["BTC", "ETH", "SOL", "GOLD"],
        "grid": grid(ratio=[0.6, 0.8], hold_h=[24, 72], stop_atr=[3.0]),
        "idea": "After quiet periods, a break of the 24h range triggers clustered stops and runs.",
        "losing_side": "Range sellers whose stops sit just outside the range.",
        "cause": "volatility mispriced (too low) vs what follows",
    },
    "mean_reversion": {
        "fn": mean_reversion,
        "markets": ["GOLD", "EUR"],
        "grid": grid(k=[2.0, 3.0], hold_h=[6, 12], stop_atr=[3.0]),
        "idea": "Crypto-venue proxies (PAXG, EURUSDT) get pushed away from the real gold/EUR price by local flows and get pulled back by arbitrage.",
        "losing_side": "Impatient crypto traders hitting thin proxy books.",
        "cause": "slow proxy market vs fast real market",
    },
}
