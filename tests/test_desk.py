"""Tests for every piece the money depends on.

Run:  python -m pytest -q
The data-based tests need data/processed (python -m desk.download && python -m desk.build).
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from desk import bot, config as C, engine
from desk.features import add_features, build_all, load_all
from desk.risk import DayGuard, data_looks_wrong, kelly_risk, position_size
from desk.strategies import STRATEGIES

HAVE_DATA = Path("data/processed/BTC.parquet").exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="run desk.download + desk.build first")


# ------------------------------------------------------------------ risk
def test_kelly_needs_edge_and_samples():
    assert kelly_risk([1.0] * 10) == 0.0                     # too few trades
    assert kelly_risk([-1.0, 0.5] * 20) == 0.0                # negative edge -> no trade
    assert kelly_risk([2.0, -1.0] * 20) == C.RISK_PER_TRADE   # big edge -> capped at 1%
    small = kelly_risk([1.02, -1.0] * 20)  # tiny edge: quarter Kelly ~0.25%
    assert 0 < small < C.RISK_PER_TRADE


def test_position_size_caps():
    # 1% risk, 2% stop -> notional 50% of equity
    units, risk = position_size(100, 0.01, 100.0, 2.0, 0, 0, 1e9)
    assert math.isclose(units * 100, 50) and math.isclose(risk, 1.0)
    # tiny stop -> leverage capped at 3x
    units, risk = position_size(100, 0.01, 100.0, 0.01, 0, 0, 1e9)
    assert math.isclose(units * 100, 300) and risk < 1.0
    # theme already at 5% risk -> nothing left
    assert position_size(100, 0.01, 100.0, 2.0, 0, 5.0, 1e9) == (0.0, 0.0)
    # thin book: max 1% of hourly volume ($200 -> $2 < $5 minimum) -> skip
    assert position_size(100, 0.01, 100.0, 2.0, 0, 0, 200.0) == (0.0, 0.0)
    # costs eat more than 25% of the risk -> skip
    assert position_size(100, 0.01, 100.0, 0.1, 0, 0, 1e9, cost_rate=0.0015) == (0.0, 0.0)


def test_day_guard_loss_and_streak():
    g = DayGuard()
    g.new_bar("2026-01-01", 100.0)
    limit = 100 * (1 - C.DAILY_LOSS_STOP)
    assert not g.check(limit + 0.5, "t1")
    assert g.check(limit - 0.1, "t2") and "daily loss" in g.reason
    g.new_bar("2026-01-02", limit - 0.1)                      # new NY day resets
    assert not g.halted
    for _ in range(3):
        g.record_trade(-0.1)
    assert g.check(limit - 0.2, "t3") and "losing" in g.reason


def test_data_checks():
    assert data_looks_wrong(100, 100, 1, 10) == ""
    assert "stale" in data_looks_wrong(100, 100, 1, 200)
    assert "jumped" in data_looks_wrong(130, 100, 1, 10)
    assert data_looks_wrong(float("nan"), 100, 1, 10) == "bad price"


# ------------------------------------------------------------------ engine
def _toy(n=200, drift=0.001):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = 100 * np.exp(np.cumsum(np.full(n, drift)))
    df = pd.DataFrame({"open": np.r_[100, close[:-1]], "close": close, "quote_volume": 1e9}, index=idx)
    df["high"] = df[["open", "close"]].max(axis=1) * 1.001
    df["low"] = df[["open", "close"]].min(axis=1) * 0.999
    df["funding"] = 0.0
    return df


def test_engine_accounting_long_trend():
    df = _toy()
    data = {"BTC": df}
    feats = {"BTC": add_features(df)}
    tgt = {"BTC": pd.Series(1.0, index=df.index)}
    res = engine.run(data, feats, tgt, {"BTC": 3.0}, {"BTC": 0.01}, df.index[30], df.index[-1])
    assert len(res.trades) >= 1
    # every dollar of equity change is explained by the trades
    assert math.isclose(res.trades["pnl"].sum(), res.equity.iloc[-1] - res.equity.iloc[0], abs_tol=1e-9)
    t = res.trades.iloc[0]
    assert t["entry"] == df.loc[df.index[31], "open"]          # filled at the NEXT bar's open
    assert t["pnl"] > 0


def test_engine_stop_and_no_reentry():
    df = _toy(drift=-0.004)                                    # steady fall vs a long target
    data, feats = {"BTC": df}, {"BTC": add_features(df)}
    tgt = {"BTC": pd.Series(1.0, index=df.index)}
    res = engine.run(data, feats, tgt, {"BTC": 1.0}, {"BTC": 0.01}, df.index[30], df.index[-1])
    assert (res.trades["reason"] == "stop").sum() == 1         # stopped once, then blocked
    assert res.trades.iloc[0]["R"] < -0.9


# ------------------------------------------------------------------ lookahead
@needs_data
@pytest.mark.parametrize("name", list(STRATEGIES))
def test_no_lookahead(name):
    """Signals up to time T must not change when the data after T is removed."""
    data = load_all()
    feats = build_all(data)
    cut = pd.Timestamp("2025-06-10 13:00", tz="UTC")
    short = {m: d.loc[:cut] for m, d in data.items()}
    feats_s = build_all(short)
    s = STRATEGIES[name]
    if s.get("oos_only"):
        pytest.skip("uses stored out-of-sample predictions")
    p = s["grid"][0]
    for m in s["markets"]:
        full = s["fn"](data[m], feats[m], market=m, **p).loc[:cut]
        part = s["fn"](short[m], feats_s[m], market=m, **p).loc[:cut]
        pd.testing.assert_series_equal(full, part, check_names=False)


# ------------------------------------------------------------------ bot = backtest
@needs_data
def test_bot_replays_exactly_like_the_backtest():
    """Feed the bot history hour by hour; it must make the same trades as engine.run."""
    data = load_all()
    markets = ["BTC", "ETH", "SOL"]
    cfg = {"name": "trend_4h", "params": {"lookback_4h": 30, "stop_atr": 4.0},
           "risk": {m: 0.01 for m in markets}, "markets": markets, "passed_gates": True, "score": 0}
    hours = pd.date_range("2025-03-01 00:00", "2025-03-12 00:00", freq="1h", tz="UTC")
    led = None
    for T in hours:
        snap = {}
        for m in markets:
            d = data[m].loc[:T].iloc[-bot.HISTORY_HOURS:].copy()
            d["confirmed"] = d.index < T                       # bar T is "in progress"
            snap[m] = d
        f = {m: add_features(snap[m], None if m == "BTC" else snap["BTC"]) for m in markets}
        live = {m: float(snap[m]["open"].iloc[-1]) for m in markets}
        led, _, _ = bot.step_ledger("champion", cfg, led, snap, f, live, T)

    feats = build_all(data)
    s = STRATEGIES["trend_4h"]
    tg = {m: s["fn"](data[m], feats[m], **cfg["params"]) for m in markets}
    res = engine.run(data, feats, tg, {m: 4.0 for m in markets}, cfg["risk"], hours[0] - pd.Timedelta(hours=1), hours[-1])
    bt = res.trades[res.trades["reason"] != "end"]
    live_trades = pd.DataFrame(led["book"]["trades"])
    assert len(bt) == len(live_trades) > 0
    assert np.allclose(bt["pnl"].values, live_trades["pnl"].values)
    assert list(bt["market"]) == list(live_trades["market"])


def test_trailing_stop_locks_profit():
    up = _toy(n=120, drift=0.004)
    down = _toy(n=120, drift=-0.004)
    df = pd.concat([up, down.assign(**{c: down[c] * up["close"].iloc[-1] / 100 for c in ["open", "high", "low", "close"]})
                    .set_axis(pd.date_range(up.index[-1] + pd.Timedelta(hours=1), periods=120, freq="1h", tz="UTC"))])
    data, feats = {"BTC": df}, {"BTC": add_features(df)}
    tgt = {"BTC": pd.Series(1.0, index=df.index)}
    res = engine.run(data, feats, tgt, {"BTC": 8.0}, {"BTC": 0.01}, df.index[30], df.index[-1], exits={"trail_atr": 3.0})
    t = res.trades.iloc[0]
    assert t["reason"] == "trail" and t["pnl"] > 0               # rode the rise, kept a profit on the fall


def test_take_profit_and_time_limit():
    df = _toy(n=300, drift=0.002)
    data, feats = {"BTC": df}, {"BTC": add_features(df)}
    tgt = {"BTC": pd.Series(1.0, index=df.index)}
    tp = engine.run(data, feats, tgt, {"BTC": 3.0}, {"BTC": 0.01}, df.index[30], df.index[-1], exits={"tp_r": 2.0})
    assert tp.trades.iloc[0]["reason"] == "take profit" and abs(tp.trades.iloc[0]["R"] - 2.0) < 0.3
    tl = engine.run(data, feats, tgt, {"BTC": 3.0}, {"BTC": 0.01}, df.index[30], df.index[-1], exits={"max_hold_h": 24})
    assert tl.trades.iloc[0]["reason"] == "time limit"
