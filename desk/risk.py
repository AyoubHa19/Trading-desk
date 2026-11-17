"""Risk rules shared by the backtest engine AND the live paper bot.

Keeping them in one file means the bot follows exactly the rules we tested.
"""

import math
from dataclasses import dataclass, field

from desk import config as C

MAX_COST_SHARE_OF_RISK = 0.25


def kelly_risk(r_multiples: list[float]) -> float:
    """Fraction of equity to RISK per trade, from past trade results in R.

    R = trade P&L / amount risked. Growth-optimal (Kelly) risk is about
    mean(R) / mean(R^2). We use a quarter of it.
    Capped at RISK_PER_TRADE. No edge (mean <= 0) or too few trades -> 0, i.e. do not trade.
    """
    if len(r_multiples) < 20:
        return 0.0
    m = sum(r_multiples) / len(r_multiples)
    m2 = sum(r * r for r in r_multiples) / len(r_multiples)
    if m <= 0 or m2 == 0:
        return 0.0
    return min(C.RISK_PER_TRADE, C.KELLY_FRACTION * m / m2)


def position_size(equity: float, risk_frac: float, price: float, stop_dist: float,
                  gross_open: float, theme_risk_open: float, quote_vol_24h: float,
                  cost_rate: float = 0.0) -> tuple[float, float]:
    """Return (units, risk_amount). 0 units means: skip the trade.

    Caps, in order: 1% risk per trade, 5% risk per theme, 3x gross leverage,
    thin book (max 1% of the market's average hourly volume), $5 minimum order,
    and costs: if the round-trip fees+slippage eat more than 25% of what we
    risk, the trade cannot pay for itself -> skip.
    """
    if equity <= 0 or price <= 0 or not stop_dist or math.isnan(stop_dist) or stop_dist <= 0:
        return 0.0, 0.0
    risk_amt = min(risk_frac, C.RISK_PER_TRADE) * equity
    risk_amt = min(risk_amt, C.RISK_PER_THEME * equity - theme_risk_open)
    if risk_amt <= 0:
        return 0.0, 0.0
    units = risk_amt / stop_dist
    max_notional = C.MAX_LEVERAGE * equity - gross_open
    if quote_vol_24h and not math.isnan(quote_vol_24h):
        max_notional = min(max_notional, 0.01 * quote_vol_24h)
    if units * price > max_notional:
        units = max(max_notional, 0.0) / price
    if units * price < C.MIN_ORDER_USD:
        return 0.0, 0.0
    risk_amt = units * stop_dist
    if 2 * cost_rate * units * price > MAX_COST_SHARE_OF_RISK * risk_amt:
        return 0.0, 0.0
    return units, risk_amt


@dataclass
class DayGuard:
    """Daily kill-switch: -3% on the New York day, or 3 losing trades in a row."""
    day: object = None
    day_start_equity: float = 0.0
    streak: int = 0
    halted: bool = False
    reason: str = ""
    log: list = field(default_factory=list)

    def new_bar(self, ny_day, equity: float):
        if ny_day != self.day:
            self.day, self.day_start_equity = ny_day, equity
            if self.halted:
                self.streak = 0
            self.halted, self.reason = False, ""

    def record_trade(self, pnl: float):
        self.streak = self.streak + 1 if pnl < 0 else 0

    def check(self, equity: float, when) -> bool:
        """Return True if trading must stop now (and stay stopped until the next NY day)."""
        if self.halted:
            return True
        if equity <= self.day_start_equity * (1 - C.DAILY_LOSS_STOP):
            self.halted, self.reason = True, f"daily loss {equity / self.day_start_equity - 1:.2%}"
        elif self.streak >= C.MAX_LOSING_STREAK:
            self.halted, self.reason = True, f"{self.streak} losing trades in a row"
        if self.halted:
            self.log.append((str(when), self.reason))
        return self.halted


def data_looks_wrong(price: float, last_price: float, atr: float, age_minutes: float) -> str:
    """Sanity checks before any order. Returns a reason, or '' if data is fine."""
    if price is None or price <= 0 or math.isnan(price):
        return "bad price"
    if age_minutes > 90:
        return f"stale data ({age_minutes:.0f} min old)"
    if last_price and atr and abs(price - last_price) > 15 * atr:
        return f"price jumped {abs(price / last_price - 1):.1%} (>15 ATR) - possible bad print"
    return ""
