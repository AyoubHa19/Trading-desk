# Trading desk — rules for every session

- PAPER ONLY. Never place a real order, never add exchange API keys to code, chat, env files or commits. Real money waits for the owner's explicit "go live".
- Only real data. Every number needs a source and a timestamp. Never invent a price, a fill or a backtest result. Label every estimate.
- No lookahead: features use bars up to t, trades fill at t+1. `python -m pytest -q` must pass before any change to strategy or engine code is pushed.
- Never change risk limits in `desk/config.py` without the owner's approval.
- The owner reads Moroccan Darija in Arabic script: write messages to them in Darija.
- Work on branch `claude/new-session-fv2ucl`. The paper bot (GitHub Actions) commits to `state/` every hour: `git pull --rebase` before pushing.
- If blocked, leave one question for the owner and keep going.
