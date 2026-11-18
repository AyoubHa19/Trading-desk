"""Quant: turn ideas into strategies and test them honestly.

Walk-forward, 12 quarterly folds (out-of-sample 2023-12-01 -> 2026-11-16):
  for each fold
    * on the previous 12 months only: pick the parameters (same for all markets),
      keep only markets whose trades made money (positive mean R, >= 20 trades),
      and size each one with quarter Kelly from those past trades (max 1% risk);
    * then trade the next 3 months, which the choice has never seen.
The out-of-sample folds are chained into one equity curve.

Then: costs doubled, Monte Carlo on the trades, bull/bear/chop split,
buy-and-hold benchmark, a 1-5 score, and a strategy card per idea.

Run:  python -m desk.quant
"""

import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from desk import config as C
from desk import engine
from desk.features import build_all, load_all
from desk.risk import kelly_risk
from desk.strategies import STRATEGIES, grid, hold

OOS_START = pd.Timestamp("2023-12-01", tz="UTC")
OOS_END = pd.Timestamp("2026-11-16 23:00", tz="UTC")
TRAIN = pd.DateOffset(months=12)

DATA = FEATS = PRICER = None


def _init():
    global DATA, FEATS, PRICER
    DATA = load_all()
    FEATS = build_all(DATA)
    PRICER = pd.read_parquet("data/processed/pricer_oos.parquet")


# ---- extra strategy that trades the Pricer's out-of-sample fair value gap ----
def pricer_gap(df, f, mult: float, hold_h: int, market: str = "", **_):
    pred = PRICER[market].reindex(df.index)
    kind = "perp" if C.MARKETS[market]["hist"][0].startswith("futures") else "spot"
    round_trip = 2 * (C.COSTS[kind]["fee"] + C.COSTS[kind]["slippage"])
    ev = pd.Series(0.0, index=df.index)
    ev[pred > mult * round_trip] = 1
    ev[pred < -mult * round_trip] = -1
    return hold(ev, hold_h)


STRATEGIES["pricer_gap"] = {
    "fn": pricer_gap,
    "markets": list(C.MARKETS),
    "grid": grid(mult=[1.0, 2.0], hold_h=[24], stop_atr=[4.0]),
    "idea": "Trade when the Pricer's fair value is far enough from the price to pay the costs.",
    "losing_side": "Whoever is wrong about the inputs (trend, funding, OI, BTC) the model reads.",
    "cause": "fair value vs price gap",
    "oos_only": True,  # predictions only exist out-of-sample
}


# ---- exit variants of trend_4h: same entries, different ways out ----
for _name, _extra, _idea in [
    ("trend_4h_trail", {"trail_atr": [4.0, 6.0]}, "Same trend entries; a trailing stop follows the best price to lock in profit."),
    ("trend_4h_tp", {"tp_r": [2.0, 3.0]}, "Same trend entries; take the profit at 2R or 3R."),
    ("trend_4h_time", {"max_hold_h": [24 * 5, 24 * 10]}, "Same trend entries; close any trade after 5 or 10 days."),
    ("trend_4h_be", {"be_r": [1.0, 2.0]}, "Same trend entries; once 1R or 2R in profit, the stop moves to breakeven."),
    ("trend_4h_partial", {"partial_r": [1.0, 2.0], "partial_frac": [0.5]},
     "Same trend entries; take half the profit at 1R or 2R, stop to breakeven, let the rest run."),
]:
    STRATEGIES[_name] = dict(STRATEGIES["trend_4h"], idea=_idea,
                             grid=grid(lookback_4h=[30, 60, 120], stop_atr=[4.0, 8.0], **_extra))


def folds():
    t = OOS_START
    while t < OOS_END:
        yield t - TRAIN, t - pd.Timedelta(hours=1), t, min(t + pd.DateOffset(months=3) - pd.Timedelta(hours=1), OOS_END)
        t = t + pd.DateOffset(months=3)


def targets_for(name, params, markets):
    s = STRATEGIES[name]
    return {m: s["fn"](DATA[m], FEATS[m], market=m, **params) for m in markets}


def exits_of(p):
    return {k: p.get(k) for k in ("trail_atr", "tp_r", "max_hold_h", "be_r", "partial_r", "partial_frac")}


def single(name, params, m, start, end, risk=C.RISK_PER_TRADE, cost_mult=1.0):
    tg = targets_for(name, params, [m])
    return engine.run(DATA, FEATS, tg, {m: params["stop_atr"]}, {m: risk}, start, end, cost_mult=cost_mult,
                      exits=exits_of(params))


def choose(name, tr0, tr1):
    """Use ONLY the training window: best params, which markets, how much risk."""
    s = STRATEGIES[name]
    best = None
    for p in s["grid"]:
        per_m = {m: single(name, p, m, tr0, tr1) for m in s["markets"]}
        sharpes = [engine.stats(r.equity, r.trades)["sharpe"] for r in per_m.values()]
        score = float(np.mean(sharpes))
        if best is None or score > best[0]:
            best = (score, p, per_m)
    _, p, per_m = best
    risk = {}
    for m, r in per_m.items():
        R = r.trades["R"].tolist() if len(r.trades) else []
        risk[m] = kelly_risk(R)
    return p, {m: k for m, k in risk.items() if k > 0}


def walk_forward(name, cost_mult=1.0, fixed=None):
    """Chain the out-of-sample folds with ONE book, like the live bot: open trades carry over
    from one fold to the next (no forced close every 3 months). At each fold the parameters
    and per-market risk are re-chosen on the previous 12 months; a market that is dropped gets
    no new trades but its open trade runs to its own exit. `fixed` re-uses earlier choices."""
    markets = STRATEGIES[name]["markets"]
    book = engine.Book(markets, C.START_CAPITAL, cost_mult)
    eq_parts, trades, halts, choices = [], [], [], []
    all_folds = list(folds())
    for k, (tr0, tr1, te0, te1) in enumerate(all_folds):
        if fixed:
            p, risk = fixed[k]["params"], fixed[k]["risk"]
        elif STRATEGIES[name].get("oos_only"):
            # Pricer predictions before the OOS start don't exist; choose on the previous fold's OOS
            p, risk = choose(name, max(tr0, OOS_START), tr1) if te0 > OOS_START else (STRATEGIES[name]["grid"][0], {})
        else:
            p, risk = choose(name, tr0, tr1)
        choices.append({"test_start": str(te0.date()), "params": p, "risk": risk})
        tg = targets_for(name, p, markets)
        res = engine.run(DATA, FEATS, tg, {m: p["stop_atr"] for m in markets}, {m: risk.get(m, 0.0) for m in markets},
                         te0, te1, cost_mult=cost_mult, exits=exits_of(p), book=book,
                         close_at_end=(k == len(all_folds) - 1))
        eq_parts.append(res.equity)
        trades.append(res.trades)
        halts += res.halts
    eq = pd.concat(eq_parts)
    eq = eq[~eq.index.duplicated(keep="last")]
    tr = pd.concat([t for t in trades if len(t)], ignore_index=True) if any(len(t) for t in trades) else pd.DataFrame(
        columns=["market", "pnl", "R", "exit_time", "entry_time"])
    return eq, tr, halts, choices


def buy_and_hold(markets):
    idx = DATA["BTC"].loc[OOS_START:OOS_END].index
    rets = pd.concat([DATA[m]["close"].reindex(idx).ffill().pct_change() for m in markets], axis=1).mean(axis=1).fillna(0)
    return C.START_CAPITAL * (1 + rets).cumprod()


def regimes(idx):
    btc = DATA["BTC"]["close"]
    r30 = (btc / btc.shift(720) - 1).reindex(idx)
    return pd.Series(np.where(r30 > 0.10, "bull", np.where(r30 < -0.10, "bear", "chop")), index=idx)


def regime_sharpe(eq):
    r = eq.pct_change().fillna(0)
    reg = regimes(eq.index)
    out = {}
    for name in ("bull", "bear", "chop"):
        x = r[reg == name]
        out[name] = round(float(x.mean() / x.std() * math.sqrt(8760)), 2) if x.std() > 0 else 0.0
    return out


def monte_carlo(eq, trades, n=5000, seed=7):
    """Reshuffle and resample the out-of-sample trades: how bad could the path have been?"""
    if len(trades) < 10:
        return {}
    # each trade as a % of equity at entry, approximated by pnl / equity just before exit
    eq_at = eq.reindex(pd.to_datetime(trades["exit_time"]), method="ffill").values
    frac = (trades["pnl"].values / np.maximum(eq_at - trades["pnl"].values, 1e-9))
    rng = np.random.default_rng(seed)
    sims = rng.choice(frac, size=(n, len(frac)), replace=True)
    paths = np.cumprod(1 + sims, axis=1)
    dd = (paths / np.maximum.accumulate(paths, axis=1) - 1).min(axis=1)
    final = paths[:, -1] - 1
    return {"p5_return_pct": round(100 * float(np.percentile(final, 5)), 1),
            "median_return_pct": round(100 * float(np.median(final)), 1),
            "p95_max_dd_pct": round(100 * float(np.percentile(dd, 5)), 1),
            "prob_loss_pct": round(100 * float((final < 0).mean()), 1)}


def score(st, reg):
    def band(x, edges):  # edges ascending; returns 1..5
        return 1 + sum(x > e for e in edges)
    s = {
        "profit": band(st.get("cagr_pct", -100), [0, 5, 15, 30]),
        "sharpe": band(st.get("sharpe", -9), [0, 0.5, 1.0, 1.5]),
        "drawdown": band(st.get("max_dd_pct", -100), [-30, -20, -10, -5]),
        "trades": band(st.get("trades", 0), [30, 60, 100, 200]),
        "losing_streak": 6 - band(st.get("worst_losing_streak", 99), [3, 5, 8, 12]),
        "regimes": 1 + sum(v > 0 for v in reg.values()) + (1 if all(v > 0.5 for v in reg.values()) else 0),
    }
    s["total"] = round(float(np.mean(list(s.values()))), 2)
    return s


def evaluate(name):
    _init() if DATA is None else None
    eq, tr, halts, choices = walk_forward(name)
    st = engine.stats(eq, tr)
    eq2, tr2, _, _ = walk_forward(name, cost_mult=2.0, fixed=choices)
    st2 = engine.stats(eq2, tr2)
    traded = sorted({m for c in choices for m in c["risk"]}) or STRATEGIES[name]["markets"]
    bh = buy_and_hold(traded)
    st_bh = engine.stats(bh, pd.DataFrame())
    reg = regime_sharpe(eq)
    sc = score(st, reg)
    gates = {
        "beats_buy_and_hold_sharpe": st["sharpe"] > st_bh["sharpe"],
        "profitable_after_costs": st["return_pct"] > 0,
        "profitable_with_costs_doubled": st2["return_pct"] > 0,
        "enough_trades": st["trades"] >= 30,
    }
    by_market = (tr.groupby("market")["pnl"].agg(["count", "sum"]).round(2).to_dict("index") if len(tr) else {})
    eq.to_frame("equity").to_parquet(f"data/processed/oos_equity_{name}.parquet")
    return {"name": name, "oos": st, "costs_doubled": st2, "buy_and_hold": st_bh, "regime_sharpe": reg,
            "monte_carlo": monte_carlo(eq, tr), "score": sc, "gates": gates, "passes": all(gates.values()),
            "halts": len(halts), "by_market": by_market, "folds": choices, "markets_traded": traded}


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return round(float(o), 3)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def main():
    names = list(STRATEGIES)
    with ProcessPoolExecutor(4, initializer=_init) as pool:
        results = list(pool.map(evaluate, names))
    results = [clean(r) for r in results]
    results.sort(key=lambda r: (r["passes"], r["score"]["total"]), reverse=True)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/quant_results.json").write_text(json.dumps(results, indent=2, default=str))
    for r in results:
        o = r["oos"]
        print(f"{r['name']:22} pass={r['passes']!s:5} score={r['score']['total']:.2f} ret={o['return_pct']:7.1f}% "
              f"sharpe={o['sharpe']:5.2f} dd={o['max_dd_pct']:6.1f}% trades={o['trades']:4} "
              f"x2costs={r['costs_doubled']['return_pct']:6.1f}% BH_sharpe={r['buy_and_hold']['sharpe']:.2f} "
              f"markets={r['markets_traded']}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- selection
def select(results_path="reports/quant_results.json", out="state/strategy.json"):
    """Champion = best strategy that passed every gate. Challengers = next two that
    made money out-of-sample after costs (they may not have passed every gate:
    they paper-trade in the shadow and can only be promoted if they pass later).
    Each one is configured on the LAST 12 months, exactly as the next walk-forward fold would be."""
    results = json.loads(Path(results_path).read_text())
    live_ok = [r for r in results if r["name"] != "pricer_gap"]  # needs the nightly model; research only
    passing = [r for r in live_ok if r["passes"]]
    others = [r for r in live_ok if not r["passes"] and r["oos"]["return_pct"] > 0]
    picks = {"champion": passing[0] if passing else None}
    # Owner's choice (2026-11-17): trade the champion only, no challengers.
    if DATA is None:
        _init()
    end = DATA["BTC"].index[-1]
    ledgers = {}
    for role, r in picks.items():
        if r is None:
            ledgers[role] = None
            continue
        p, risk = choose(r["name"], end - TRAIN, end)
        ledgers[role] = {"name": r["name"], "params": p, "risk": risk, "markets": sorted(risk),
                         "passed_gates": r["passes"], "score": r["score"]["total"]}
    doc = {"generated_utc": str(pd.Timestamp.now(tz="UTC").floor("s")), "trained_through_utc": str(end), "ledgers": ledgers}
    Path(out).parent.mkdir(exist_ok=True)
    Path(out).write_text(json.dumps(clean(doc), indent=2))
    return doc
