# Strategy cards

All numbers are OUT-OF-SAMPLE walk-forward results, 2023-12-01 → 2026-11-16, $100 start, after fees,
slippage (estimated) and funding. Source data: data.binance.vision (see data/manifest.csv), cross-checked with OKX.
Buy & hold = equal-weight hold of the same markets over the same period.

## trend_4h — CHAMPION — score 3.17/5 — PASSED all gates

- **Idea:** Prices under-react to news, so a move over the last 5-20 days tends to continue.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h` in desk/strategies.py; stop = 8.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 8.0}; markets traded ['BTC', 'ETH', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 52.96% (CAGR 15.43%), Sharpe 0.83, max drawdown -19.93%, 905 trades, win rate 35.25%, worst losing streak 21
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return 35.22%, Sharpe 0.62
- **Worst month:** 2025-09 (-9.42%)
- **Bull / bear / chop Sharpe:** {'bull': 2.73, 'bear': 3.66, 'chop': -0.83}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -1.8, 'median_return_pct': 48.8, 'p95_max_dd_pct': -27.0, 'prob_loss_pct': 5.9}
- **Daily halts triggered:** 117
- **Market that breaks it:** Sideways chop: the 'chop' regime Sharpe is negative; whipsaws cost 2 fees each time.
- **Earliest sign it's fading:** Rolling 90-day paper Sharpe < 0 while BTC moves > 10%/month (trends exist but we miss them).
- **Gates:** {'beats_buy_and_hold_sharpe': True, 'profitable_after_costs': True, 'profitable_with_costs_doubled': True, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 4, 'sharpe': 3, 'drawdown': 3, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 3.17}

**WHY THIS COULD FAIL:** Crypto trend-following is crowded; in 2026 every CTA and bot runs it. Most of the profit comes from a few big moves and from trades closed by the daily halt rule, so a calm year can bleed for months. The edge was 16% instead of 53% under a slightly different bookkeeping of the training trades: the SIZE of the result is fragile even if the sign held for every lookback tested. Gold here was tested on PAXG (a crypto token), but the bot uses OKX's XAU perp.

## lead_lag — CHALLENGER_1 — score 3.17/5 — FAILED gates

- **Idea:** After a big BTC hour, ETH/SOL that lagged catch up.
- **Fair value vs price:** slow markets following fast ones.
- **Who loses:** Slow liquidity providers in the alt books.
- **Rules:** entry/exit = `lead_lag` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'k': 3.0, 'hold_h': 4, 'stop_atr': 3.0}; markets traded ['ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 4.19% (CAGR 1.40%), Sharpe 0.26, max drawdown -5.87%, 261 trades, win rate 49.04%, worst losing streak 7
- **Buy & hold, same markets:** return 15.76%, Sharpe 0.42, max drawdown -71.47%
- **Costs doubled:** return -5.81%, Sharpe -0.29
- **Worst month:** 2024-07 (-1.92%)
- **Bull / bear / chop Sharpe:** {'bull': 0.09, 'bear': 2.69, 'chop': -1.0}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -10.6, 'median_return_pct': 4.0, 'p95_max_dd_pct': -15.3, 'prob_loss_pct': 34.0}
- **Daily halts triggered:** 22
- **Market that breaks it:** Fast markets where ETH/SOL react within the same minute as BTC (the usual case today).
- **Earliest sign it's fading:** Average R per trade drops below the round-trip cost.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 4, 'trades': 5, 'losing_streak': 3, 'regimes': 3, 'total': 3.17}

**WHY THIS COULD FAIL:** It dies when costs double (-5.8%): the edge is about the same size as the fees. Arbitrage bots close this gap in seconds, not hours.

## funding_reversion — CHALLENGER_2 — score 3.0/5 — FAILED gates

- **Idea:** When funding is extreme, one side is crowded and over-paying; fade them.
- **Fair value vs price:** funding extremes.
- **Who loses:** Leveraged traders paying extreme funding who get forced out.
- **Rules:** entry/exit = `funding_reversion` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'z': 2.5, 'hold_h': 72, 'stop_atr': 3.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 6.82% (CAGR 2.25%), Sharpe 0.29, max drawdown -9.39%, 84 trades, win rate 42.86%, worst losing streak 5
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return 2.04%, Sharpe 0.12
- **Worst month:** 2024-11 (-2.89%)
- **Bull / bear / chop Sharpe:** {'bull': 0.13, 'bear': -1.28, 'chop': 1.02}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -11.5, 'median_return_pct': 5.8, 'p95_max_dd_pct': -17.3, 'prob_loss_pct': 30.8}
- **Daily halts triggered:** 8
- **Market that breaks it:** Strong one-way bull or bear runs where crowded funding stays extreme for weeks.
- **Earliest sign it's fading:** Funding spikes stop mean-reverting within 72h; losses cluster in bear regime (Sharpe -1.28 there).
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': True, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 4, 'trades': 3, 'losing_streak': 4, 'regimes': 3, 'total': 3.0}

**WHY THIS COULD FAIL:** Only 84 trades in 3 years; the result could be luck. It does not beat buy-and-hold on Sharpe.

## vol_breakout — REJECTED — score 2.33/5 — FAILED gates

- **Idea:** After quiet periods, a break of the 24h range triggers clustered stops and runs.
- **Fair value vs price:** volatility mispriced (too low) vs what follows.
- **Who loses:** Range sellers whose stops sit just outside the range.
- **Rules:** entry/exit = `vol_breakout` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'ratio': 0.8, 'hold_h': 24, 'stop_atr': 3.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 10.44% (CAGR 3.41%), Sharpe 0.26, max drawdown -31.05%, 620 trades, win rate 38.87%, worst losing streak 13
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -37.71%, Sharpe -0.65
- **Worst month:** 2025-12 (-11.62%)
- **Bull / bear / chop Sharpe:** {'bull': -2.17, 'bear': 1.52, 'chop': 0.8}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -34.4, 'median_return_pct': 7.7, 'p95_max_dd_pct': -45.6, 'prob_loss_pct': 40.8}
- **Daily halts triggered:** 88
- **Market that breaks it:** Bull regime (Sharpe -2.17): fake breakouts out of quiet ranges.
- **Earliest sign it's fading:** Drawdown beyond 30%.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.33}

**WHY THIS COULD FAIL:** -38% with costs doubled; 31% drawdown. Rejected.

## liquidation_reversal — REJECTED — score 2.0/5 — FAILED gates

- **Idea:** A violent 1h move with open interest collapsing is forced selling (or buying); it overshoots and bounces.
- **Fair value vs price:** forced sellers.
- **Who loses:** Liquidated traders whose positions are closed at any price.
- **Rules:** entry/exit = `liquidation_reversal` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'k': 4.0, 'oi_drop': 0.01, 'hold_h': 12, 'stop_atr': 3.0}; markets traded ['ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -9.57% (CAGR -3.34%), Sharpe -0.80, max drawdown -11.92%, 73 trades, win rate 42.47%, worst losing streak 9
- **Buy & hold, same markets:** return 15.76%, Sharpe 0.42, max drawdown -71.47%
- **Costs doubled:** return -11.78%, Sharpe -0.99
- **Worst month:** 2025-11 (-3.25%)
- **Bull / bear / chop Sharpe:** {'bull': -1.1, 'bear': -3.93, 'chop': 0.45}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -19.1, 'median_return_pct': -9.7, 'p95_max_dd_pct': -20.1, 'prob_loss_pct': 93.3}
- **Daily halts triggered:** 7
- **Market that breaks it:** Real crashes where forced selling continues for hours.
- **Earliest sign it's fading:** Already negative out-of-sample.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 3, 'trades': 3, 'losing_streak': 2, 'regimes': 2, 'total': 2.0}

**WHY THIS COULD FAIL:** Lost money out-of-sample. The 'forced seller' story is true but the bounce is already taken within the same hour by faster players.

## mean_reversion — REJECTED — score 1.67/5 — FAILED gates

- **Idea:** Crypto-venue proxies (PAXG, EURUSDT) get pushed away from the real gold/EUR price by local flows and get pulled back by arbitrage.
- **Fair value vs price:** slow proxy market vs fast real market.
- **Who loses:** Impatient crypto traders hitting thin proxy books.
- **Rules:** entry/exit = `mean_reversion` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'k': 3.0, 'hold_h': 6, 'stop_atr': 3.0}; markets traded ['GOLD', 'EUR'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 0.00% (CAGR 0.00%), Sharpe 0.00, max drawdown 0.00%, 0 trades, win rate 0.00%, worst losing streak -
- **Buy & hold, same markets:** return 42.31%, Sharpe 0.90, max drawdown -20.63%
- **Costs doubled:** return 0.00%, Sharpe 0.00
- **Worst month:** 2023-12 (0.00%)
- **Bull / bear / chop Sharpe:** {'bull': 0.0, 'bear': 0.0, 'chop': 0.0}
- **Monte Carlo (5000 resamples of the trades):** {}
- **Daily halts triggered:** 0
- **Market that breaks it:** Everywhere: costs on PAXG/EURUSDT spot (0.3% round trip) are bigger than the moves.
- **Earliest sign it's fading:** Never traded: the cost check blocked every trade.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': False}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 5, 'trades': 1, 'losing_streak': 1, 'regimes': 1, 'total': 1.67}

**WHY THIS COULD FAIL:** No trade can pay its costs. EUR/USD and gold need a real FX/CFD broker with ~0.01% spreads, not crypto proxies.

## pricer_gap — REJECTED — score 1.67/5 — FAILED gates

- **Idea:** Trade when the Pricer's fair value is far enough from the price to pay the costs.
- **Fair value vs price:** fair value vs price gap.
- **Who loses:** Whoever is wrong about the inputs (trend, funding, OI, BTC) the model reads.
- **Rules:** entry/exit = `pricer_gap` in desk/strategies.py; stop = 4.0 × ATR(24h); latest params {'mult': 2.0, 'hold_h': 24, 'stop_atr': 4.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -30.22% (CAGR -11.44%), Sharpe -0.73, max drawdown -37.76%, 505 trades, win rate 43.17%, worst losing streak 16
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -42.43%, Sharpe -1.16
- **Worst month:** 2024-06 (-9.07%)
- **Bull / bear / chop Sharpe:** {'bull': -0.43, 'bear': -1.33, 'chop': -0.74}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -50.6, 'median_return_pct': -31.4, 'p95_max_dd_pct': -53.0, 'prob_loss_pct': 96.9}
- **Daily halts triggered:** 54
- **Market that breaks it:** Everywhere: the Pricer has ~0 out-of-sample predictive power (rank IC ~0.0-0.06).
- **Earliest sign it's fading:** Already negative.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 1, 'total': 1.67}

**WHY THIS COULD FAIL:** -30% out-of-sample. The fair-value model is not good enough to trade on its own.
