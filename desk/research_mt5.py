"""What would the champion do on an Exness MT5 account with $100?

Same walk-forward as desk/quant.py, with broker rules on top:
  * lots: a trade is rounded DOWN to the lot step; below the minimum lot it is SKIPPED
    (we never take more risk than the rule allows),
  * costs: spread (round trip, as a share of price) instead of exchange fees, no funding,
  * swap: a fee per night on every open position (charged at 21:00 UTC rollover; x3 on Wednesday
    for gold/FX),
  * two account types: Standard (USD) and Standard Cent (prices in US cents, so a $100 deposit
    behaves like 10,000 units and 1 lot is 1/100 of a standard lot).

ALL broker numbers below are ESTIMATES (labelled). Check them in MT5: right-click the symbol in
Market Watch -> Specification, and correct the PROFILES dict. Weekend gaps of gold/EUR are NOT in
this data (the proxies trade 24/7): MT5's own Strategy Tester is needed for that.

Run:  python -m desk.research_mt5
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from desk import engine, quant
from desk.risk import position_size

# contract = units of the asset in 1 lot; min_lot / lot_step in lots; spread = round-trip cost as share of price
PROFILE = {  # ESTIMATES for Exness Standard; check the Specification window in MT5
    "BTC": {"contract": 1.0, "min_lot": 0.01, "lot_step": 0.01, "spread": 0.00030, "fx_swap": False},
    "ETH": {"contract": 1.0, "min_lot": 0.10, "lot_step": 0.10, "spread": 0.00080, "fx_swap": False},
    "GOLD": {"contract": 100.0, "min_lot": 0.01, "lot_step": 0.01, "spread": 0.00006, "fx_swap": True},
    "EUR": {"contract": 100000.0, "min_lot": 0.01, "lot_step": 0.01, "spread": 0.00010, "fx_swap": True},
}
MARKETS = list(PROFILE)

SCENARIOS = {  # swap per night as a share of notional, charged to longs AND shorts (worst case)
    "standard_noswap": {"cent": False, "swap": {"crypto": 0.0, "fx": 0.0}},
    "standard_swap": {"cent": False, "swap": {"crypto": 0.0006, "fx": 0.0001}},
    "cent_noswap": {"cent": True, "swap": {"crypto": 0.0, "fx": 0.0}},
    "cent_swap_mid": {"cent": True, "swap": {"crypto": 0.0003, "fx": 0.0001}},
    "cent_swap_high": {"cent": True, "swap": {"crypto": 0.0006, "fx": 0.0002}},
}


def setup(scn):
    """Patch the shared engine with the broker's rules (in this process only)."""
    quant._init()
    for m in quant.DATA:
        if "funding" in quant.DATA[m]:
            quant.DATA[m] = quant.DATA[m].assign(funding=0.0)  # CFDs: no perp funding, swap instead
    cent = SCENARIOS[scn]["cent"]
    swap = SCENARIOS[scn]["swap"]
    stats = {"signals": 0, "skipped_min_lot": 0}

    class BrokerBook(engine.Book):
        def __init__(self, markets, equity=100.0, cost_mult=1.0, exits=None):
            super().__init__(markets, equity, cost_mult, exits)
            self.cost = {m: PROFILE[m]["spread"] / 2 * cost_mult for m in self.markets}  # half the spread each side

        def _size(self, m, *args):
            units, risk = position_size(*args)
            if units <= 0:
                return units, risk
            stats["signals"] += 1
            p = PROFILE[m]
            size = p["contract"] / (100 if cent else 1)        # asset units per 1 lot on this account
            step, mn = p["lot_step"] * size, p["min_lot"] * size
            units = round(units / step, 9) // 1 * step          # round DOWN to the lot step
            if units < mn - 1e-12:
                stats["skipped_min_lot"] += 1                   # smallest lot would break the risk rule
                return 0.0, 0.0
            return units, units * args[3]                       # args[3] = stop distance

        def close_bar(self, t, highs, lows, closes, opens, atrs=None):
            ts = pd.Timestamp(t)
            if ts.hour == 21:  # rollover
                for m, p in self.pos.items():
                    if not p:
                        continue
                    kind = "fx" if PROFILE[m]["fx_swap"] else "crypto"
                    nights = 3 if (kind == "fx" and ts.dayofweek == 2) else 1
                    fee = abs(p["units"]) * closes[m] * swap[kind] * nights
                    self.realized -= fee
                    p["funding"] -= fee
            return super().close_bar(t, highs, lows, closes, opens, atrs)

    return BrokerBook, stats


def run(scn):
    BrokerBook, stats = setup(scn)
    engine.Book = BrokerBook
    quant.STRATEGIES["trend_4h"] = dict(quant.STRATEGIES["trend_4h"], markets=MARKETS)
    r = quant.evaluate("trend_4h")
    o = r["oos"]
    return scn, {"return_pct": round(o["return_pct"], 1), "sharpe": round(o["sharpe"], 2), "max_dd_pct": round(o["max_dd_pct"], 1),
                 "trades": o["trades"], "costs_x2_return_pct": round(r["costs_doubled"]["return_pct"], 1),
                 "skipped_min_lot_pct": round(100 * stats["skipped_min_lot"] / max(stats["signals"], 1), 1),
                 "by_market": r["by_market"], "passes": r["passes"], "mc_prob_loss_pct": r["monte_carlo"].get("prob_loss_pct")}


if __name__ == "__main__":
    names = sys.argv[1:] or list(SCENARIOS)
    with ProcessPoolExecutor(min(4, len(names))) as pool:
        out = dict(pool.map(run, names))
    for k, v in out.items():
        print(k, json.dumps(v))
    Path("reports/mt5_exness.json").write_text(json.dumps({"profile_estimates": PROFILE, "scenarios": SCENARIOS,
                                                           "results": out}, indent=2))


# ---------------------------------------------------------------- every idea, on Exness
def _eval_strategy(args):
    scn, name = args
    BrokerBook, stats = setup(scn)
    engine.Book = BrokerBook
    s = quant.STRATEGIES[name]
    mk = [m for m in s["markets"] if m in PROFILE]
    if not mk:
        return name, None
    quant.STRATEGIES[name] = dict(s, markets=mk)
    r = quant.evaluate(name)
    o = r["oos"]
    return name, {"passes": r["passes"], "gates": r["gates"], "score": r["score"]["total"],
                  "return_pct": round(o["return_pct"], 1), "sharpe": round(o["sharpe"], 2), "max_dd_pct": round(o["max_dd_pct"], 1),
                  "trades": o["trades"], "costs_x2_return_pct": round(r["costs_doubled"]["return_pct"], 1),
                  "hold_sharpe": round(r["buy_and_hold"]["sharpe"], 2), "mc_prob_loss_pct": r["monte_carlo"].get("prob_loss_pct"),
                  "regimes": r["regime_sharpe"], "by_market": r["by_market"], "skipped_min_lot_pct":
                  round(100 * stats["skipped_min_lot"] / max(stats["signals"], 1), 1), "last_fold": r["folds"][-1]}


def all_strategies(scn="cent_swap_mid"):
    names = [n for n in quant.STRATEGIES if n != "pricer_gap"]
    with ProcessPoolExecutor(4) as pool:
        res = dict(pool.map(_eval_strategy, [(scn, n) for n in names]))
    res = {k: v for k, v in res.items() if v}
    Path(f"reports/mt5_exness_all_{scn}.json").write_text(json.dumps(res, indent=2, default=str))
    for k, v in sorted(res.items(), key=lambda kv: (kv[1]["passes"], kv[1]["sharpe"]), reverse=True):
        print(f"{k:22} pass={v['passes']!s:5} ret={v['return_pct']:7.1f}% sharpe={v['sharpe']:5.2f} dd={v['max_dd_pct']:6.1f}% "
              f"trades={v['trades']:5} x2={v['costs_x2_return_pct']:6.1f}% hold_sharpe={v['hold_sharpe']:.2f} "
              f"MCloss={v['mc_prob_loss_pct']} markets={ {m: round(x['sum'], 1) for m, x in v['by_market'].items()} }")
    return res
