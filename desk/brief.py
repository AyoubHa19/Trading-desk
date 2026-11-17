"""Morning brief data: writes reports/brief.md (facts only; the 07:30 session words the message).

Run:  python -m desk.brief
"""

import json
from pathlib import Path

import pandas as pd

from desk import config as C
from desk import okx

STATE, REPORTS = Path("state"), Path("reports")


def market_lines():
    rows = []
    for m, spec in C.MARKETS.items():
        try:
            df = okx.candles_1h(spec["okx"], 30)
            last, prev = df["close"].iloc[-1], df["close"].iloc[-25]
            if spec["okx"] == "USDT-EUR":
                last, prev = 1 / last, 1 / prev
            rows.append(f"{m} {(f'{last:,.2f}' if last > 10 else f'{last:.4f}')} ({100 * (last / prev - 1):+.2f}% 24h, OKX {spec['okx']}, {df.index[-1]:%Y-%m-%d %H:%M} UTC)")
        except Exception as e:  # never invent a price
            rows.append(f"{m}: price unavailable ({e.__class__.__name__})")
    return rows


def main():
    now = pd.Timestamp.now(tz="UTC")
    since = now - pd.Timedelta(hours=24)
    out = [f"# Brief data {now.tz_convert(C.TIMEZONE):%Y-%m-%d %H:%M} New York", "", "## Markets", *[f"- {x}" for x in market_lines()], ""]

    res = {r["name"]: r for r in json.loads((REPORTS / "quant_results.json").read_text())}
    cfg = json.loads((STATE / "strategy.json").read_text())
    ledgers = json.loads((STATE / "ledgers.json").read_text()) if (STATE / "ledgers.json").exists() else {}
    eq = pd.read_csv(STATE / "equity.csv", parse_dates=["bar_utc"]) if (STATE / "equity.csv").exists() else pd.DataFrame()

    out.append("## Champion and challengers")
    for role, c in cfg["ledgers"].items():
        if not c:
            out.append(f"- {role}: none qualified")
            continue
        r, b = res[c["name"]], ledgers.get(role, {}).get("book", {})
        trades = [t for t in b.get("trades", []) if pd.Timestamp(t["exit_time"]) >= since]
        pnl24 = sum(t["pnl"] for t in trades)
        out.append(f"- {role} {c['name']} ({'passed' if c['passed_gates'] else 'shadow, failed gates'}): "
                   f"backtest OOS {r['oos']['return_pct']:.1f}% / Sharpe {r['oos']['sharpe']:.2f} / maxDD {r['oos']['max_dd_pct']:.1f}%; "
                   f"paper realized ${b.get('realized', C.START_CAPITAL):.2f}, closed-trade P&L 24h ${pnl24:+.2f} ({len(trades)} trades)")
        for t in trades:
            out.append(f"  - {t['market']} {'LONG' if t['dir'] > 0 else 'SHORT'} {t['entry']:.4f}→{t['exit']:.4f} ${t['pnl']:+.2f} ({t['reason']})")
        for m, p in (b.get("pos") or {}).items():
            if p:
                out.append(f"  - open {m} {'LONG' if p['units'] > 0 else 'SHORT'} @ {p['entry']:.4f} stop {p['stop']:.4f} risk ${p['risk']:.2f}")
    if len(eq):
        last = eq.sort_values("bar_utc").groupby("ledger").tail(1)
        out.append("- last marked equity: " + ", ".join(f"{r.ledger} ${r.equity:.2f}" for r in last.itertuples()))
    out.append("")

    out.append("## Risk halts (last 24h)")
    halts = []
    if (STATE / "risk_log.csv").exists():
        log = pd.read_csv(STATE / "risk_log.csv")
        log = log[pd.to_datetime(log["time_utc"], format="mixed", utc=True) >= since]
        halts = [f"- {r.time_utc[:16]} {r.event}" for r in log.itertuples()]
    out += halts or ["- none"]
    (REPORTS / "brief.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
