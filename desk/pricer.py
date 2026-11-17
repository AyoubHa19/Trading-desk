"""Pricer: a fair value for every market, written down from the inputs only.

Fair value = what the price "should" be 24h from now given trend, volatility,
funding, open interest and BTC (cross-market). It is a small ridge regression
of the next-24h log return on those inputs, re-trained every month on the
previous 12 months only (with a 24h gap so no training label peeks into the test).

    fair_value = price * exp(predicted 24h return)

The model never sees the price it is judging: inputs are returns/ratios, and
the number is stored before we compare it with the market.

Run:  python -m desk.pricer      (writes reports/pricer.json)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from desk.features import build_all, load_all

HORIZON = 24
TRAIN_HOURS = 24 * 365
INPUTS_ALL = ["mom_5d", "mom_10d", "mom_20d", "ret_z", "vol_ratio"]
INPUTS_PERP = ["funding_z", "oi_chg_24h"]
INPUTS_ALT = ["resid_vs_btc_1h", "btc_mom_5d"]


def design(market: str, f: pd.DataFrame, btc_f: pd.DataFrame) -> pd.DataFrame:
    X = f[["mom_5d", "mom_10d", "mom_20d", "ret_z"]].copy()
    X["vol_ratio"] = f["vol_24h"] / f["vol_30d"]
    if "funding_z" in f:
        X["funding_z"] = f["funding_z"]
        X["oi_chg_24h"] = f["oi_chg_24h"]
    if market != "BTC":
        X["resid_vs_btc_1h"] = f["resid_vs_btc_1h"]
        X["btc_mom_5d"] = btc_f["mom_5d"].reindex(f.index)
    return X


def ridge_fit(X: np.ndarray, y: np.ndarray, lam: float = 10.0):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = (X - mu) / sd
    beta = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return mu, sd, beta, y.mean()


def ridge_predict(model, X: np.ndarray) -> np.ndarray:
    mu, sd, beta, b0 = model
    return b0 + ((X - mu) / sd) @ beta


def walk_forward(data, feats, market: str, start="2023-12-01") -> pd.Series:
    """Out-of-sample predictions: each month predicted by a model trained only on the past."""
    df, f = data[market], feats[market]
    X = design(market, f, feats["BTC"]).replace([np.inf, -np.inf], np.nan)
    y = np.log(df["close"].shift(-HORIZON) / df["close"])  # the FUTURE 24h return (label only)
    preds = []
    for month_start in pd.date_range(pd.Timestamp(start, tz="UTC"), df.index[-1], freq="MS"):
        month_end = month_start + pd.offsets.MonthBegin(1)
        train_end = month_start - pd.Timedelta(hours=HORIZON)  # purge: labels must end before the test starts
        tr = X.loc[train_end - pd.Timedelta(hours=TRAIN_HOURS):train_end].join(y.rename("y")).dropna()
        te = X.loc[month_start:month_end - pd.Timedelta(hours=1)].dropna()
        if len(tr) < 2000 or te.empty:
            continue
        model = ridge_fit(tr.drop(columns="y").values, tr["y"].values)
        preds.append(pd.Series(ridge_predict(model, te.values), index=te.index))
    return pd.concat(preds) if preds else pd.Series(dtype=float)


def evaluate(pred: pd.Series, df: pd.DataFrame) -> dict:
    fut = np.log(df["close"].shift(-HORIZON) / df["close"]).reindex(pred.index)
    ok = fut.notna()
    p, r = pred[ok], fut[ok]
    daily = pd.DataFrame({"p": p, "r": r}).iloc[::24]  # non-overlapping 24h samples
    return {
        "oos_rank_ic": round(float(p.rank().corr(r.rank())), 4),
        "oos_rank_ic_daily_nonoverlap": round(float(daily["p"].rank().corr(daily["r"].rank())), 4),
        "hit_rate_pct": round(100 * float((np.sign(p) == np.sign(r)).mean()), 1),
        "avg_abs_pred_pct": round(100 * float(p.abs().mean()), 3),
        "n_days": int(len(daily)),
    }


def fair_values_now(data, feats) -> list[dict]:
    """Today's fair value per market from a model trained on the last 12 months."""
    out = []
    for m in data:
        df, f = data[m], feats[m]
        X = design(m, f, feats["BTC"]).replace([np.inf, -np.inf], np.nan)
        y = np.log(df["close"].shift(-HORIZON) / df["close"])
        last = X.dropna().index[-1]
        tr = X.loc[last - pd.Timedelta(hours=TRAIN_HOURS + HORIZON):last - pd.Timedelta(hours=HORIZON)].join(y.rename("y")).dropna()
        model = ridge_fit(tr.drop(columns="y").values, tr["y"].values)
        pred = float(ridge_predict(model, X.loc[[last]].values)[0])
        price = float(df.loc[last, "close"])
        out.append({"market": m, "as_of_utc": str(last + pd.Timedelta(hours=1)), "source": "data.binance.vision 1h close",
                    "fair_value_24h": round(price * float(np.exp(pred)), 4), "price": price,
                    "gap_pct": round(100 * pred, 3), "label": "MODEL ESTIMATE"})
    return out


def main():
    data = load_all()
    feats = build_all(data)
    report = {"method": __doc__.strip().split("\n\n")[1], "markets": {}}
    preds = {}
    for m in data:
        preds[m] = walk_forward(data, feats, m)
        report["markets"][m] = evaluate(preds[m], data[m])
        print(m, report["markets"][m])
    report["fair_value_now"] = fair_values_now(data, feats)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/pricer.json").write_text(json.dumps(report, indent=2))
    pd.DataFrame(preds).to_parquet("data/processed/pricer_oos.parquet")


if __name__ == "__main__":
    main()
