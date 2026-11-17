"""Hour-by-hour portfolio simulation, shared by the backtest AND the paper bot.

Timing (no lookahead):
  * the target for bar t is decided at the close of bar t,
  * it is executed at the OPEN of bar t+1           -> Book.open_bar
  * stops are checked against bar t+1's high/low,
  * equity is marked at bar t+1's close             -> Book.close_bar
Costs: fee + slippage on every entry and exit; funding paid/received on perps.
Risk: desk/risk.py (1% per trade, 5% per theme, 3x leverage, thin book,
cost check, -3% day / 3-loss streak kill-switch).

The backtest calls the Book once per historical bar; the bot calls the very
same Book once per live hour and saves it to state/*.json in between.
"""

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from desk import config as C
from desk.risk import DayGuard, position_size


@dataclass
class Result:
    equity: pd.Series
    trades: pd.DataFrame
    halts: list


def cost_rate(market: str, mult: float = 1.0) -> float:
    kind = "perp" if C.MARKETS[market]["hist"][0].startswith("futures") else "spot"
    return (C.COSTS[kind]["fee"] + C.COSTS[kind]["slippage"]) * mult


class Book:
    def __init__(self, markets, equity=C.START_CAPITAL, cost_mult=1.0):
        self.markets = list(markets)
        self.cost = {m: cost_rate(m, cost_mult) for m in self.markets}
        self.theme = {m: C.MARKETS[m]["theme"] for m in self.markets}
        self.realized = float(equity)
        self.pos = {m: None for m in self.markets}
        self.blocked = {m: 0 for m in self.markets}   # direction we were stopped out of
        self.guard = DayGuard()
        self.trades = []
        self._halted_at_open = False

    # ------------------------------------------------------------ helpers
    def equity(self, px) -> float:
        return self.realized + sum(p["units"] * (px[m] - p["entry"]) for m, p in self.pos.items() if p)

    def _close(self, m, t, price, reason):
        p = self.pos[m]
        cost = abs(p["units"]) * price * self.cost[m]
        move = p["units"] * (price - p["entry"])
        self.realized += move - cost
        pnl = move - cost - p["entry_cost"] + p["funding"]
        self.trades.append({"market": m, "dir": int(np.sign(p["units"])), "entry_time": p["t"], "exit_time": t,
                            "entry": p["entry"], "exit": price, "units": p["units"], "risk": p["risk"],
                            "pnl": pnl, "R": pnl / p["risk"] if p["risk"] else 0.0, "reason": reason,
                            "why": p.get("why")})
        self.guard.record_trade(pnl)
        self.pos[m] = None

    def close_all(self, t, px, reason):
        for m in self.markets:
            if self.pos[m]:
                self._close(m, t, px[m], reason)

    # ------------------------------------------------------------ the hour
    def open_bar(self, t, ny_day, opens, funding, decisions, prev_close, stop_atr, risk_frac, why=None):
        """decisions[m] = (target, atr, quote_vol_24h) known at the previous close.
        why[m] (optional, bot only): the facts behind the decision, saved on the position."""
        self.guard.new_bar(ny_day, self.equity(prev_close))
        halted = self._halted_at_open = self.guard.halted

        for m in self.markets:
            tgt, atr, qv = decisions[m]
            want = 0 if halted or tgt is None or (isinstance(tgt, float) and math.isnan(tgt)) else int(tgt)
            if not C.MARKETS[m]["can_short"]:
                want = max(want, 0)
            if self.blocked[m] and want == self.blocked[m]:
                want = 0                       # no re-entry after a stop until the signal resets
            elif want != self.blocked[m]:
                self.blocked[m] = 0
            p = self.pos[m]
            have = int(np.sign(p["units"])) if p else 0
            if p and have != want:
                self._close(m, t, opens[m], "signal")
            if want != 0 and not self.pos[m]:
                eq = self.equity(opens)
                gross = sum(abs(q["units"]) * opens[k] for k, q in self.pos.items() if q)
                theme_risk = sum(q["risk"] for k, q in self.pos.items() if q and self.theme[k] == self.theme[m])
                stop_dist = stop_atr[m] * atr if atr else float("nan")
                units, risk_amt = position_size(eq, risk_frac[m], opens[m], stop_dist, gross, theme_risk, qv, self.cost[m])
                if units > 0:
                    entry = opens[m]
                    cost = units * entry * self.cost[m]
                    self.realized -= cost
                    self.pos[m] = {"units": want * units, "entry": entry, "risk": risk_amt, "t": t,
                                   "stop": entry - want * stop_dist, "entry_cost": cost, "funding": 0.0}
                    if why and why.get(m):
                        self.pos[m]["why"] = dict(why[m], stop_atr=stop_atr[m], atr=atr, risk_pct=100 * risk_frac[m])

        for m in self.markets:          # funding on perps held through a funding timestamp
            p = self.pos[m]
            if p and funding.get(m):
                pay = -p["units"] * opens[m] * funding[m]
                self.realized += pay
                p["funding"] += pay

    def close_bar(self, t, highs, lows, closes, opens) -> float:
        for m in self.markets:          # stops; a gap through the stop fills at the (worse) open
            p = self.pos[m]
            if not p:
                continue
            if p["units"] > 0 and lows[m] <= p["stop"]:
                self.blocked[m] = 1
                self._close(m, t, min(opens[m], p["stop"]), "stop")
            elif p["units"] < 0 and highs[m] >= p["stop"]:
                self.blocked[m] = -1
                self._close(m, t, max(opens[m], p["stop"]), "stop")
        eq = self.equity(closes)
        if not self._halted_at_open and self.guard.check(eq, t):
            self.close_all(t, closes, "halt")
            eq = self.realized
        return eq

    # ------------------------------------------------------------ save/load (bot)
    def to_dict(self):
        return {"markets": self.markets, "realized": self.realized, "pos": self.pos, "blocked": self.blocked,
                "guard": asdict(self.guard), "trades": self.trades, "cost": self.cost}

    @classmethod
    def from_dict(cls, d):
        b = cls(d["markets"], d["realized"])
        b.cost, b.pos, b.blocked, b.trades = d["cost"], d["pos"], d["blocked"], d["trades"]
        b.guard = DayGuard(**d["guard"])
        return b


def run(data, feats, targets, stop_atr, risk_frac, start, end,
        start_equity=C.START_CAPITAL, cost_mult=1.0) -> Result:
    """Backtest. targets: {market: Series of -1/0/1}; stop_atr / risk_frac: {market: float}."""
    markets = list(targets)
    idx = data["BTC"].loc[start:end].index
    if len(idx) < 2:
        return Result(pd.Series(dtype=float), pd.DataFrame(), [])
    ny_day = [str(d) for d in idx.tz_convert(C.TIMEZONE).date]

    # Plain Python lists are much faster than pandas inside the loop.
    A = {}
    for m in markets:
        d = data[m].reindex(idx).ffill()
        f = feats[m].reindex(idx).ffill()
        A[m] = {"o": d["open"].tolist(), "h": d["high"].tolist(), "l": d["low"].tolist(), "c": d["close"].tolist(),
                "fund": d["funding"].fillna(0.0).tolist() if "funding" in d else [0.0] * len(idx),
                "atr": f["atr"].tolist(), "qv": f["quote_vol_24h"].tolist(),
                "tgt": targets[m].reindex(idx).fillna(0.0).tolist()}

    book = Book(markets, start_equity, cost_mult)
    eq_curve = [float(start_equity)]
    for i in range(1, len(idx)):
        col = lambda k, j=i: {m: A[m][k][j] for m in markets}  # noqa: E731
        decisions = {m: (A[m]["tgt"][i - 1], A[m]["atr"][i - 1], A[m]["qv"][i - 1]) for m in markets}
        opens = col("o")
        book.open_bar(idx[i], ny_day[i], opens, col("fund"), decisions, col("c", i - 1), stop_atr, risk_frac)
        eq_curve.append(book.close_bar(idx[i], col("h"), col("l"), col("c"), opens))

    # End of the window: close what is still open so every trade is counted
    # (and paid for) inside the window it belongs to.
    book.close_all(idx[-1], {m: A[m]["c"][-1] for m in markets}, "end")
    eq_curve[-1] = book.realized
    return Result(pd.Series(eq_curve, index=idx), pd.DataFrame(book.trades), book.guard.log)


def stats(equity: pd.Series, trades: pd.DataFrame) -> dict:
    if equity.empty:
        return {"return_pct": 0.0, "sharpe": 0.0, "max_dd_pct": 0.0, "trades": 0}
    r = equity.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 86400), 1e-9)
    total = equity.iloc[-1] / equity.iloc[0] - 1
    dd = (equity / equity.cummax() - 1).min()
    sharpe = r.mean() / r.std() * math.sqrt(8760) if r.std() > 0 else 0.0
    out = {
        "return_pct": 100 * total,
        "cagr_pct": 100 * ((1 + total) ** (1 / years) - 1) if total > -1 else -100.0,
        "sharpe": sharpe,
        "max_dd_pct": 100 * dd,
        "trades": int(len(trades)),
    }
    if len(trades):
        losses = (trades["pnl"] < 0).astype(int)
        streak = losses.groupby((losses != losses.shift()).cumsum()).cumsum().max()
        out.update({
            "win_rate_pct": 100 * (trades["pnl"] > 0).mean(),
            "avg_R": trades["R"].mean(),
            "worst_losing_streak": int(streak),
        })
    monthly = equity.resample("ME").last()
    monthly = pd.concat([equity.iloc[:1], monthly]).pct_change().dropna()
    if len(monthly):
        out["worst_month_pct"] = 100 * monthly.min()
        out["worst_month"] = str(monthly.idxmin().date())[:7]
    return out
