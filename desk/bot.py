"""Paper-trading bot. Runs once an hour (GitHub Actions), never places real orders.

Each run:
  1. reads state/strategy.json (champion + 2 challengers) and state/ledgers.json,
  2. downloads recent OKX public candles + funding (no keys),
  3. Risk checks the data; if anything looks wrong, NOTHING is changed this hour,
  4. for each ledger, replays the hours since the last run through the same
     Book used in the backtest (stops, funding, -3% day / 3-loss halt), then
     makes this hour's decision and fills it at the live OKX price,
  5. writes state/ledgers.json, state/equity.csv, state/risk_log.csv, state/status.md.

Run:  python -m desk.bot
"""

import csv
import json
from pathlib import Path

import pandas as pd

from desk import config as C
from desk import okx
from desk.engine import Book
from desk.features import add_features
from desk.risk import data_looks_wrong
from desk.strategies import STRATEGIES

STATE = Path("state")
MAX_CATCH_UP_HOURS = 72
HISTORY_HOURS = 900  # enough for 30-day volatility + 20-day trend


def read_json(p: Path, default):
    return json.loads(p.read_text()) if p.exists() else default


def append_csv(p: Path, header, rows):
    new = not p.exists()
    with p.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)


def fetch_market(m: str) -> pd.DataFrame:
    inst = C.MARKETS[m]["okx"]
    df = okx.candles_1h(inst, HISTORY_HOURS)
    if inst == "USDT-EUR":  # OKX quotes EUR per USDT; we want USD (USDT) per EUR
        o, h, l, c = 1 / df["open"], 1 / df["low"], 1 / df["high"], 1 / df["close"]
        df["open"], df["high"], df["low"], df["close"] = o, h, l, c
    if inst.endswith("-SWAP") and m != "GOLD":
        df["funding"] = okx.funding_history(inst).reindex(df.index).fillna(0.0)
    return df


def check_data(m: str, df: pd.DataFrame, feats: pd.DataFrame, now: pd.Timestamp) -> str:
    done = df[df["confirmed"]]
    if len(done) < 800:
        return f"only {len(done)} hourly bars"
    gaps = done.index.to_series().diff().dropna()
    if (gaps.iloc[-48:] != pd.Timedelta(hours=1)).any():
        return "missing hours in the last 48h"
    age = (now - (done.index[-1] + pd.Timedelta(hours=1))).total_seconds() / 60
    return data_looks_wrong(float(done["close"].iloc[-1]), float(done["close"].iloc[-2]),
                            float(feats["atr"].loc[done.index[-2]]), age)


def step_ledger(role, cfg, led, data, feats, live_px, now):
    """Advance one ledger to the current hour. Returns (ledger, equity rows, notes)."""
    markets = cfg["markets"]
    strat = STRATEGIES[cfg["name"]]
    params = cfg["params"]
    targets = {m: strat["fn"](data[m], feats[m], market=m, **params) for m in markets}
    stop_atr = {m: params["stop_atr"] for m in markets}
    notes, rows = [], []

    # New or changed strategy config: close the old book at live prices, keep the money.
    if not led or led.get("config") != cfg:
        equity = C.START_CAPITAL
        if led:
            old = Book.from_dict(led["book"])
            px = {m: live_px.get(m, data[m]["close"].iloc[-1]) for m in old.markets}
            old.close_all(str(now), px, "config change")
            equity = old.realized
            notes.append(f"{role}: config changed, old positions closed, equity carried {equity:.2f}")
        led = {"config": cfg, "book": Book(markets, equity).to_dict(), "closed_through": None,
               "opened_bar": None, "live_open": {}}

    book = Book.from_dict(led["book"])
    idx = data["BTC"][data["BTC"]["confirmed"]].index
    done = [t for t in idx if led["closed_through"] is None or t > pd.Timestamp(led["closed_through"])]
    if led["closed_through"] is None:
        done = []                                    # first run: start trading from now, no back-fill
    if len(done) > MAX_CATCH_UP_HOURS:
        px = {m: live_px[m] for m in markets}
        book.close_all(str(now), px, "bot was down too long")
        notes.append(f"{role}: {len(done)}h missed -> flattened and restarted")
        done = []

    def decisions(t):
        prev = t - pd.Timedelta(hours=1)
        return {m: (float(targets[m].get(prev, 0.0)), float(feats[m]["atr"].get(prev, float("nan"))),
                    float(feats[m]["quote_vol_24h"].get(prev, float("nan")))) for m in markets}

    def bar(m, t, k):
        return float(data[m].loc[t, k])

    for t in done:
        prev = t - pd.Timedelta(hours=1)
        ny = str(t.tz_convert(C.TIMEZONE).date())
        live = led["opened_bar"] == str(t)
        opens = {m: led["live_open"][m] for m in markets} if live else {m: bar(m, t, "open") for m in markets}
        if not live:  # catch-up hour we did not see live: open it with the real bar open
            book.open_bar(str(t), ny, opens, {m: float(data[m].get("funding", pd.Series()).get(t, 0.0)) for m in markets},
                          decisions(t), {m: bar(m, prev, "close") for m in markets}, stop_atr, cfg["risk"])
        eq = book.close_bar(str(t), {m: bar(m, t, "high") for m in markets}, {m: bar(m, t, "low") for m in markets},
                            {m: bar(m, t, "close") for m in markets}, opens)
        rows.append([str(t), role, cfg["name"], round(eq, 4)])
        led["closed_through"] = str(t)

    # This hour: decide from the last closed bar, fill at the live price.
    current = data["BTC"].index[-1]
    if not data["BTC"]["confirmed"].iloc[-1] and led["opened_bar"] != str(current):
        last_closed = current - pd.Timedelta(hours=1)
        ny = str(current.tz_convert(C.TIMEZONE).date())
        fund = {m: float(data[m].get("funding", pd.Series()).get(current, 0.0)) for m in markets}
        book.open_bar(str(current), ny, live_px, fund, decisions(current),
                      {m: bar(m, last_closed, "close") for m in markets}, stop_atr, cfg["risk"])
        led["opened_bar"], led["live_open"] = str(current), {m: live_px[m] for m in markets}
        if led["closed_through"] is None:
            led["closed_through"] = str(last_closed)
    led["book"] = book.to_dict()
    return led, rows, notes


def write_status(cfg_doc, ledgers, now, problems):
    lines = [f"# Paper desk status — {now.tz_convert(C.TIMEZONE):%Y-%m-%d %H:%M} New York", "",
             "PAPER ONLY. No real orders. Prices: OKX public API.", ""]
    if problems:
        lines += ["**RISK HALT this hour (data):** " + "; ".join(f"{m}: {p}" for m, p in problems.items()), ""]
    for role, led in ledgers.items():
        if not led:
            continue
        b = led["book"]
        cfg = led["config"]
        lines.append(f"## {role}: {cfg['name']} {'(passed all gates)' if cfg['passed_gates'] else '(shadow: did NOT pass all gates)'}")
        lines.append(f"- realized equity: ${b['realized']:.2f} (start ${C.START_CAPITAL:.0f})")
        g = b["guard"]
        lines.append(f"- today: halted={g['halted']} {g['reason']} | losing streak={g['streak']}")
        for m, p in b["pos"].items():
            if p:
                lines.append(f"- open {m}: {'LONG' if p['units'] > 0 else 'SHORT'} {abs(p['units']):.6f} @ {p['entry']:.4f}, stop {p['stop']:.4f}, risk ${p['risk']:.2f}")
        for t in b["trades"][-5:]:
            lines.append(f"- trade {t['market']} {'L' if t['dir'] > 0 else 'S'} {t['entry_time'][:16]}→{t['exit_time'][:16]} pnl ${t['pnl']:.2f} ({t['reason']})")
        lines.append("")
    (STATE / "status.md").write_text("\n".join(lines))


def main():
    STATE.mkdir(exist_ok=True)
    now = pd.Timestamp.now(tz="UTC")
    cfg_doc = read_json(STATE / "strategy.json", None)
    if not cfg_doc:
        raise SystemExit("state/strategy.json missing: run python -m desk.quant first")
    ledgers = read_json(STATE / "ledgers.json", {})
    active = {r: c for r, c in cfg_doc["ledgers"].items() if c and c["markets"]}
    needed = sorted({"BTC", *[m for c in active.values() for m in c["markets"]]})

    data = {m: fetch_market(m) for m in needed}
    feats = {m: add_features(data[m], None if m == "BTC" else data["BTC"]) for m in needed}
    live_px = {m: okx.ticker_last(C.MARKETS[m]["okx"]) for m in needed}
    if "EUR" in live_px:
        live_px["EUR"] = 1 / live_px["EUR"]

    problems = {m: p for m in needed if (p := check_data(m, data[m], feats[m], now))}
    if problems:
        append_csv(STATE / "risk_log.csv", ["time_utc", "event"], [[str(now), f"DATA HALT {problems}"]])
        write_status(cfg_doc, ledgers, now, problems)
        print("RISK HALT:", problems)
        return

    all_rows, all_notes = [], []
    for role, cfg in active.items():
        ledgers[role], rows, notes = step_ledger(role, cfg, ledgers.get(role), data, feats, live_px, now)
        all_rows += rows
        all_notes += notes
        for h in ledgers[role]["book"]["guard"]["log"]:
            all_notes.append(f"{role} HALT {h}")
        ledgers[role]["book"]["guard"]["log"] = []
    (STATE / "ledgers.json").write_text(json.dumps(ledgers, indent=1, default=str))
    if all_rows:
        append_csv(STATE / "equity.csv", ["bar_utc", "ledger", "strategy", "equity"], all_rows)
    if all_notes:
        append_csv(STATE / "risk_log.csv", ["time_utc", "event"], [[str(now), n] for n in all_notes])
    write_status(cfg_doc, ledgers, now, {})
    print((STATE / "status.md").read_text())


if __name__ == "__main__":
    main()
