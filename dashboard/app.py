"""Live trade screen for the paper desk (Streamlit).

Reads the bot's trades from state/ (updated every hour by GitHub Actions) and
prices them live with OKX's public API every 15 seconds. Read-only: it never
places an order and holds no keys.

Run locally:  streamlit run dashboard/app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from desk import config as C  # noqa: E402
from desk import okx  # noqa: E402

STATE = ROOT / "state"
REFRESH_SECONDS = 15
NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "GOLD": "الذهب (XAU)", "EUR": "EUR/USD"}

st.set_page_config(page_title="مكتب التداول", page_icon="📈", layout="wide")
st.markdown("""
<style>
  html, body, [class*="st-"] { direction: rtl; }
  [data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] * { direction: ltr !important; }
  .num { direction: ltr; unicode-bidi: embed; font-variant-numeric: tabular-nums; }
  .card { border: 1px solid rgba(128,128,128,.25); border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; }
  .row { display: flex; flex-wrap: wrap; gap: 8px 22px; align-items: baseline; }
  .mkt { font-size: 1.25rem; font-weight: 600; }
  .side { padding: 2px 10px; border-radius: 999px; font-weight: 600; font-size: .85rem; }
  .LONG { background: rgba(22,163,74,.15); color: #16a34a; }
  .SHORT { background: rgba(220,38,38,.15); color: #dc2626; }
  .pos { color: #16a34a; } .neg { color: #dc2626; }
  .lbl { opacity: .65; font-size: .8rem; display: block; }
  .why { margin-top: 10px; line-height: 1.8; font-size: .95rem; }
  .bar { height: 6px; background: rgba(128,128,128,.2); border-radius: 3px; overflow: hidden; margin-top: 4px; direction: ltr; }
  .bar > i { display: block; height: 100%; background: #dc2626; }
</style>
""", unsafe_allow_html=True)


def money(v, sign=False):
    s = f"{'+' if sign and v > 0 else '-' if v < 0 else ''}${abs(v):,.2f}"
    return f'<span class="num">{s}</span>'


def price(v):
    return f'<span class="num">{v:,.2f}</span>' if abs(v) >= 100 else f'<span class="num">{v:,.4f}</span>'


def load_state():
    cfg = json.loads((STATE / "strategy.json").read_text())
    ledgers = json.loads((STATE / "ledgers.json").read_text()) if (STATE / "ledgers.json").exists() else {}
    eq = pd.read_csv(STATE / "equity.csv") if (STATE / "equity.csv").exists() else pd.DataFrame()
    risk = pd.read_csv(STATE / "risk_log.csv") if (STATE / "risk_log.csv").exists() else pd.DataFrame()
    return cfg, ledgers, eq, risk


@st.cache_data(ttl=10, show_spinner=False)
def live_price(market: str):
    inst = C.MARKETS[market]["okx"]
    p = okx.ticker_last(inst)
    return (1 / p if inst == "USDT-EUR" else p), pd.Timestamp.now(tz="UTC")


@st.cache_data(ttl=60, show_spinner=False)
def exit_level(market: str, lookback_4h: int):
    """Price that flips the 20-day trend at the next 4h close, and when that close is.

    trend_4h compares each completed 4h close with the 4h close `lookback_4h` bars earlier.
    At the next 4h close the reference will be today's c4[-lookback], so that price is the line.
    """
    inst = C.MARKETS[market]["okx"]
    df = okx.candles_1h(inst, 4 * lookback_4h + 48)
    done = df[df["confirmed"]]
    c4 = done["close"][done.index.hour % 4 == 3]          # closes of 4h blocks (UTC 00-04, 04-08, ...)
    if len(c4) < lookback_4h:
        return None, None
    level = float(c4.iloc[-lookback_4h])
    next_close = c4.index[-1] + pd.Timedelta(hours=5)    # bar opened 03:00 closes 04:00; next block ends 4h later
    if inst == "USDT-EUR":
        level = 1 / level
    return level, next_close


def plan_text(m, p, champ):
    side = "SHORT" if p["units"] < 0 else "LONG"
    try:
        level, when = exit_level(m, champ["params"]["lookback_4h"])
    except Exception:
        level, when = None, None
    flip = (f"الثمن ديال الإغلاق ديال 4 ساعات يكون <b>{'فوق' if side == 'SHORT' else 'تحت'} {price(level)}</b> "
            f"(أول شيك: {when:%H:%M} UTC، ومن بعد كل 4 ساعات؛ هاد الخط كيتبدل شوية بشوية)") if level else "الاتجاه ديال 20 يوم يتقلب"
    return (f"<b>خطة الخروج:</b> كيتسد بوحدو ملي يوقع واحد من هادو:<br>"
            f"① {flip}.<br>"
            f"② الثمن يضرب الـ stop {price(p['stop'])} (الخسارة كتكون تقريبا {money(p['risk'])}).<br>"
            f"③ Risk يوقف النهار: خسارة {C.DAILY_LOSS_STOP:.0%} ولا {C.MAX_LOSING_STREAK} خسارات متتابعة.<br>"
            f"ما كاينش take-profit: جربناه فالـ backtest وكان كيقتل الربح (+72% بلاه، -13% بيه).")


def why_text(m, p):
    w = p.get("why") or {}
    side = "SHORT" if p["units"] < 0 else "LONG"
    if w.get("rule") == "trend_4h":
        move = "طاح" if w["change_pct"] < 0 else "طلع"
        then = pd.Timestamp(w["then_utc"]).strftime("%Y-%m-%d")
        dist = w["stop_atr"] * w["atr"]
        return (
            f"<b>علاش تحل؟</b> الثمن ديال {NAMES.get(m, m)} {move} "
            f"<span class='num'>{abs(w['change_pct']):.1f}%</span> ف {w['lookback_days']:.0f} يوم "
            f"(من {price(w['price_then'])} نهار {then} حتى {price(w['price_now'])}). "
            f"الـ strategy <b>trend_4h</b> كتبع الاتجاه ديال 20 يوم: إلا الثمن {move}، كندخلو <b>{side}</b>.<br>"
            f"<b>الـ stop:</b> 8 × ATR (الحركة العادية ف ساعة = {price(w['atr'])}) = {price(dist)} "
            f"{'فوق' if side == 'SHORT' else 'تحت'} الدخول. <b>الخطر:</b> {w['risk_pct']:.1f}% من الرأسمال، يعني ما تخسرش أكثر من {money(p['risk'])} إلا ضرب الـ stop "
            f"(الحجم كيتحسب بـ ربع Kelly، والحد الأقصى {C.RISK_PER_TRADE:.0%})."
        )
    return "<b>علاش تحل؟</b> ما تسجلش السبب ديال هاد الـ trade."


CHART_DAYS_BACK, CHART_DAYS_AHEAD = 10, 20  # 20 days ahead = the whole known future of the line


@st.cache_data(ttl=60, show_spinner=False)
def history(market: str):
    """~32 days of hourly OKX candles: enough for the 20-day line over the last 10 days."""
    df = okx.candles_1h(C.MARKETS[market]["okx"], 24 * 32)
    if C.MARKETS[market]["okx"] == "USDT-EUR":
        df = df.assign(open=1 / df["open"], high=1 / df["low"], low=1 / df["high"], close=1 / df["close"])
    return df


def trade_chart(m, p, champ, closed, px, candle_hours):
    """Live chart: candles, the 20-day line (past solid, future dotted), entry, stop, price now, past trades."""
    n = champ["params"]["lookback_4h"]
    df = history(m)
    if px:  # the bar in progress follows the live price
        last = df.index[-1]
        df.loc[last, ["close", "high", "low"]] = [px, max(df.loc[last, "high"], px), min(df.loc[last, "low"], px)]
    done = df[df["confirmed"]]
    c4 = done["close"][done.index.hour % 4 == 3].copy()
    c4.index = c4.index + pd.Timedelta(hours=1)          # moment each 4h close is known
    line_past = c4.shift(n).dropna()
    fut_t = [c4.index[-1] + pd.Timedelta(hours=4 * (k + 1)) for k in range(6 * CHART_DAYS_AHEAD)]
    fut_v = [float(c4.iloc[-n + k]) for k in range(min(len(fut_t), n))]
    fut_t = fut_t[:len(fut_v)]

    bars = df if candle_hours == 1 else df.resample("4h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    start = df.index[-1] - pd.Timedelta(days=CHART_DAYS_BACK)
    bars = bars[bars.index >= start]
    line_past = line_past[line_past.index >= start]
    end = fut_t[-1]

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=bars.index, open=bars["open"], high=bars["high"], low=bars["low"], close=bars["close"],
                                 name="الثمن", increasing_line_color="#16a34a", decreasing_line_color="#dc2626"))
    fig.add_trace(go.Scatter(x=line_past.index, y=line_past.values, name="الحد (ثمن قبل 20 يوم)",
                             line=dict(color="#e08a00", width=2)))
    fig.add_trace(go.Scatter(x=fut_t, y=fut_v, name="الحد فالأيام الجاية", line=dict(color="#e08a00", width=2, dash="dot")))
    entry_t = pd.Timestamp(p["t"])
    fig.add_trace(go.Scatter(x=[entry_t, end], y=[p["entry"]] * 2, name="الدخول", mode="lines",
                             line=dict(color="#7c8796", width=1.5, dash="dash")))
    fig.add_trace(go.Scatter(x=[entry_t, end], y=[p["stop"]] * 2, name="Stop", mode="lines",
                             line=dict(color="#dc2626", width=2)))
    side = "SHORT" if p["units"] < 0 else "LONG"
    fig.add_trace(go.Scatter(x=[entry_t], y=[p["entry"]], mode="markers+text", text=[side], textposition="bottom center",
                             marker=dict(size=11, color="#1f6feb", symbol="triangle-down" if side == "SHORT" else "triangle-up"),
                             name="دخلنا", showlegend=False))
    if px:
        fig.add_trace(go.Scatter(x=[df.index[-1]], y=[px], mode="markers", marker=dict(size=10, color="#1f6feb",
                                 line=dict(color="white", width=2)), name="دابا", showlegend=False))
    # earlier closed trades on this market, inside the window
    for t in closed:
        if t["market"] != m or pd.Timestamp(t["exit_time"]) < start:
            continue
        fig.add_trace(go.Scatter(x=[pd.Timestamp(t["entry_time"]), pd.Timestamp(t["exit_time"])], y=[t["entry"], t["exit"]],
                                 mode="lines+markers", line=dict(color="#16a34a" if t["pnl"] > 0 else "#dc2626", width=1, dash="dot"),
                                 marker=dict(size=6), name=f"trade قديم {t['pnl']:+.2f}$", showlegend=False))
    ys = list(bars["low"]) + list(bars["high"]) + [p["stop"], p["entry"]] + fut_v + list(line_past.values)
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.05
    fig.update_layout(height=430, margin=dict(l=58, r=10, t=10, b=10), xaxis_rangeslider_visible=False,
                      yaxis=dict(range=[lo - pad, hi + pad], side="left", automargin=True,
                                 tickformat=".4~s" if hi >= 1000 else ".2f"),
                      xaxis=dict(range=[start, end]), legend=dict(orientation="h", y=-0.12, x=0),
                      uirevision=f"{m}-{candle_hours}", hovermode="x unified")
    return fig


@st.fragment(run_every=REFRESH_SECONDS)
def screen():
    cfg, ledgers, eq, risk = load_state()
    champ = cfg["ledgers"].get("champion")
    led = ledgers.get("champion")
    if not champ or not led:
        st.warning("البوت ما زال ما بدا.")
        return
    book = led["book"]
    open_pos = {m: p for m, p in book["pos"].items() if p}

    rows, unreal_total, risk_total = [], 0.0, 0.0
    for m, p in open_pos.items():
        try:
            px, at = live_price(m)
        except Exception:
            px, at = None, None
        u = p["units"] * (px - p["entry"]) if px else 0.0
        unreal_total += u
        risk_total += p["risk"]
        rows.append((m, p, px, at, u))

    realized = book["realized"]
    equity = realized + unreal_total
    g = book["guard"]
    last_bar = led.get("opened_bar")

    st.title("مكتب التداول")
    st.caption(f"PAPER فقط، ما كاين حتى order حقيقي · strategy: {champ['name']} · الأسعار live من OKX كل {REFRESH_SECONDS} ثانية · "
               f"آخر مرة خدم البوت: {pd.Timestamp(last_bar).strftime('%Y-%m-%d %H:%M') if last_bar else '—'} UTC")

    c = st.columns(4)
    c[0].metric("الرأسمال (equity)", f"${equity:,.2f}", f"{equity - C.START_CAPITAL:+.2f}$ من البداية ($100)")
    c[1].metric("ربح/خسارة مفتوحة", f"{'+' if unreal_total > 0 else '-' if unreal_total < 0 else ''}${abs(unreal_total):,.2f}")
    c[2].metric("الخطر المفتوح", f"${risk_total:,.2f}", f"{100 * risk_total / max(realized, 1e-9):.1f}% من الرأسمال", delta_color="off")
    c[3].metric("حالة البوت", "واقف اليوم ⛔" if g["halted"] else "خدام ✅", g["reason"] or f"خسارات متتابعة: {g['streak']}", delta_color="off")

    st.subheader(f"الـ trades المفتوحين ({len(rows)})")
    st.radio("الشموع", [4, 1], format_func=lambda h: f"{h} ساعات" if h > 1 else "ساعة", horizontal=True, key="candles")
    st.caption("فالـ chart: الشموع = الثمن · البرتقالي = الحد (الثمن ديال قبل 20 يوم)، المنقط = الأيام الجاية · "
               "الحمر = Stop · الرمادي = الدخول. الـ trade كيتسد ملي الثمن يقطع البرتقالي ولا يضرب الحمر.")
    if not rows:
        st.info("ما كاين حتى trade مفتوح دابا. البوت كيقرر كل ساعة.")
    for m, p, px, at, u in rows:
        side = "LONG" if p["units"] > 0 else "SHORT"
        notional = abs(p["units"]) * p["entry"]
        pct = 100 * u / notional if notional else 0
        to_stop = abs(p["stop"] - px) / px * 100 if px else None
        used = max(0.0, min(100.0, -u / p["risk"] * 100)) if p["risk"] and u < 0 else 0.0
        cls = "pos" if u > 0 else "neg" if u < 0 else ""
        st.markdown(f"""
<div class="card">
  <div class="row">
    <span class="mkt">{NAMES.get(m, m)}</span><span class="side {side}">{side}</span>
    <span><span class="lbl">الحجم</span>{money(notional)}</span>
    <span><span class="lbl">الدخول</span>{price(p['entry'])}</span>
    <span><span class="lbl">الثمن دابا</span>{price(px) if px else '—'}</span>
    <span><span class="lbl">ربح/خسارة</span><b class="{cls}">{money(u, True)} <span class="num">({pct:+.2f}%)</span></b></span>
    <span><span class="lbl">Stop</span>{price(p['stop'])}{f" <span class='num'>({to_stop:.1f}% بعيد)</span>" if to_stop is not None else ''}</span>
    <span><span class="lbl">الخطر</span>{money(p['risk'])}</span>
    <span><span class="lbl">تحل</span><span class="num">{pd.Timestamp(p['t']).strftime('%m-%d %H:%M')} UTC</span></span>
  </div>
  <div class="bar" title="شحال تخسر من الخطر"><i style="width:{used:.0f}%"></i></div>
  <div class="why">{why_text(m, p)}</div>
  <div class="why">{plan_text(m, p, champ)}</div>
</div>""", unsafe_allow_html=True)
        try:
            st.plotly_chart(trade_chart(m, p, champ, book["trades"], px, st.session_state.get("candles", 4)),
                            use_container_width=True, key=f"chart-{m}", config={"displayModeBar": False})
        except Exception as e:  # never invent a chart: say it failed
            st.caption(f"الـ chart ديال {m} ما تحملش دابا ({e.__class__.__name__}). غادي يعاود بوحدو.")

    st.subheader("الـ trades المسدودين")
    trades = pd.DataFrame(book["trades"])
    if trades.empty:
        st.info("ما زال حتى trade ما تسد.")
    else:
        reasons = {"signal": "الاتجاه تقلب", "stop": "ضرب الـ stop", "halt": "Risk وقف النهار", "end": "نهاية",
                   "config change": "تبدلت الـ strategy", "bot was down too long": "البوت وقف بزاف"}
        t = trades.sort_values("exit_time", ascending=False).assign(
            السوق=lambda d: d["market"], الاتجاه=lambda d: d["dir"].map({1: "LONG", -1: "SHORT"}),
            تحل=lambda d: d["entry_time"].str[:16], تسد=lambda d: d["exit_time"].str[:16],
            الدخول=lambda d: d["entry"], الخروج=lambda d: d["exit"], الربح=lambda d: d["pnl"].round(2),
            السبب=lambda d: d["reason"].map(reasons).fillna(d["reason"]))
        st.dataframe(t[["السوق", "الاتجاه", "تحل", "تسد", "الدخول", "الخروج", "الربح", "السبب"]], hide_index=True, use_container_width=True)

    if len(eq):
        st.subheader("الرأسمال ساعة بساعة")
        e = eq[eq["ledger"] == "champion"].assign(bar_utc=lambda d: pd.to_datetime(d["bar_utc"])).set_index("bar_utc")["equity"]
        st.line_chart(e, height=220)

    with st.expander("Risk: التوقفات"):
        if risk.empty:
            st.write("ما كاين حتى توقف.")
        else:
            st.dataframe(risk.iloc[::-1], hide_index=True, use_container_width=True)


screen()
