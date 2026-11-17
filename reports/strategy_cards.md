# Strategy cards

All numbers are OUT-OF-SAMPLE walk-forward results, 2023-12-01 → 2026-11-16, $100 start, after fees,
slippage (estimated) and funding. Source data: data.binance.vision (see data/manifest.csv), cross-checked with OKX.
Buy & hold = equal-weight hold of the same markets over the same period.

## trend_4h — CHAMPION — score 2.83/5 — PASSED all gates

- **Idea:** Prices under-react to news, so a move over the last 5-20 days tends to continue.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h` in desk/strategies.py; stop = 8.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 8.0}; markets traded ['BTC', 'ETH', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 72.11% (CAGR 20.12%), Sharpe 0.84, max drawdown -33.58%, 896 trades, win rate 34.49%, worst losing streak 21
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return 28.46%, Sharpe 0.46
- **Worst month:** 2025-09 (-15.84%)
- **Bull / bear / chop Sharpe:** {'bull': 2.25, 'bear': 3.61, 'chop': -0.57}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -13.0, 'median_return_pct': 64.5, 'p95_max_dd_pct': -39.1, 'prob_loss_pct': 10.3}
- **Daily halts triggered:** 114
- **Market that breaks it:** Sideways chop: the 'chop' regime Sharpe is negative; whipsaws cost 2 fees each time.
- **Earliest sign it's fading:** Rolling 90-day paper Sharpe < 0 while BTC moves > 10%/month (trends exist but we miss them).
- **Gates:** {'beats_buy_and_hold_sharpe': True, 'profitable_after_costs': True, 'profitable_with_costs_doubled': True, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 4, 'sharpe': 3, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.83}

**WHY THIS COULD FAIL:** Crypto trend-following is crowded; in 2026 every CTA and bot runs it. Most of the profit comes from a few big moves and from trades closed by the daily halt rule, so a calm year can bleed for months. The edge was 16% instead of 53% under a slightly different bookkeeping of the training trades: the SIZE of the result is fragile even if the sign held for every lookback tested. Gold here was tested on PAXG (a crypto token), but the bot uses OKX's XAU perp.

## lead_lag — REJECTED — score 2.83/5 — FAILED gates

- **Idea:** After a big BTC hour, ETH/SOL that lagged catch up.
- **Fair value vs price:** slow markets following fast ones.
- **Who loses:** Slow liquidity providers in the alt books.
- **Rules:** entry/exit = `lead_lag` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'k': 3.0, 'hold_h': 4, 'stop_atr': 3.0}; markets traded ['ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 8.38% (CAGR 2.75%), Sharpe 0.30, max drawdown -10.84%, 261 trades, win rate 49.04%, worst losing streak 7
- **Buy & hold, same markets:** return 15.76%, Sharpe 0.42, max drawdown -71.47%
- **Costs doubled:** return -9.71%, Sharpe -0.25
- **Worst month:** 2025-09 (-3.19%)
- **Bull / bear / chop Sharpe:** {'bull': -0.01, 'bear': 2.84, 'chop': -0.89}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -17.5, 'median_return_pct': 7.9, 'p95_max_dd_pct': -25.7, 'prob_loss_pct': 33.0}
- **Daily halts triggered:** 22
- **Market that breaks it:** Fast markets where ETH/SOL react within the same minute as BTC (the usual case today).
- **Earliest sign it's fading:** Average R per trade drops below the round-trip cost.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 3, 'trades': 5, 'losing_streak': 3, 'regimes': 2, 'total': 2.83}

**WHY THIS COULD FAIL:** It dies when costs double (-5.8%): the edge is about the same size as the fees. Arbitrage bots close this gap in seconds, not hours.

## vol_breakout — REJECTED — score 2.33/5 — FAILED gates

- **Idea:** After quiet periods, a break of the 24h range triggers clustered stops and runs.
- **Fair value vs price:** volatility mispriced (too low) vs what follows.
- **Who loses:** Range sellers whose stops sit just outside the range.
- **Rules:** entry/exit = `vol_breakout` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'ratio': 0.8, 'hold_h': 24, 'stop_atr': 3.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 6.39% (CAGR 2.11%), Sharpe 0.23, max drawdown -43.54%, 616 trades, win rate 38.31%, worst losing streak 13
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -52.52%, Sharpe -0.60
- **Worst month:** 2025-12 (-21.15%)
- **Bull / bear / chop Sharpe:** {'bull': -2.18, 'bear': 1.13, 'chop': 0.82}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -54.9, 'median_return_pct': 1.3, 'p95_max_dd_pct': -64.9, 'prob_loss_pct': 49.0}
- **Daily halts triggered:** 84
- **Market that breaks it:** Bull regime (Sharpe -2.17): fake breakouts out of quiet ranges.
- **Earliest sign it's fading:** Drawdown beyond 30%.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.33}

**WHY THIS COULD FAIL:** -38% with costs doubled; 31% drawdown. Rejected.

## trend_4h_time — REJECTED — score 2.33/5 — FAILED gates

- **Idea:** Same trend entries; close any trade after 5 or 10 days.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h_time` in desk/strategies.py; stop = 4.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 4.0, 'max_hold_h': 240}; markets traded ['BTC', 'ETH', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 8.64% (CAGR 2.84%), Sharpe 0.24, max drawdown -38.88%, 1085 trades, win rate 34.93%, worst losing streak 16
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return -19.36%, Sharpe -0.13
- **Worst month:** 2026-09 (-12.82%)
- **Bull / bear / chop Sharpe:** {'bull': 0.18, 'bear': -0.55, 'chop': 0.45}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -47.9, 'median_return_pct': 3.1, 'p95_max_dd_pct': -58.1, 'prob_loss_pct': 46.9}
- **Daily halts triggered:** 128
- **Market that breaks it:** Same as trend_4h.
- **Earliest sign it's fading:** Same as trend_4h.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.33}

**WHY THIS COULD FAIL:** Closing trend trades early cut off the few big moves that pay for all the small losses.

## funding_reversion — REJECTED — score 2.0/5 — FAILED gates

- **Idea:** When funding is extreme, one side is crowded and over-paying; fade them.
- **Fair value vs price:** funding extremes.
- **Who loses:** Leveraged traders paying extreme funding who get forced out.
- **Rules:** entry/exit = `funding_reversion` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'z': 2.5, 'hold_h': 72, 'stop_atr': 3.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -17.50% (CAGR -6.29%), Sharpe -0.24, max drawdown -33.44%, 117 trades, win rate 35.90%, worst losing streak 8
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -29.66%, Sharpe -0.51
- **Worst month:** 2024-09 (-14.09%)
- **Bull / bear / chop Sharpe:** {'bull': -0.36, 'bear': -1.61, 'chop': 0.24}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -44.4, 'median_return_pct': -19.0, 'p95_max_dd_pct': -48.1, 'prob_loss_pct': 80.6}
- **Daily halts triggered:** 15
- **Market that breaks it:** Strong one-way bull or bear runs where crowded funding stays extreme for weeks.
- **Earliest sign it's fading:** Funding spikes stop mean-reverting within 72h; losses cluster in bear regime (Sharpe -1.28 there).
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 1, 'trades': 4, 'losing_streak': 3, 'regimes': 2, 'total': 2.0}

**WHY THIS COULD FAIL:** Only 84 trades in 3 years; the result could be luck. It does not beat buy-and-hold on Sharpe.

## trend_4h_trail — REJECTED — score 2.0/5 — FAILED gates

- **Idea:** Same trend entries; a trailing stop follows the best price to lock in profit.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h_trail` in desk/strategies.py; stop = 4.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 4.0, 'trail_atr': 4.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -29.82% (CAGR -11.27%), Sharpe -0.25, max drawdown -60.89%, 937 trades, win rate 32.02%, worst losing streak 24
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -45.87%, Sharpe -0.50
- **Worst month:** 2026-02 (-37.48%)
- **Bull / bear / chop Sharpe:** {'bull': 0.42, 'bear': 0.23, 'chop': -0.6}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -65.8, 'median_return_pct': -33.9, 'p95_max_dd_pct': -69.5, 'prob_loss_pct': 83.4}
- **Daily halts triggered:** 121
- **Market that breaks it:** Same as trend_4h.
- **Earliest sign it's fading:** Same as trend_4h.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.0}

**WHY THIS COULD FAIL:** Closing trend trades early cut off the few big moves that pay for all the small losses.

## trend_4h_tp — REJECTED — score 2.0/5 — FAILED gates

- **Idea:** Same trend entries; take the profit at 2R or 3R.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h_tp` in desk/strategies.py; stop = 8.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 8.0, 'tp_r': 3.0}; markets traded ['BTC', 'ETH', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -13.45% (CAGR -4.76%), Sharpe 0.01, max drawdown -51.28%, 1269 trades, win rate 33.41%, worst losing streak 19
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return -26.88%, Sharpe -0.20
- **Worst month:** 2026-02 (-33.27%)
- **Bull / bear / chop Sharpe:** {'bull': 2.14, 'bear': -1.67, 'chop': -0.29}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -62.0, 'median_return_pct': -18.2, 'p95_max_dd_pct': -68.9, 'prob_loss_pct': 66.9}
- **Daily halts triggered:** 158
- **Market that breaks it:** Same as trend_4h.
- **Earliest sign it's fading:** Same as trend_4h.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 2, 'total': 2.0}

**WHY THIS COULD FAIL:** Closing trend trades early cut off the few big moves that pay for all the small losses.

## liquidation_reversal — REJECTED — score 1.83/5 — FAILED gates

- **Idea:** A violent 1h move with open interest collapsing is forced selling (or buying); it overshoots and bounces.
- **Fair value vs price:** forced sellers.
- **Who loses:** Liquidated traders whose positions are closed at any price.
- **Rules:** entry/exit = `liquidation_reversal` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'k': 4.0, 'oi_drop': 0.01, 'hold_h': 12, 'stop_atr': 3.0}; markets traded ['ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -18.61% (CAGR -6.71%), Sharpe -0.83, max drawdown -22.74%, 73 trades, win rate 42.47%, worst losing streak 9
- **Buy & hold, same markets:** return 15.76%, Sharpe 0.42, max drawdown -71.47%
- **Costs doubled:** return -22.37%, Sharpe -1.02
- **Worst month:** 2025-11 (-6.43%)
- **Bull / bear / chop Sharpe:** {'bull': -1.1, 'bear': -3.77, 'chop': 0.35}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -34.5, 'median_return_pct': -18.9, 'p95_max_dd_pct': -36.1, 'prob_loss_pct': 94.1}
- **Daily halts triggered:** 7
- **Market that breaks it:** Real crashes where forced selling continues for hours.
- **Earliest sign it's fading:** Already negative out-of-sample.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 2, 'trades': 3, 'losing_streak': 2, 'regimes': 2, 'total': 1.83}

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
- **Results after costs:** return -46.46% (CAGR -19.02%), Sharpe -0.67, max drawdown -56.09%, 500 trades, win rate 43.40%, worst losing streak 16
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -61.59%, Sharpe -1.10
- **Worst month:** 2024-06 (-15.63%)
- **Bull / bear / chop Sharpe:** {'bull': -0.26, 'bear': -1.32, 'chop': -0.73}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -70.9, 'median_return_pct': -48.7, 'p95_max_dd_pct': -73.2, 'prob_loss_pct': 96.5}
- **Daily halts triggered:** 53
- **Market that breaks it:** Everywhere: the Pricer has ~0 out-of-sample predictive power (rank IC ~0.0-0.06).
- **Earliest sign it's fading:** Already negative.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 1, 'total': 1.67}

**WHY THIS COULD FAIL:** -30% out-of-sample. The fair-value model is not good enough to trade on its own.
