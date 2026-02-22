import json, os, glob, pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_DATA_DIR = os.path.join(ROOT_DIR, 'training_data')

# ==============================================================================
# 📜 CONTRACT SPECS & RISK LIMITS (DO NOT DELETE OR MODIFY WITHOUT SYNC)
# ⚠️ THIS BLOCK MUST BE IDENTICAL IN 'main_commander.py'
# ==============================================================================
CONTRACT_SPECS = {
    "NQ": {
        "name": "E-mini NASDAQ-100",
        "exchange": "CME Globex",
        "tick_size": 0.25,
        "tick_value": 5.00,
        "contract_months": ["H (Mar)", "M (Jun)", "U (Sep)", "Z (Dec)"]
    },
    "MNQ": {
        "name": "Micro E-mini NASDAQ-100",
        "exchange": "CME Globex",
        "tick_size": 0.25,
        "tick_value": 0.50,
        "contract_months": ["H (Mar)", "M (Jun)", "U (Sep)", "Z (Dec)"]
    },
    "MARKET_HOURS_ET": {
        "timezone": "US/Eastern",
        "open": 18,
        "close": 17,
        "halt_start": 17,
        "halt_end": 18,
        "hard_stop": 16,
        "maintenance_start": 17,
        "maintenance_end": 18
    },
    "RISK_LIMITS": {
        "DAILY_PROFIT_TARGET": 650.00,
        "MAX_DAILY_LOSS": -500.00,
        "MAX_DRAWDOWN_SESSION": -300.00
    }
}

# ==============================================================================
# 🔒 MASTER PLAYBOOK (DO NOT DELETE OR MODIFY WITHOUT SYNC)
# ⚠️ THIS BLOCK MUST BE IDENTICAL IN 'main_commander.py'
# ==============================================================================
MASTER_PLAYBOOK = {
    "ALGO_STRATEGIES": {
        "MOMENTUM_ALGO": { "desc": "Trade strong RSI/MACD shifts.", "req_oracle": 60 },
        "MEAN_REVERSION_SYSTEM": { "desc": "Fade VWAP/Bollinger extremes.", "req_oracle": 65 },
        "BREAKOUT_BOT": { "desc": "Trade support/resistance breaks.", "req_oracle": 65 },
        "SCALPING_ALGO": { "desc": "High-freq small profit taking.", "req_oracle": 55 },
        "TREND_FOLLOWING_ALGO": { "desc": "Trend continuation on pullback.", "req_oracle": 60 },
        "VOLUME_PROFILE_ALGO": { "desc": "Trade high-volume zones.", "req_oracle": 65 },
        "STAT_ARBITRAGE": { "desc": "Exploit NQ correlation deviations.", "req_oracle": 70 },
        "EVENT_DRIVEN_ALGO": { "desc": "News volatility reaction.", "req_oracle": 80 },
        "MARKET_INTERNALS_ALGO": { "desc": "Breadth-confirmed trades.", "req_oracle": 75 }
    },
    "NON_ALGO_STRATEGIES": {
        "ORB_BREAKOUT": { "desc": "Opening Range Breakout (9:30-10:00).", "stop": 20, "take_profit": 40, "req_oracle": 65 },
        "VWAP_MEAN_REVERSION": { "desc": "Fade moves back to VWAP.", "stop": 15, "take_profit": 30, "req_oracle": 70 },
        "ORDER_FLOW_SCALP": { "desc": "Imbalance scalping (DOM).", "stop": 10, "take_profit": 15, "req_oracle": 60 },
        "BREAK_RETEST": { "desc": "Retest of broken level.", "stop": 15, "take_profit": 35, "req_oracle": 65 },
        "GAP_FADE": { "desc": "Fade overnight gap.", "stop": 20, "take_profit": 40, "req_oracle": 65 },
        "MOMENTUM_BREAKOUT_VOL": { "desc": "Volume-backed breakout.", "stop": 15, "take_profit": 50, "req_oracle": 60 },
        "EMA_TREND_JOIN": { "desc": "Pullback to 9/21 EMA.", "stop": 12, "take_profit": 25, "req_oracle": 60 },
        "MARKET_INTERNAL_REVERSAL": { "desc": "Extreme TICK reversal.", "stop": 15, "take_profit": 20, "req_oracle": 75 },
        "VOL_PROFILE_VA": { "desc": "Value Area rejection.", "stop": 15, "take_profit": 30, "req_oracle": 65 },
        "NEWS_CATALYST_SCALP": { "desc": "Post-news scalp.", "stop": 25, "take_profit": 60, "req_oracle": 80 },
        "FVG_TRADING": { "desc": "Fair Value Gap fill (3-candle imbalance).", "stop": 15, "take_profit": 35, "req_oracle": 65 }
    },
    "PREDICTIVE_AI_ML": {
        "SENTIMENT_MOMENTUM": { "desc": "NLP Sentiment entry.", "req_oracle": 65 },
        "RL_OPTIMIZATION": { "desc": "Reinforcement Learning.", "req_oracle": 60 },
        "EVENT_VOLATILITY": { "desc": "Event swing prediction.", "req_oracle": 80 },
        "AI_STAT_ARB": { "desc": "ML mean reversion.", "req_oracle": 70 },
        "AUTO_PATTERN_REC": { "desc": "DL pattern detection.", "req_oracle": 65 }
    },
    "STOP_LOSS_STRATEGIES": {
        "ATR_STOPS": "2x ATR stop.",
        "NATURAL_SWING": "Stop beyond Swing High/Low.",
        "MULTI_BARRIER": "Stop behind Support + MA.",
        "BRACKET_ORDERS": "Auto-placed fixed stop."
    },
    "RISK_MANAGEMENT": {
        "1_2_PCT_MODEL": "Max 1-2% risk per trade.",
        "3_5_7_RULE": "3% trade / 5% open / 7% port max.",
        "MNQ_SCALING": "Switch to Micro NQ if stop > 2%.",
        "PRE_MARKET_GAPS": "Reduce size in illiquid times."
    }
}
# ==============================================================================

def categorize_strategy(strategy_name):
    if not strategy_name: return "Uncategorized"
    for category, strategies in MASTER_PLAYBOOK.items():
        if strategy_name in strategies: return category
    strat_clean = strategy_name.lower()
    if "ai" in strat_clean or "sentiment" in strat_clean: return "PREDICTIVE_AI_ML"
    if "algo" in strat_clean: return "ALGO_STRATEGIES"
    if "fvg" in strat_clean: return "NON_ALGO_STRATEGIES"
    return "Uncategorized"

def analyze_performance():
    print("🧠 PERFORMANCE ENGINE: Synchronizing Knowledge Base...")
    files = glob.glob(os.path.join(TRAINING_DATA_DIR, "*.json"))
    if not files: return

    total_trades, wins, losses, total_pnl = 0, 0, 0, 0.0
    stats_by_cat = {cat: {"wins": 0, "total": 0} for cat in MASTER_PLAYBOOK.keys()}
    stats_by_cat["Uncategorized"] = {"wins": 0, "total": 0}

    for f in files:
        try:
            with open(f, 'r') as json_file:
                data = json.load(json_file)
                outcome = data.get('estimated_outcome', 'FLAT')
                strat_name = data.get('strategy', 'Unknown')
                category = categorize_strategy(strat_name)
                
                total_trades += 1
                total_pnl += data.get('pnl_change_at_signal', 0.0)
                stats_by_cat[category]["total"] += 1
                if outcome == "WIN":
                    wins += 1
                    stats_by_cat[category]["wins"] += 1
        except: pass

    print("\n" + "="*40)
    print(f"📊 PERFORMANCE REPORT (Generated {datetime.now().strftime('%H:%M')})")
    print("="*40)
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate:     {round((wins/total_trades)*100, 1) if total_trades > 0 else 0}%")
    print(f"Net PnL Est: ${round(total_pnl, 2)}")
    print("-" * 40)
    for cat, stat in stats_by_cat.items():
        if stat["total"] > 0:
            print(f"   - {cat}: {round((stat['wins']/stat['total'])*100,1)}% WR ({stat['total']} trades)")
    print("="*40)

if __name__ == "__main__":
    analyze_performance()