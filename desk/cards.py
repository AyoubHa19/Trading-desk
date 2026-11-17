"""Write reports/strategy_cards.md from reports/quant_results.json.

Run:  python -m desk.cards
"""

import json
from pathlib import Path

from desk.strategies import STRATEGIES
import desk.quant  # noqa: F401  (registers pricer_gap)

# Hand-written judgement per idea: where it breaks, how we'd see it fading, why it could fail.
JUDGEMENT = {
    "trend_4h": {
        "breaks_in": "Sideways chop: the 'chop' regime Sharpe is negative; whipsaws cost 2 fees each time.",
        "fading_sign": "Rolling 90-day paper Sharpe < 0 while BTC moves > 10%/month (trends exist but we miss them).",
        "fail": "Crypto trend-following is crowded; in 2026 every CTA and bot runs it. Most of the profit comes from a few big moves and from trades closed by the daily halt rule, so a calm year can bleed for months. The edge was 16% instead of 53% under a slightly different bookkeeping of the training trades: the SIZE of the result is fragile even if the sign held for every lookback tested. Gold here was tested on PAXG (a crypto token), but the bot uses OKX's XAU perp.",
    },
    "funding_reversion": {
        "breaks_in": "Strong one-way bull or bear runs where crowded funding stays extreme for weeks.",
        "fading_sign": "Funding spikes stop mean-reverting within 72h; losses cluster in bear regime (Sharpe -1.28 there).",
        "fail": "Only 84 trades in 3 years; the result could be luck. It does not beat buy-and-hold on Sharpe.",
    },
    "lead_lag": {
        "breaks_in": "Fast markets where ETH/SOL react within the same minute as BTC (the usual case today).",
        "fading_sign": "Average R per trade drops below the round-trip cost.",
        "fail": "It dies when costs double (-5.8%): the edge is about the same size as the fees. Arbitrage bots close this gap in seconds, not hours.",
    },
    "vol_breakout": {
        "breaks_in": "Bull regime (Sharpe -2.17): fake breakouts out of quiet ranges.",
        "fading_sign": "Drawdown beyond 30%.",
        "fail": "-38% with costs doubled; 31% drawdown. Rejected.",
    },
    "liquidation_reversal": {
        "breaks_in": "Real crashes where forced selling continues for hours.",
        "fading_sign": "Already negative out-of-sample.",
        "fail": "Lost money out-of-sample. The 'forced seller' story is true but the bounce is already taken within the same hour by faster players.",
    },
    "mean_reversion": {
        "breaks_in": "Everywhere: costs on PAXG/EURUSDT spot (0.3% round trip) are bigger than the moves.",
        "fading_sign": "Never traded: the cost check blocked every trade.",
        "fail": "No trade can pay its costs. EUR/USD and gold need a real FX/CFD broker with ~0.01% spreads, not crypto proxies.",
    },
    "pricer_gap": {
        "breaks_in": "Everywhere: the Pricer has ~0 out-of-sample predictive power (rank IC ~0.0-0.06).",
        "fading_sign": "Already negative.",
        "fail": "-30% out-of-sample. The fair-value model is not good enough to trade on its own.",
    },
}


def fmt(x, unit=""):
    return f"{x:.2f}{unit}" if isinstance(x, (int, float)) else str(x)


def main():
    results = json.loads(Path("reports/quant_results.json").read_text())
    strategy = json.loads(Path("state/strategy.json").read_text()) if Path("state/strategy.json").exists() else {"ledgers": {}}
    roles = {v["name"]: k for k, v in strategy["ledgers"].items() if v}
    out = ["# Strategy cards", "",
           "All numbers are OUT-OF-SAMPLE walk-forward results, 2023-12-01 → 2026-11-16, $100 start, after fees,",
           "slippage (estimated) and funding. Source data: data.binance.vision (see data/manifest.csv), cross-checked with OKX.",
           "Buy & hold = equal-weight hold of the same markets over the same period.", ""]
    for r in results:
        s, j, o, bh = STRATEGIES[r["name"]], JUDGEMENT[r["name"]], r["oos"], r["buy_and_hold"]
        role = roles.get(r["name"], "rejected" if not r["passes"] else "standby")
        last = r["folds"][-1]
        out += [
            f"## {r['name']} — {role.upper()} — score {r['score']['total']}/5 — {'PASSED all gates' if r['passes'] else 'FAILED gates'}",
            "",
            f"- **Idea:** {s['idea']}",
            f"- **Fair value vs price:** {s['cause']}.",
            f"- **Who loses:** {s['losing_side']}",
            f"- **Rules:** entry/exit = `{r['name']}` in desk/strategies.py; stop = {last['params'].get('stop_atr')} × ATR(24h); "
            f"latest params {last['params']}; markets traded {r['markets_traded']}.",
            f"- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.",
            f"- **Results after costs:** return {fmt(o['return_pct'], '%')} (CAGR {fmt(o.get('cagr_pct', 0), '%')}), Sharpe {fmt(o['sharpe'])}, "
            f"max drawdown {fmt(o['max_dd_pct'], '%')}, {o['trades']} trades, win rate {fmt(o.get('win_rate_pct', 0), '%')}, "
            f"worst losing streak {o.get('worst_losing_streak', '-')}",
            f"- **Buy & hold, same markets:** return {fmt(bh['return_pct'], '%')}, Sharpe {fmt(bh['sharpe'])}, max drawdown {fmt(bh['max_dd_pct'], '%')}",
            f"- **Costs doubled:** return {fmt(r['costs_doubled']['return_pct'], '%')}, Sharpe {fmt(r['costs_doubled']['sharpe'])}",
            f"- **Worst month:** {o.get('worst_month', '-')} ({fmt(o.get('worst_month_pct', 0), '%')})",
            f"- **Bull / bear / chop Sharpe:** {r['regime_sharpe']}",
            f"- **Monte Carlo (5000 resamples of the trades):** {r['monte_carlo']}",
            f"- **Daily halts triggered:** {r['halts']}",
            f"- **Market that breaks it:** {j['breaks_in']}",
            f"- **Earliest sign it's fading:** {j['fading_sign']}",
            f"- **Gates:** {r['gates']}",
            f"- **Score detail (1-5):** {r['score']}",
            "",
            f"**WHY THIS COULD FAIL:** {j['fail']}",
            "",
        ]
    Path("reports/strategy_cards.md").write_text("\n".join(out))
    print("wrote reports/strategy_cards.md")


if __name__ == "__main__":
    main()
