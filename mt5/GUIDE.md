# TrendDesk EA: الطريقة باش تخدم بيه (خطوة بخطوة)

> كيخدم غير على **حساب demo**. إلا حطيتيه على حساب حقيقي، كيرفض يخدم بوحدو (`InpDemoOnly = true`).

## 1. الحساب ديال Exness
1. فـ Exness Personal Area، صاوب **حساب Demo** من نوع **Standard Cent**، بـ MetaTrader 5، و$100.
2. حمل **MetaTrader 5** على الـ PC (Windows) من Exness، ودخل بالحساب ديال الـ demo.

## 2. تحط الـ EA فـ MT5
1. حمل الملف `TrendDesk.mq5` من GitHub: حل الملف `mt5/TrendDesk.mq5` فالـ repo ← زرّ **Download raw file**.
2. فـ MT5: **File ← Open Data Folder**.
3. حل `MQL5` ← `Experts`، وحط فيه `TrendDesk.mq5`.
4. فـ MT5 كليكي **F4** (كيتحل MetaEditor)، وفاللائحة على اليسار حل `Experts` ← `TrendDesk.mq5`.
5. كليكي **Compile** (ولا **F7**). لتحت خاصك تشوف `0 errors`. إلا كاين شي error: صيفط screenshot.

## 3. Backtest فـ Strategy Tester (قبل أي حاجة)
1. فـ MT5: **View ← Strategy Tester** (ولا **Ctrl+R**).
2. عمر:
   - **Expert:** `TrendDesk`
   - **Symbol:** `XAUUSDc`
   - **Timeframe:** `H1`
   - **Date:** Custom period، من `2023.12.01` حتى اليوم
   - **Modelling:** `Every tick based on real ticks` (إلا ما خدمش: `1 minute OHLC`)
   - **Deposit:** `10000` USC (يعني $100 فـ Cent)
   - **Leverage:** بحال الحساب ديالك
3. فـ **Inputs**: خلي كلشي كيف هو. `InpSymbols` = `XAUUSDc,BTCUSDc,ETHUSDc`.
4. كليكي **Start**. ملي يسالي، صيفط screenshots ديال **Backtest** (النتائج) و**Graph**.
5. عاود نفس الشي بـ `InpUseProfitLock = false` باش نقارنو.

## 4. Demo live
1. حل chart ديال `XAUUSDc`، **H1**.
2. جر `TrendDesk` من **Navigator ← Expert Advisors** للـ chart.
3. فـ **Common**: شعل **Allow Algo Trading**. فـ **Inputs**: خلي كلشي كيف هو ← **OK**.
4. فالفوق ديال MT5، شعل الزرّ **Algo Trading** (خاصو يولي خضر).
5. فالـ chart كيبان النص ديال الحالة: equity، النهار، واش واقف، الاتجاه ديال كل سوق.
6. الـ trades والأسباب ديالهم: **Toolbox ← Experts** (الـ logs).

## 5. باش يبقى خدام 24/7
MT5 خاصو يبقى شاعل. إما الـ PC ديما شاعل، ولا **VPS** (MT5: كليك يمين على الحساب ← **Register a Virtual Server**، تقريبا $10–15 فالشهر).

## الـ Inputs المهمين
| Input | الافتراضي | شنو كيدير |
|---|---|---|
| `InpSymbols` | `XAUUSDc,BTCUSDc,ETHUSDc` | الأسواق |
| `InpRiskPct` | `2.0` | أكبر خطر فكل trade (%) |
| `InpStopATR` | `8.0` | الـ stop = 8 × الحركة العادية ديال ساعة |
| `InpDailyLossPct` | `5.0` | يوقف النهار إلا خسر 5% |
| `InpMaxLosingStreak` | `3` | يوقف النهار من بعد 3 خسارات متتابعة |
| `InpUseProfitLock` | `true` | يسد كلشي ملي النهار +2% |
| `InpProfitLockPct` | `2.0` | قفل الربح (%) |
| `InpServerGMTOffset` | `0` | الوقت ديال السيرفر ناقص GMT (Exness = 0) |
| `InpDemoOnly` | `true` | ما يخدمش على حساب حقيقي |
