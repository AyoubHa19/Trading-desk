"""Desk settings in one place. Change numbers here, not inside the code."""

from datetime import date

# ---- Research window: 4 years of history ----
HISTORY_START = date(2022, 11, 1)
HISTORY_END = date(2026, 11, 16)  # last full day downloaded

# ---- Markets ----
# key: our name for the market
# hist: where the 4-year history comes from (Binance public data dump)
# okx: the instrument the paper bot prices and "trades" on OKX
# can_short: perps can go short; spot proxies are long-only
MARKETS = {
    "BTC": {"hist": ("futures/um", "BTCUSDT"), "okx": "BTC-USDT-SWAP", "can_short": True, "theme": "crypto"},
    "ETH": {"hist": ("futures/um", "ETHUSDT"), "okx": "ETH-USDT-SWAP", "can_short": True, "theme": "crypto"},
    "SOL": {"hist": ("futures/um", "SOLUSDT"), "okx": "SOL-USDT-SWAP", "can_short": True, "theme": "crypto"},
    # Gold: PAXG spot has 4 years; the real XAU perp on Binance only starts 2025-12.
    "GOLD": {"hist": ("spot", "PAXGUSDT"), "okx": "XAU-USDT-SWAP", "can_short": True, "theme": "gold"},
    # EUR/USD: no FX broker on Binance/OKX. EURUSDT spot is the proxy (long-only).
    "EUR": {"hist": ("spot", "EURUSDT"), "okx": "USDT-EUR", "can_short": False, "theme": "fx"},
}

# Perps with funding / open-interest history
PERPS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---- Costs (per side, as a fraction of notional) ----
# OKX regular tier, taker: swaps 0.05%, spot 0.10%. Slippage is our estimate (labelled).
COSTS = {
    "perp": {"fee": 0.0005, "slippage": 0.0002},
    "spot": {"fee": 0.0010, "slippage": 0.0005},  # thin books (PAXG, EUR) -> more slippage
}

# ---- Money and risk (from the owner's answers) ----
START_CAPITAL = 100.0          # USD, paper
RISK_PER_TRADE = 0.01          # max 1% of equity at risk per trade
RISK_PER_THEME = 0.05          # max 5% per theme (BTC/ETH/SOL count as one bet)
KELLY_FRACTION = 0.25          # quarter Kelly
DAILY_LOSS_STOP = 0.03         # stop for the day after -3% (New York day)
MAX_LOSING_STREAK = 3          # stop for the day after 3 losing trades in a row
MAX_LEVERAGE = 3.0             # hard cap on notional / equity
MIN_ORDER_USD = 5.0            # below this the exchange rejects the order
TIMEZONE = "America/New_York"

# ---- Promotion rules ----
CHALLENGER_DAYS_TO_PROMOTE = 7  # challenger replaces champion after 7 winning paper days
