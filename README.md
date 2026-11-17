# Trading desk (paper only)

A small research desk and a **paper-trading** bot for BTC, ETH, SOL, gold and EUR.
No API keys, no real orders. Real money only after the owner says "go live".

## How it works

| Step | Command | What it does |
|---|---|---|
| Data | `python -m desk.download && python -m desk.build` | 4 years of hourly history from data.binance.vision, each file checked against Binance's sha256 and logged in `data/manifest.csv`. Quality report: `reports/data_quality.json`. |
| Pricer | `python -m desk.pricer` | Fair value per market (ridge model on trend, volatility, funding, open interest, BTC). Walk-forward, out-of-sample. `reports/pricer.json`. |
| Quant | `python -m desk.quant` | 7 strategy ideas, 12 quarterly walk-forward folds (OOS 2023-12 → 2026-11), costs, costs ×2, Monte Carlo, bull/bear/chop, buy & hold. `reports/quant_results.json`. |
| Select | `python -c "from desk import quant; quant.select()"` | Champion + 2 challengers configured on the last 12 months → `state/strategy.json`. |
| Cards | `python -m desk.cards` | `reports/strategy_cards.md`, each closing with **WHY THIS COULD FAIL**. |
| Bot | `python -m desk.bot` | Hourly paper bot (GitHub Actions `.github/workflows/paper-bot.yml`). OKX public prices. |
| Brief | `python -m desk.brief` | Facts for the 07:30 New York brief → `reports/brief.md`. |
| Tests | `python -m pytest -q` | Risk rules, accounting, stops, **no lookahead**, and **bot == backtest** replay. |

## Rules (config in `desk/config.py`)

- $100 paper capital, max 1% risk per trade, 5% per theme (BTC/ETH/SOL are one theme), quarter Kelly, 3x max leverage.
- Stop for the New York day after -3% or 3 losing trades in a row (positions closed).
- Skip any trade whose round-trip costs exceed 25% of the amount risked; thin book = max 1% of hourly volume.
- Risk halts the whole bot for the hour when data looks wrong (stale, gaps, >15 ATR jump).
- A challenger can replace the champion only after 7 winning paper days **and** passing every research gate.

## Honest limits

- Fills are simulated at the live OKX price; slippage is an estimate.
- EUR and gold are traded through crypto proxies (EURUSDT, PAXG for history; OKX XAU perp live). Real FX/gold needs a real broker.
- The Binance API blocks US cloud servers (HTTP 451), so live prices come from OKX.
