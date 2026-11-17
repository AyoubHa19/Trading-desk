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
            f"{'فوق' if side == 'SHORT' else 'تحت'} الدخول. <b>الخطر:</b> {w['risk_pct']:.1f}% من الرأسمال، يعني ما تخسرش أكثر من {money(p['risk'])} إلا ضرب الـ stop.<br>"
            f"<b>كيتسد ملي:</b> الاتجاه ديال 20 يوم كيتقلب، ولا يضرب الـ stop، ولا Risk يوقف النهار (-3% ولا 3 خسارات متتابعة)."
        )
    return "<b>علاش تحل؟</b> ما تسجلش السبب ديال هاد الـ trade."


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
</div>""", unsafe_allow_html=True)

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
