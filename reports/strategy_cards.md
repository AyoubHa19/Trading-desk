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
- **Results after costs:** return 67.95% (CAGR 19.13%), Sharpe 0.80, max drawdown -34.20%, 873 trades, win rate 34.94%, worst losing streak 21
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return 58.77%, Sharpe 0.72
- **Worst month:** 2025-09 (-16.67%)
- **Bull / bear / chop Sharpe:** {'bull': 2.74, 'bear': 3.15, 'chop': -0.8}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -10.2, 'median_return_pct': 58.4, 'p95_max_dd_pct': -37.3, 'prob_loss_pct': 9.2}
- **Daily halts triggered:** 112
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

## trend_4h_time — REJECTED — score 2.67/5 — FAILED gates

- **Idea:** Same trend entries; close any trade after 5 or 10 days.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h_time` in desk/strategies.py; stop = 4.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 4.0, 'max_hold_h': 240}; markets traded ['BTC', 'ETH', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 30.41% (CAGR 9.38%), Sharpe 0.46, max drawdown -38.55%, 1097 trades, win rate 35.46%, worst losing streak 15
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return -5.73%, Sharpe 0.06
- **Worst month:** 2026-09 (-12.82%)
- **Bull / bear / chop Sharpe:** {'bull': 0.56, 'bear': 0.19, 'chop': 0.48}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -37.2, 'median_return_pct': 25.4, 'p95_max_dd_pct': -52.7, 'prob_loss_pct': 29.2}
- **Daily halts triggered:** 134
- **Market that breaks it:** Same as trend_4h.
- **Earliest sign it's fading:** Same as trend_4h.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 3, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 4, 'total': 2.67}

**WHY THIS COULD FAIL:** Closing trend trades early cut off the few big moves that pay for all the small losses.

## trend_4h_be — REJECTED — score 2.67/5 — FAILED gates

- **Idea:** Same trend entries; once 1R or 2R in profit, the stop moves to breakeven.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h_be` in desk/strategies.py; stop = 8.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 8.0, 'be_r': 1.0}; markets traded ['BTC', 'ETH', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 34.71% (CAGR 10.58%), Sharpe 0.53, max drawdown -31.43%, 823 trades, win rate 32.69%, worst losing streak 14
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return 7.12%, Sharpe 0.22
- **Worst month:** 2025-06 (-11.58%)
- **Bull / bear / chop Sharpe:** {'bull': 1.59, 'bear': 2.4, 'chop': -0.38}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -26.6, 'median_return_pct': 30.4, 'p95_max_dd_pct': -43.3, 'prob_loss_pct': 22.5}
- **Daily halts triggered:** 115
- **Market that breaks it:** Same as trend_4h.
- **Earliest sign it's fading:** Same as trend_4h.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': True, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 3, 'sharpe': 3, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.67}

**WHY THIS COULD FAIL:** Closing trend trades early cut off the few big moves that pay for all the small losses.

## vol_breakout — REJECTED — score 2.33/5 — FAILED gates

- **Idea:** After quiet periods, a break of the 24h range triggers clustered stops and runs.
- **Fair value vs price:** volatility mispriced (too low) vs what follows.
- **Who loses:** Range sellers whose stops sit just outside the range.
- **Rules:** entry/exit = `vol_breakout` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'ratio': 0.8, 'hold_h': 24, 'stop_atr': 3.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 0.23% (CAGR 0.08%), Sharpe 0.17, max drawdown -44.77%, 606 trades, win rate 38.28%, worst losing streak 13
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -52.83%, Sharpe -0.63
- **Worst month:** 2025-12 (-21.15%)
- **Bull / bear / chop Sharpe:** {'bull': -2.0, 'bear': 1.04, 'chop': 0.71}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -57.2, 'median_return_pct': -3.2, 'p95_max_dd_pct': -66.1, 'prob_loss_pct': 52.1}
- **Daily halts triggered:** 84
- **Market that breaks it:** Bull regime (Sharpe -2.17): fake breakouts out of quiet ranges.
- **Earliest sign it's fading:** Drawdown beyond 30%.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.33}

**WHY THIS COULD FAIL:** -38% with costs doubled; 31% drawdown. Rejected.

## trend_4h_partial — REJECTED — score 2.33/5 — FAILED gates

- **Idea:** Same trend entries; take half the profit at 1R or 2R, stop to breakeven, let the rest run.
- **Fair value vs price:** slow markets following fast ones / under-reaction.
- **Who loses:** Early profit-takers and slow money (funds, treasuries) that buy or sell late.
- **Rules:** entry/exit = `trend_4h_partial` in desk/strategies.py; stop = 8.0 × ATR(24h); latest params {'lookback_4h': 120, 'stop_atr': 8.0, 'partial_r': 2.0, 'partial_frac': 0.5}; markets traded ['BTC', 'ETH', 'EUR', 'GOLD', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return 0.68% (CAGR 0.23%), Sharpe 0.17, max drawdown -49.52%, 1571 trades, win rate 41.69%, worst losing streak 15
- **Buy & hold, same markets:** return 59.60%, Sharpe 0.61, max drawdown -45.35%
- **Costs doubled:** return 0.82%, Sharpe 0.17
- **Worst month:** 2025-04 (-17.41%)
- **Bull / bear / chop Sharpe:** {'bull': 2.21, 'bear': 0.64, 'chop': -0.84}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -53.3, 'median_return_pct': -8.7, 'p95_max_dd_pct': -62.5, 'prob_loss_pct': 57.7}
- **Daily halts triggered:** 156
- **Market that breaks it:** Same as trend_4h.
- **Earliest sign it's fading:** Same as trend_4h.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': True, 'profitable_with_costs_doubled': True, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 2, 'sharpe': 2, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 3, 'total': 2.33}

**WHY THIS COULD FAIL:** Closing trend trades early cut off the few big moves that pay for all the small losses.

## funding_reversion — REJECTED — score 2.0/5 — FAILED gates

- **Idea:** When funding is extreme, one side is crowded and over-paying; fade them.
- **Fair value vs price:** funding extremes.
- **Who loses:** Leveraged traders paying extreme funding who get forced out.
- **Rules:** entry/exit = `funding_reversion` in desk/strategies.py; stop = 3.0 × ATR(24h); latest params {'z': 2.5, 'hold_h': 72, 'stop_atr': 3.0}; markets traded ['BTC', 'ETH', 'SOL'].
- **Size:** quarter Kelly from the previous 12 months' trades, max 1% risk/trade, 5%/theme, 3x leverage, $5 min, skip if costs > 25% of risk.
- **Results after costs:** return -15.76% (CAGR -5.62%), Sharpe -0.23, max drawdown -30.76%, 110 trades, win rate 34.55%, worst losing streak 8
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -26.36%, Sharpe -0.45
- **Worst month:** 2024-09 (-10.68%)
- **Bull / bear / chop Sharpe:** {'bull': -0.76, 'bear': -1.7, 'chop': 0.6}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -42.2, 'median_return_pct': -16.6, 'p95_max_dd_pct': -46.1, 'prob_loss_pct': 78.4}
- **Daily halts triggered:** 14
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
- **Results after costs:** return -26.26% (CAGR -9.77%), Sharpe -0.21, max drawdown -58.55%, 911 trades, win rate 31.94%, worst losing streak 24
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -45.06%, Sharpe -0.51
- **Worst month:** 2026-02 (-37.48%)
- **Bull / bear / chop Sharpe:** {'bull': 0.68, 'bear': 0.19, 'chop': -0.58}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -63.7, 'median_return_pct': -31.2, 'p95_max_dd_pct': -68.1, 'prob_loss_pct': 81.5}
- **Daily halts triggered:** 118
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
- **Results after costs:** return -5.86% (CAGR -2.02%), Sharpe 0.10, max drawdown -52.86%, 1249 trades, win rate 33.15%, worst losing streak 19
- **Buy & hold, same markets:** return 67.79%, Sharpe 0.61, max drawdown -53.33%
- **Costs doubled:** return -33.05%, Sharpe -0.31
- **Worst month:** 2026-02 (-33.27%)
- **Bull / bear / chop Sharpe:** {'bull': 2.59, 'bear': -1.73, 'chop': -0.29}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -58.7, 'median_return_pct': -11.0, 'p95_max_dd_pct': -66.7, 'prob_loss_pct': 59.5}
- **Daily halts triggered:** 157
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
- **Results after costs:** return -16.75% (CAGR -6.00%), Sharpe -0.72, max drawdown -20.97%, 75 trades, win rate 44.00%, worst losing streak 9
- **Buy & hold, same markets:** return 15.76%, Sharpe 0.42, max drawdown -71.47%
- **Costs doubled:** return -20.64%, Sharpe -0.91
- **Worst month:** 2025-11 (-6.43%)
- **Bull / bear / chop Sharpe:** {'bull': -0.72, 'bear': -3.77, 'chop': 0.35}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -33.4, 'median_return_pct': -16.8, 'p95_max_dd_pct': -35.3, 'prob_loss_pct': 91.9}
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
- **Results after costs:** return -49.99% (CAGR -20.86%), Sharpe -0.77, max drawdown -58.89%, 489 trades, win rate 43.15%, worst losing streak 16
- **Buy & hold, same markets:** return 39.26%, Sharpe 0.49, max drawdown -65.42%
- **Costs doubled:** return -63.97%, Sharpe -1.20
- **Worst month:** 2024-06 (-17.64%)
- **Bull / bear / chop Sharpe:** {'bull': -0.39, 'bear': -1.41, 'chop': -0.82}
- **Monte Carlo (5000 resamples of the trades):** {'p5_return_pct': -72.8, 'median_return_pct': -51.7, 'p95_max_dd_pct': -75.0, 'prob_loss_pct': 97.8}
- **Daily halts triggered:** 53
- **Market that breaks it:** Everywhere: the Pricer has ~0 out-of-sample predictive power (rank IC ~0.0-0.06).
- **Earliest sign it's fading:** Already negative.
- **Gates:** {'beats_buy_and_hold_sharpe': False, 'profitable_after_costs': False, 'profitable_with_costs_doubled': False, 'enough_trades': True}
- **Score detail (1-5):** {'profit': 1, 'sharpe': 1, 'drawdown': 1, 'trades': 5, 'losing_streak': 1, 'regimes': 1, 'total': 1.67}

**WHY THIS COULD FAIL:** -30% out-of-sample. The fair-value model is not good enough to trade on its own.
