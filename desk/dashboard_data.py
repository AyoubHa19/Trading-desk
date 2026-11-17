"""Export the desk's state and research as small JSON files for the dashboard.

Writes reports/dashboard/*.json, each {"rows": [...], "meta": [...]}.
Live prices come from OKX's public API at export time (source + timestamp in each row).

Run:  python -m desk.dashboard_data
"""

import json
from pathlib import Path

import pandas as pd

from desk import config as C
from desk import okx

OUT = Path("reports/dashboard")
CODE = Path(__file__).read_text()


def write(name, rows, inputs):
    OUT.mkdir(parents=True, exist_ok=True)
    meta = [{"label": "dashboard_data.py", "value": CODE, "type": "code", "lang": "python"},
            {"label": "Input", "value": inputs}]
    (OUT / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta}, default=str))


def r2(x, n=2):
    return None if x is None or pd.isna(x) else round(float(x), n)


def main():
    now = pd.Timestamp.now(tz="UTC").floor("s")
    cfg = json.loads(Path("state/strategy.json").read_text())
    ledgers = json.loads(Path("state/ledgers.json").read_text())
    results = {r["name"]: r for r in json.loads(Path("reports/quant_results.json").read_text())}
    pricer = json.loads(Path("reports/pricer.json").read_text())

    # live prices
    px, chg = {}, {}
    for m, spec in C.MARKETS.items():
        df = okx.candles_1h(spec["okx"], 30)
        last, prev = float(df["close"].iloc[-1]), float(df["close"].iloc[-25])
        if spec["okx"] == "USDT-EUR":
            last, prev = 1 / last, 1 / prev
        px[m], chg[m] = last, 100 * (last / prev - 1)

    # ledgers + positions
    led_rows, pos_rows = [], []
    for role, c in cfg["ledgers"].items():
        if not c:
            continue
        b = ledgers.get(role, {}).get("book", {})
        unreal = 0.0
        n_open = 0
        for m, p in (b.get("pos") or {}).items():
            if not p:
                continue
            u = p["units"] * (px[m] - p["entry"])
            unreal += u
            n_open += 1
            pos_rows.append({"key": f"{role}:{m}", "role": role, "strategy": c["name"], "market": m,
                             "side": "LONG" if p["units"] > 0 else "SHORT", "size_usd": r2(abs(p["units"]) * p["entry"]),
                             "entry": r2(p["entry"], 4), "price": r2(px[m], 4), "stop": r2(p["stop"], 4),
                             "risk_usd": r2(p["risk"]), "unrealized_usd": r2(u), "opened_utc": p["t"],
                             "price_source": f"OKX {C.MARKETS[m]['okx']} {now}"})
        g = b.get("guard", {})
        trades = b.get("trades", [])
        led_rows.append({"role": role, "strategy": c["name"], "passed_gates": "yes" if c["passed_gates"] else "no",
                         "realized_usd": r2(b.get("realized", C.START_CAPITAL)), "unrealized_usd": r2(unreal),
                         "equity_usd": r2(b.get("realized", C.START_CAPITAL) + unreal), "open_positions": n_open,
                         "closed_trades": len(trades), "halted_today": "yes" if g.get("halted") else "no",
                         "losing_streak": g.get("streak", 0), "markets": ", ".join(c["markets"]), "as_of_utc": str(now)})
    write("ledgers", led_rows, "state/strategy.json, state/ledgers.json, OKX live prices")
    write("positions", pos_rows, "state/ledgers.json, OKX live prices")

    eq = pd.read_csv("state/equity.csv") if Path("state/equity.csv").exists() else pd.DataFrame()
    write("paper_equity", eq.to_dict("records"), "state/equity.csv (equity at each hourly bar close)")

    trades = [dict(t, role=role) for role, l in ledgers.items() for t in l["book"]["trades"]]
    write("paper_trades", trades, "state/ledgers.json")

    # research
    res_rows = []
    roles = {c["name"]: role for role, c in cfg["ledgers"].items() if c}
    for name, r in results.items():
        o = r["oos"]
        res_rows.append({"strategy": name, "role": roles.get(name, "rejected"), "passed": "yes" if r["passes"] else "no",
                         "score": r["score"]["total"], "return_pct": r2(o["return_pct"], 1), "sharpe": r2(o["sharpe"]),
                         "max_dd_pct": r2(o["max_dd_pct"], 1), "trades": o["trades"],
                         "costs_x2_return_pct": r2(r["costs_doubled"]["return_pct"], 1),
                         "hold_sharpe": r2(r["buy_and_hold"]["sharpe"]), "hold_return_pct": r2(r["buy_and_hold"]["return_pct"], 1)})
    write("research", res_rows, "reports/quant_results.json (walk-forward 2023-12-01 to 2026-11-16)")

    curves = []
    for name in [c["name"] for c in cfg["ledgers"].values() if c]:
        p = Path(f"data/processed/oos_equity_{name}.parquet")
        if p.exists():
            e = pd.read_parquet(p)["equity"].resample("D").last().dropna()
            curves += [{"date": str(d.date()), "series": name, "equity": r2(v)} for d, v in e.items()]
    btc = pd.read_parquet("data/processed/BTC.parquet")["close"].loc["2023-12-01":].resample("D").last()
    curves += [{"date": str(d.date()), "series": "BTC buy & hold", "equity": r2(100 * v / btc.iloc[0])} for d, v in btc.items()]
    write("oos_equity", curves, "data/processed/oos_equity_*.parquet, BTC closes from data.binance.vision")

    # markets
    fv = {x["market"]: x for x in pricer["fair_value_now"]}
    mk = [{"market": m, "okx_instrument": C.MARKETS[m]["okx"], "price": r2(px[m], 4), "change_24h_pct": r2(chg[m]),
           "model_gap_pct": fv[m]["gap_pct"], "fair_value_as_of_utc": fv[m]["as_of_utc"],
           "pricer_rank_ic": pricer["markets"][m]["oos_rank_ic_daily_nonoverlap"], "price_as_of_utc": str(now)} for m in C.MARKETS]
    write("markets", mk, "OKX public candles; reports/pricer.json")

    log = pd.read_csv("state/risk_log.csv").to_dict("records") if Path("state/risk_log.csv").exists() else []
    write("risk_log", log, "state/risk_log.csv")
    print("wrote", sorted(p.name for p in OUT.glob("*.json")))


if __name__ == "__main__":
    main()
