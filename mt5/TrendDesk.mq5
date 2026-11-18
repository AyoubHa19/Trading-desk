//+------------------------------------------------------------------+
//| TrendDesk.mq5                                                    |
//| 20-day trend following + daily risk rules + optional profit lock |
//| Same rules as the Python desk (desk/strategies.py trend_4h,      |
//| desk/risk.py, desk/engine.py). DEMO ACCOUNTS ONLY by default.    |
//+------------------------------------------------------------------+
#property copyright "Trading desk (demo)"
#property version   "1.20"
#property description "Trend 20 days (H4 close vs 120 H4 bars ago), stop 8x ATR(24 H1),"
#property description "2% risk per trade, -5% or 3 losses = stop the New York day,"
#property description "optional +2% profit lock. Demo accounts only unless you change InpDemoOnly."

#include <Trade\Trade.mqh>

//--- inputs
input string InpSymbols         = "XAUUSDc,BTCUSDc,ETHUSDc"; // Symbols to trade (comma separated)
input string InpThemeSymbols    = "BTCUSDc,ETHUSDc";         // Symbols that count as ONE bet (crypto)
input double InpRiskPct         = 2.0;    // Max risk per trade, % of equity
input string InpRiskOverrides   = "";     // Per-symbol risk, e.g. "BTCUSDc:1,ETHUSDc:0.8"
input ENUM_TIMEFRAMES InpCheckTF = PERIOD_H1; // How often the EA decides (tested: H1)
input ENUM_TIMEFRAMES InpTrendTF = PERIOD_H4; // Bars used for the trend (tested: H4)
input ENUM_TIMEFRAMES InpATRTF   = PERIOD_H1; // Bars used for the ATR / stop (tested: H1)
input int    InpLookbackH4      = 120;    // Trend lookback in InpTrendTF bars (120 x H4 = 20 days)
input double InpStopATR         = 8.0;    // Stop distance in ATRs
input double InpTakeProfitATR   = 0.0;    // Take profit distance in ATRs (0 = no take profit, as tested)
input int    InpATRBars         = 24;     // ATR length in InpATRTF bars
input double InpThemeRiskPct    = 5.0;    // Max total risk of the theme symbols, % of equity
input double InpMaxLeverage     = 3.0;    // Max total position value / equity
input double InpDailyLossPct    = 5.0;    // Stop the New York day after this loss %
input int    InpMaxLosingStreak = 3;      // Stop the New York day after N losing trades in a row
input bool   InpUseProfitLock   = true;   // Close everything once the day is up InpProfitLockPct
input double InpProfitLockPct   = 2.0;    // Profit lock, % of the day's starting equity
input double InpMaxSpreadShare  = 0.25;   // Skip a trade if spread > this share of the stop distance
input int    InpServerGMTOffset = 0;      // Broker server time minus GMT, in hours (Exness = 0)
input long   InpMagic           = 20261118; // Magic number (identifies this EA's trades)
input bool   InpAllowNewTrades  = true;   // false = only manage trades already open
input bool   InpDemoOnly        = true;   // Refuse to trade on a real account

//--- state
CTrade   g_trade;
string   g_syms[];
double   g_risk[];
bool     g_theme[];
int      g_blocked[];      // direction we were stopped out of (no re-entry until the signal resets)
datetime g_lastHour = 0;
int      g_dayKey = 0;
double   g_dayStartEq = 0;
bool     g_halted = false;
int      g_streak = 0;
string   g_haltReason = "";

//+------------------------------------------------------------------+
//| Small helpers                                                    |
//+------------------------------------------------------------------+
string Trim(string s) { StringTrimLeft(s); StringTrimRight(s); return s; }

string GV(string name) { return "TD_" + IntegerToString(InpMagic) + "_" + name; }

void SaveState()
{
   GlobalVariableSet(GV("dayKey"), g_dayKey);
   GlobalVariableSet(GV("dayStartEq"), g_dayStartEq);
   GlobalVariableSet(GV("halted"), g_halted ? 1 : 0);
   GlobalVariableSet(GV("streak"), g_streak);
   for(int i = 0; i < ArraySize(g_syms); i++)
      GlobalVariableSet(GV("blk_" + g_syms[i]), g_blocked[i]);
}

void LoadState()
{
   if(GlobalVariableCheck(GV("dayKey")))     g_dayKey     = (int)GlobalVariableGet(GV("dayKey"));
   if(GlobalVariableCheck(GV("dayStartEq"))) g_dayStartEq = GlobalVariableGet(GV("dayStartEq"));
   if(GlobalVariableCheck(GV("halted")))     g_halted     = GlobalVariableGet(GV("halted")) > 0.5;
   if(GlobalVariableCheck(GV("streak")))     g_streak     = (int)GlobalVariableGet(GV("streak"));
   for(int i = 0; i < ArraySize(g_syms); i++)
      if(GlobalVariableCheck(GV("blk_" + g_syms[i])))
         g_blocked[i] = (int)GlobalVariableGet(GV("blk_" + g_syms[i]));
}

int SymIndex(string s)
{
   for(int i = 0; i < ArraySize(g_syms); i++)
      if(g_syms[i] == s) return i;
   return -1;
}

//--- New York day (US daylight saving: 2nd Sunday of March to 1st Sunday of November)
datetime NthSunday(int year, int mon, int n)
{
   MqlDateTime t;
   t.year = year; t.mon = mon; t.day = 1; t.hour = 0; t.min = 0; t.sec = 0;
   datetime d = StructToTime(t);
   TimeToStruct(d, t);
   int first = (7 - t.day_of_week) % 7;
   return d + (first + 7 * (n - 1)) * 86400;
}

bool IsUSDST(datetime gmt)
{
   MqlDateTime t;
   TimeToStruct(gmt, t);
   datetime start = NthSunday(t.year, 3, 2) + 7 * 3600;   // 02:00 EST = 07:00 GMT
   datetime end   = NthSunday(t.year, 11, 1) + 6 * 3600;  // 02:00 EDT = 06:00 GMT
   return gmt >= start && gmt < end;
}

int NYDayKey()
{
   datetime gmt = TimeCurrent() - InpServerGMTOffset * 3600;
   datetime ny  = gmt - (IsUSDST(gmt) ? 4 : 5) * 3600;
   MqlDateTime t;
   TimeToStruct(ny, t);
   return t.year * 10000 + t.mon * 100 + t.day;
}

//--- market data
// +1 when the last completed H4 close is above the close InpLookbackH4 bars earlier, -1 below, 0 unknown
int TrendSignal(string s, double &now, double &then, double &nextLine)
{
   double c[];
   ArraySetAsSeries(c, true);
   int need = InpLookbackH4 + 1;
   if(CopyClose(s, InpTrendTF, 1, need, c) != need) return 0;
   now = c[0];
   then = c[InpLookbackH4];
   nextLine = c[InpLookbackH4 - 1];   // the reference price at the NEXT H4 close
   if(now > then) return 1;
   if(now < then) return -1;
   return 0;
}

double ATRH1(string s)
{
   MqlRates r[];
   ArraySetAsSeries(r, true);
   int n = InpATRBars;
   if(CopyRates(s, InpATRTF, 1, n + 1, r) != n + 1) return 0;
   double sum = 0;
   for(int i = 0; i < n; i++)
   {
      double pc = r[i + 1].close;
      double tr = MathMax(r[i].high - r[i].low, MathMax(MathAbs(r[i].high - pc), MathAbs(r[i].low - pc)));
      sum += tr;
   }
   return sum / n;
}

// account money per 1.0 price move for 1 lot
double ValuePerPriceUnit(string s)
{
   double tv = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0) tv = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) return 0;
   return tv / ts;
}

int VolumeDigits(double step)
{
   int d = 0;
   while(d < 8 && MathAbs(step * MathPow(10, d) - MathRound(step * MathPow(10, d))) > 1e-9) d++;
   return d;
}

double RoundLots(string s, double lots)
{
   double step = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(s, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(s, SYMBOL_VOLUME_MAX);
   if(step <= 0) return 0;
   lots = MathFloor(lots / step + 1e-9) * step;     // always round DOWN: never more risk than allowed
   if(lots < mn) return 0;
   if(lots > mx) lots = mx;
   return NormalizeDouble(lots, VolumeDigits(step));
}

//--- our positions
bool GetPosition(string s, ulong &ticket, int &dir, double &risk, double &value)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != s || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      ticket = t;
      dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      double vol = PositionGetDouble(POSITION_VOLUME);
      double vpu = ValuePerPriceUnit(s);
      double sl  = PositionGetDouble(POSITION_SL);
      double op  = PositionGetDouble(POSITION_PRICE_OPEN);
      risk  = (sl > 0) ? MathAbs(op - sl) * vpu * vol : 0;
      value = PositionGetDouble(POSITION_PRICE_CURRENT) * vpu * vol;
      return true;
   }
   ticket = 0; dir = 0; risk = 0; value = 0;
   return false;
}

void CloseAll(string why)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      string s = PositionGetString(POSITION_SYMBOL);
      if(g_trade.PositionClose(t))
         PrintFormat("CLOSE %s: %s", s, why);
      else
         PrintFormat("CLOSE %s FAILED (%s): retcode %d", s, why, g_trade.ResultRetcode());
   }
}

//+------------------------------------------------------------------+
//| Daily rules                                                      |
//+------------------------------------------------------------------+
void UpdateDay()
{
   int key = NYDayKey();
   if(key != g_dayKey)
   {
      g_dayKey = key;
      g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(g_halted) g_streak = 0;
      g_halted = false;
      g_haltReason = "";
      PrintFormat("New York day %d: start equity %.2f", key, g_dayStartEq);
      SaveState();
   }
}

void Halt(string why)
{
   g_halted = true;
   g_haltReason = why;
   PrintFormat("RISK HALT: %s -> close everything, no new trades until the next New York day", why);
   CloseAll(why);
   SaveState();
}

void CheckDay()
{
   if(g_halted || g_dayStartEq <= 0) return;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double chg = eq / g_dayStartEq - 1.0;
   if(chg <= -InpDailyLossPct / 100.0)
      Halt(StringFormat("daily loss %.2f%%", 100 * chg));
   else if(g_streak >= InpMaxLosingStreak)
      Halt(StringFormat("%d losing trades in a row", g_streak));
   else if(InpUseProfitLock && chg >= InpProfitLockPct / 100.0)
      Halt(StringFormat("profit lock +%.2f%%", 100 * chg));
}

//+------------------------------------------------------------------+
//| The hourly decision                                              |
//+------------------------------------------------------------------+
void Hourly()
{
   UpdateDay();
   CheckDay();

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   for(int i = 0; i < ArraySize(g_syms); i++)
   {
      string s = g_syms[i];
      double now = 0, then = 0, nextLine = 0;
      int sig = TrendSignal(s, now, then, nextLine);
      int want = g_halted ? 0 : sig;

      // after a stop, no re-entry in the same direction until the signal changes
      if(g_blocked[i] != 0 && want == g_blocked[i]) want = 0;
      else if(want != g_blocked[i]) g_blocked[i] = 0;

      ulong ticket; int have; double prisk, pvalue;
      GetPosition(s, ticket, have, prisk, pvalue);

      if(have != 0 && have != want)
      {
         if(g_trade.PositionClose(ticket))
            PrintFormat("CLOSE %s: 20-day trend turned (now %.5f vs %.5f 20 days ago)", s, now, then);
         have = 0;
      }
      if(want == 0 || have != 0 || !InpAllowNewTrades) continue;

      // ---- size the new trade
      double atr = ATRH1(s);
      double stopDist = InpStopATR * atr;
      double vpu = ValuePerPriceUnit(s);
      if(atr <= 0 || vpu <= 0) { PrintFormat("SKIP %s: no data yet", s); continue; }

      double riskMoney = eq * g_risk[i] / 100.0;
      double themeOpen = 0, gross = 0;
      for(int k = 0; k < ArraySize(g_syms); k++)
      {
         ulong tk; int d; double r, v;
         if(GetPosition(g_syms[k], tk, d, r, v))
         {
            gross += v;
            if(g_theme[k] && g_theme[i]) themeOpen += r;
         }
      }
      if(g_theme[i]) riskMoney = MathMin(riskMoney, eq * InpThemeRiskPct / 100.0 - themeOpen);
      if(riskMoney <= 0) { PrintFormat("SKIP %s: theme risk limit reached", s); continue; }

      double lots = RoundLots(s, riskMoney / (stopDist * vpu));
      double price = (want > 0) ? SymbolInfoDouble(s, SYMBOL_ASK) : SymbolInfoDouble(s, SYMBOL_BID);
      double maxValue = InpMaxLeverage * eq - gross;
      if(lots > 0 && lots * price * vpu > maxValue)
         lots = RoundLots(s, maxValue / (price * vpu));
      if(lots <= 0)
      {
         PrintFormat("SKIP %s: even the minimum lot would risk more than %.2f%% (use a Cent account or more capital)", s, g_risk[i]);
         continue;
      }

      double spread = SymbolInfoDouble(s, SYMBOL_ASK) - SymbolInfoDouble(s, SYMBOL_BID);
      if(spread > InpMaxSpreadShare * stopDist)
      {
         PrintFormat("SKIP %s: spread %.5f too big for a stop of %.5f", s, spread, stopDist);
         continue;
      }

      int digits = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
      double sl = NormalizeDouble(want > 0 ? price - stopDist : price + stopDist, digits);
      double tp = 0;
      if(InpTakeProfitATR > 0)
         tp = NormalizeDouble(want > 0 ? price + InpTakeProfitATR * atr : price - InpTakeProfitATR * atr, digits);
      string why = StringFormat("TD %s 20d %+.1f%%", want > 0 ? "LONG" : "SHORT", 100.0 * (now / then - 1.0));
      g_trade.SetTypeFillingBySymbol(s);
      // Buy/Sell(volume, symbol, price (0 = market), stop loss, take profit (0 = none), comment)
      bool ok = (want > 0) ? g_trade.Buy(lots, s, 0, sl, tp, why) : g_trade.Sell(lots, s, 0, sl, tp, why);
      if(ok)
         PrintFormat("OPEN %s %s %.2f lots @ %.5f, stop %.5f (%.1f ATR), risk %.2f. Why: price %.5f vs %.5f 20 days ago (%+.1f%%)",
                     want > 0 ? "LONG" : "SHORT", s, lots, price, sl, InpStopATR, lots * stopDist * vpu, now, then, 100.0 * (now / then - 1.0));
      else
         PrintFormat("OPEN %s FAILED: %d %s (will retry at the next check)", s, g_trade.ResultRetcode(),
                     g_trade.ResultRetcodeDescription());
   }
   SaveState();
   ShowStatus();
}

void ShowStatus()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   string txt = StringFormat("TrendDesk | equity %.2f | today %+.2f%% | %s | losing streak %d\n",
                             eq, g_dayStartEq > 0 ? 100 * (eq / g_dayStartEq - 1) : 0.0,
                             g_halted ? "STOPPED: " + g_haltReason : "running", g_streak);
   for(int i = 0; i < ArraySize(g_syms); i++)
   {
      double now = 0, then = 0, nextLine = 0;
      int sig = TrendSignal(g_syms[i], now, then, nextLine);
      ulong tk; int d; double r, v;
      GetPosition(g_syms[i], tk, d, r, v);
      txt += StringFormat("%s: trend %s | position %s | line now %.5f, next line %.5f\n", g_syms[i],
                          sig > 0 ? "UP" : sig < 0 ? "DOWN" : "?", d > 0 ? "LONG" : d < 0 ? "SHORT" : "none", then, nextLine);
   }
   Comment(txt);
}

//+------------------------------------------------------------------+
//| Events                                                           |
//+------------------------------------------------------------------+
int OnInit()
{
   bool tester = (bool)MQLInfoInteger(MQL_TESTER);
   if(InpDemoOnly && !tester && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
   {
      Alert("TrendDesk: this is not a DEMO account. Trading refused (InpDemoOnly = true).");
      return INIT_FAILED;
   }

   string parts[];
   int n = StringSplit(InpSymbols, ',', parts);
   ArrayResize(g_syms, 0);
   for(int i = 0; i < n; i++)
   {
      string s = Trim(parts[i]);
      if(s == "") continue;
      if(!SymbolSelect(s, true)) { Alert("TrendDesk: symbol not found: ", s); return INIT_FAILED; }
      int k = ArraySize(g_syms);
      ArrayResize(g_syms, k + 1);
      g_syms[k] = s;
   }
   int m = ArraySize(g_syms);
   if(m == 0) { Alert("TrendDesk: no symbols"); return INIT_FAILED; }
   ArrayResize(g_risk, m);
   ArrayResize(g_theme, m);
   ArrayResize(g_blocked, m);
   ArrayInitialize(g_blocked, 0);

   string theme[];
   int nt = StringSplit(InpThemeSymbols, ',', theme);
   for(int i = 0; i < m; i++)
   {
      g_risk[i] = InpRiskPct;
      g_theme[i] = false;
      for(int k = 0; k < nt; k++)
         if(Trim(theme[k]) == g_syms[i]) g_theme[i] = true;
   }
   string ov[];
   int no = StringSplit(InpRiskOverrides, ',', ov);
   for(int k = 0; k < no; k++)
   {
      string kv[];
      if(StringSplit(Trim(ov[k]), ':', kv) == 2)
      {
         int idx = SymIndex(Trim(kv[0]));
         if(idx >= 0) g_risk[idx] = MathMin(InpRiskPct, StringToDouble(kv[1]));
      }
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(50);
   LoadState();
   EventSetTimer(30);
   PrintFormat("TrendDesk started on %d symbols, risk %.1f%%, profit lock %s, check %s, trend %s x%d, ATR %s",
               m, InpRiskPct, InpUseProfitLock ? "ON" : "OFF", EnumToString(InpCheckTF), EnumToString(InpTrendTF),
               InpLookbackH4, EnumToString(InpATRTF));
   if(InpCheckTF != PERIOD_H1 || InpTrendTF != PERIOD_H4 || InpATRTF != PERIOD_H1)
      Print("TrendDesk: TEST timeframes - this is NOT the tested strategy, use it only to check orders and stops");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void Tick()
{
   long step = PeriodSeconds(InpCheckTF);                     // H1 = 3600 s, M5 = 300 s
   datetime hour = (datetime)(((long)TimeCurrent() / step) * step);
   if(hour != g_lastHour)
   {
      g_lastHour = hour;
      Hourly();
   }
}

void OnTick()  { Tick(); }
void OnTimer() { Tick(); }

// Count losing streaks and remember stop-outs
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) return;

   double pnl = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) + HistoryDealGetDouble(trans.deal, DEAL_SWAP)
              + HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   g_streak = (pnl < 0) ? g_streak + 1 : 0;

   long reason = HistoryDealGetInteger(trans.deal, DEAL_REASON);
   if(reason == DEAL_REASON_SL || reason == DEAL_REASON_TP)   // after a stop or a take profit: wait for a new signal
   {
      int idx = SymIndex(HistoryDealGetString(trans.deal, DEAL_SYMBOL));
      // a SELL deal closes a LONG position, a BUY deal closes a SHORT one
      if(idx >= 0) g_blocked[idx] = (HistoryDealGetInteger(trans.deal, DEAL_TYPE) == DEAL_TYPE_SELL) ? 1 : -1;
      PrintFormat("%s hit on %s, pnl %.2f", reason == DEAL_REASON_TP ? "TAKE PROFIT" : "STOP",
                  HistoryDealGetString(trans.deal, DEAL_SYMBOL), pnl);
   }
   SaveState();
}
//+------------------------------------------------------------------+
