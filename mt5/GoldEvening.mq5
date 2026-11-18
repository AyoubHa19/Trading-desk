//+------------------------------------------------------------------+
//| GoldEvening.mq5                                                  |
//| Hypothesis from Exness XAUUSDm H1 data (2022-2026): gold drifts  |
//| UP between 20:00 and midnight server time (GMT). Buy at 20:00,   |
//| sell just before midnight, Monday-Thursday. DEMO ONLY by default.|
//+------------------------------------------------------------------+
#property copyright "Trading desk (demo)"
#property version   "1.00"
#property description "Buys gold at InpEntryHour and closes it at InpExitHour:InpExitMinute (server time),"
#property description "Monday to Thursday. Safety stop. Size = InpLeverage x equity. Demo accounts only."

#include <Trade\Trade.mqh>

input string InpSymbol      = "XAUUSDm"; // Symbol
input int    InpEntryHour   = 20;        // Entry hour (server time)
input int    InpExitHour    = 23;        // Exit hour (server time)
input int    InpExitMinute  = 55;        // Exit minute
input double InpLeverage    = 1.0;       // Position value / equity (1.0 = no leverage)
input double InpStopPct     = 1.5;       // Safety stop, % below entry
input double InpMaxSpread   = 0.60;      // Skip the day if the spread is above this (price units)
input bool   InpFridays     = false;     // Trade on Fridays too (gold closes early on Friday)
input long   InpMagic       = 777;       // Magic number
input bool   InpDemoOnly    = true;      // Refuse to trade on a real account

CTrade g_trade;
int    g_lastEntryDay = 0;

int DayKey(datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.year * 10000 + s.mon * 100 + s.day; }

bool HasPosition(ulong &ticket)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) == InpSymbol && PositionGetInteger(POSITION_MAGIC) == InpMagic)
      { ticket = t; return true; }
   }
   ticket = 0;
   return false;
}

double LotsForValue(double value)
{
   double tv = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   double price = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   if(tv <= 0 || ts <= 0 || price <= 0) return 0;
   double valuePerLot = price / ts * tv;            // account money for 1 lot at today's price
   double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MAX);
   double lots = MathFloor(value / valuePerLot / step + 1e-9) * step;   // round DOWN
   if(lots < mn) return 0;
   return MathMin(lots, mx);
}

void Check()
{
   datetime now = TimeCurrent();
   MqlDateTime s;
   TimeToStruct(now, s);
   ulong ticket;
   bool open = HasPosition(ticket);

   // ---- exit: just before midnight (and never hold into the next day)
   if(open && (s.hour > InpExitHour || (s.hour == InpExitHour && s.min >= InpExitMinute) || s.hour < InpEntryHour))
   {
      if(g_trade.PositionClose(ticket)) Print("CLOSE evening position");
      return;
   }

   // ---- entry: once per day, in the entry hour, Monday-Thursday (Friday optional)
   bool weekday = (s.day_of_week >= 1 && s.day_of_week <= 4) || (InpFridays && s.day_of_week == 5);
   if(open || !weekday || s.hour != InpEntryHour || g_lastEntryDay == DayKey(now)) return;

   double ask = SymbolInfoDouble(InpSymbol, SYMBOL_ASK), bid = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   if(ask - bid > InpMaxSpread) { PrintFormat("SKIP: spread %.2f > %.2f", ask - bid, InpMaxSpread); g_lastEntryDay = DayKey(now); return; }

   double lots = LotsForValue(AccountInfoDouble(ACCOUNT_EQUITY) * InpLeverage);
   if(lots <= 0) { Print("SKIP: account too small for the minimum lot at this leverage"); g_lastEntryDay = DayKey(now); return; }

   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   double sl = NormalizeDouble(ask * (1.0 - InpStopPct / 100.0), digits);
   g_trade.SetTypeFillingBySymbol(InpSymbol);
   if(g_trade.Buy(lots, InpSymbol, 0, sl, 0, "GoldEvening"))
      PrintFormat("BUY %.2f lots %s @ %.3f, safety stop %.3f", lots, InpSymbol, ask, sl);
   else
      PrintFormat("BUY FAILED: %d %s", g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
   g_lastEntryDay = DayKey(now);
}

int OnInit()
{
   if(InpDemoOnly && !(bool)MQLInfoInteger(MQL_TESTER) && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
   { Alert("GoldEvening: not a DEMO account. Trading refused."); return INIT_FAILED; }
   if(!SymbolSelect(InpSymbol, true)) { Alert("GoldEvening: symbol not found: ", InpSymbol); return INIT_FAILED; }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(50);
   EventSetTimer(20);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }
void OnTick()  { Check(); }
void OnTimer() { Check(); }
//+------------------------------------------------------------------+
