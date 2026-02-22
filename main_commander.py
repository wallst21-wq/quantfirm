import os
import sys
import logging
import time
import datetime
import json
import re
import requests
import io
import pickle
import collections
import subprocess
import pandas as pd
import numpy as np

# --- 🔇 SILENCE LOGS ---
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "3"
logging.getLogger("google.genai").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)

from google import genai
from google.genai import types

# --- 🧠 MODEL CONFIGURATION (2026 STANDARDS) ---
# Defines which AI Brain uses which Gemini Version

# 1. Intelligence Engine (Agents: CIO, Risk, Strat)
# We use Gemini 1.5 Pro (Stable) for high-IQ reasoning
SMART_MODEL = "gemini-2.5-pro" 

# 2. Speed Engine (Sniper checks)
# We use Gemini 2 Flash for sub-second execution
FAST_MODEL = "gemini-2.5-flash"

# 3. Default Fallback
MODEL_NAME = SMART_MODEL

# --- 🧠 ML LIBRARIES ---
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model, Model
    import xgboost as xgb
    from sklearn.preprocessing import RobustScaler
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError as e:
    print(f"❌ Warning: ML Libraries missing ({e}). Sniper running in Logic Mode.")

# --- 🔧 CONFIGURATION (LIVE) ---
# API KEYS
GEMINI_API_KEY = "AIzaSyC4kRiyNVht0HFmmrL2zcUAd3GZrQnQvoM"
FMP_API_KEY = "uRNcyQLBibUhCXeALztwMHcCTNmuDRft"       
FINNHUB_API_KEY = "d5beev9r01qnaidt4nlgd5beev9r01qnaidt4nm0" 

# CROSSTRADE
WEBHOOK_URL = "https://app.crosstrade.io/v1/send/Hunm2Ve4/1PG9b8GEukklVI8pnmeT3Q"
CT_API_KEY = "zmHO2C_5QNvtW2wBFfJBbu98f4h5R24YRtkhFjFfSfc"
ACCOUNT_NAME = "Sim101"

# PATHS
CMD_FILE = r"C:\Data\bridge_commands.json"
MARKET_DATA = r"C:\Data\MarketData.csv"
TRAINING_DIR = r"C:\Data\training_data"
TRAINER_SCRIPT = "model_trainer.py"

# ML PATHS
MODEL_NN_PATH = r"C:\Data\hybrid_feature_extractor.h5"
MODEL_XGB_PATH = r"C:\Data\xgb_decision_maker.json"
SCALER_PATH = r"C:\Data\scaler.pkl"

# MODELS
MODEL_CIO = SMART_MODEL 
MODEL_AGENTS = FAST_MODEL

# TRADING
SYMBOL = "MNQ 03-26"
QTY = 1

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler("commander.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found.")
    sys.exit()

client = genai.Client(api_key=GEMINI_API_KEY)

# ==============================================================================
# 📜 CONTRACT SPECS & RISK LIMITS (DO NOT DELETE OR MODIFY WITHOUT SYNC)
# ⚠️ THIS BLOCK MUST BE IDENTICAL IN 'performance_engine.py'
# ==============================================================================
CONTRACT_SPECS = {
    "NQ": {
        "name": "E-mini NASDAQ-100",
        "exchange": "CME Globex",
        "tick_size": 0.25,
        "tick_value": 5.00, # $20 per point
        "contract_months": ["H (Mar)", "M (Jun)", "U (Sep)", "Z (Dec)"]
    },
    "MNQ": {
        "name": "Micro E-mini NASDAQ-100",
        "exchange": "CME Globex",
        "tick_size": 0.25,
        "tick_value": 0.50, # $2 per point
        "contract_months": ["H (Mar)", "M (Jun)", "U (Sep)", "Z (Dec)"]
    },
    "MARKET_HOURS_ET": {
        "timezone": "US/Eastern",
        "open": 18,   # 6:00 PM ET (Sunday Open / Daily Open)
        "close": 17,  # 5:00 PM ET (Daily Close)
        "halt_start": 17, # 5:00 PM ET
        "halt_end": 18,   # 6:00 PM ET
        "hard_stop": 14,  # 2:00 PM CST / 3:00 PM EST (Stop 1hr before close)
        "maintenance_start": 17, # 5:00 PM ET
        "maintenance_end": 18    # 6:00 PM ET
    },
    "RISK_LIMITS": {
        "DAILY_PROFIT_TARGET": 650.00,
        "MAX_DAILY_LOSS": -500.00,
        "MAX_DRAWDOWN_SESSION": -300.00
    }
}

# ==============================================================================
# 🔒 MASTER PLAYBOOK (DO NOT DELETE OR MODIFY WITHOUT SYNC)
# ⚠️ THIS BLOCK MUST BE IDENTICAL IN 'performance_engine.py'
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

# --- GLOBAL STATE ---
QUANT_BRAIN = {"nn": None, "xgb": None, "scaler": None, "active": False}
MISSION_STATE = {
    "CIO_VOTE": "FLAT", "RO_VOTE": "FLAT", "STRAT_VOTE": "FLAT",
    "LAST_TRADE_TIME": 0, "DEFCON": 5,
    "NEWS_CONTEXT": "No major news yet.",
    "SENTIMENT_SCORE": 50,
    "MARKET_STATUS": "OPEN",
    "DAILY_PNL": 0.0,
    "OPEN_PNL": 0.0,
    "TRAINING_COMPLETED_TODAY": False,
    "CURRENT_QTY": 0, # Tracks how many contracts we think we hold
    "CURRENT_SIDE": "FLAT", # Tracks if we are Long or Short
}

# ==========================================
# 💾 STATE PERSISTENCE (Prevent Memory Loss)
# ==========================================
import json
STATE_FILE = "bot_state.json"

def save_mission_state():
    try:
        with open(STATE_FILE, 'w') as f:
            # We only save the critical position data
            data_to_save = {
                "CURRENT_QTY": MISSION_STATE["CURRENT_QTY"],
                "CURRENT_SIDE": MISSION_STATE["CURRENT_SIDE"]
            }
            json.dump(data_to_save, f)
    except Exception as e:
        logging.error(f"State Save Failed: {e}")

def load_mission_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                saved = json.load(f)
                MISSION_STATE["CURRENT_QTY"] = saved.get("CURRENT_QTY", 0)
                MISSION_STATE["CURRENT_SIDE"] = saved.get("CURRENT_SIDE", "FLAT")
                logging.info(f"♻️ RESTORED STATE: {MISSION_STATE['CURRENT_SIDE']} x{MISSION_STATE['CURRENT_QTY']}")
        except Exception as e:
            logging.error(f"State Load Failed: {e}")

# ==========================================
# 🕒 0. MARKET TIME & MAINTENANCE
# ==========================================
def check_market_status():
    """ Enforces Contract Hours, Daily Limits & Maintenance Windows (CST ALIGNED) """
def check_market_status():
    """ 
    Enforces Contract Hours, Daily Limits & Maintenance Windows
    ⚠️ Server runs in CST timezone
    🎯 STOPS TRADING AT 3 PM EST (2 PM CST) - 1 hour before 4 PM EST close
    """
    
    # 1. Check Daily PnL Limits
    if MISSION_STATE["DAILY_PNL"] >= CONTRACT_SPECS["RISK_LIMITS"]["DAILY_PROFIT_TARGET"]:
        return "DAILY_HALT_WIN"
    if MISSION_STATE["DAILY_PNL"] <= CONTRACT_SPECS["RISK_LIMITS"]["MAX_DAILY_LOSS"]:
        return "DAILY_HALT_LOSS"

    # 2. Check Time (Server is CST)
    now = datetime.datetime.now()
    hour = now.hour
    weekday = now.weekday() # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    
    # Weekend Logic (Friday 4PM CST to Sunday 5PM CST)
    if weekday == 4 and hour >= 16: return "MAINTENANCE" # Friday Night
    if weekday == 5: return "MAINTENANCE" # Saturday
    if weekday == 6 and hour < 17: return "MAINTENANCE" # Sunday Day
    
    # Daily Maintenance (4PM - 5PM CST = 5PM - 6PM EST)
    if hour == 16: return "MAINTENANCE"
    
    # ✅ FIXED: Hard Stop at 2PM CST (3PM EST) - 1 hour before 4PM EST close
    if hour >= 14: return "SLEEP"
    
    return "OPEN"

def run_auto_training():
    """ Triggers Model Training during Maintenance """
    if MISSION_STATE["TRAINING_COMPLETED_TODAY"]: return

    logging.info("🛠️ MAINTENANCE WINDOW: Starting Auto-Training Protocol...")
    
    try:
        if not os.path.exists(TRAINING_DIR): os.makedirs(TRAINING_DIR)
        
        logging.info("   ... Launching model_trainer.py ...")
        # Ensure we are in the correct directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        trainer_path = os.path.join(current_dir, TRAINER_SCRIPT)
        
        if os.path.exists(trainer_path):
            subprocess.run(["python", trainer_path], check=True)
            MISSION_STATE["TRAINING_COMPLETED_TODAY"] = True
            logging.info("✅ Auto-Training Complete. Models Updated.")
            # Reload Brain
            load_quant_brain()
        else:
            logging.error(f"❌ Trainer script not found: {trainer_path}")
        
    except Exception as e:
        logging.error(f"❌ Auto-Training Failed: {e}")

# ==========================================
# 📡 1. EXTERNAL INTELLIGENCE
# ==========================================
def fetch_fmp_calendar():
    try:
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?apikey={FMP_API_KEY}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            events = r.json()[:3]
            return ", ".join([f"{e.get('event')} ({e.get('impact')})" for e in events])
    except: pass
    return "No Data"

def fetch_finnhub_sentiment():
    try:
        url = f"https://finnhub.io/api/v1/news-sentiment?symbol=QQQ&token={FINNHUB_API_KEY}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            score = data.get('sentiment', {}).get('bullishPercent', 0.5) * 100
            MISSION_STATE["SENTIMENT_SCORE"] = score
            return f"Market Sentiment: {score:.0f}% Bullish"
    except: pass
    return "Sentiment Neutral"

def read_ninja_pnl():
    """ Placeholder: In real production, this reads a file exported by NT8 strategies """
    # For now, we simulate logic or read a dump file if you implement the NT8 exporter
    return 0.0, 0.0 

# ==========================================
# 🧠 2. QUANT BRAIN & BLACK BOX RECORDER
# ==========================================
def load_quant_brain():
    if not os.path.exists(MODEL_NN_PATH): return
    try:
        # Load Main Model
        QUANT_BRAIN["nn"] = load_model(MODEL_NN_PATH)
        
        # --- FIX: CREATE EXTRACTOR ONCE HERE ---
        # Create the sub-model that extracts features from the fusion layer
        QUANT_BRAIN["extractor"] = Model(
            inputs=QUANT_BRAIN["nn"].input, 
            outputs=QUANT_BRAIN["nn"].get_layer('fusion_layer').output
        )
        # ---------------------------------------

        QUANT_BRAIN["xgb"] = xgb.Booster()
        QUANT_BRAIN["xgb"].load_model(MODEL_XGB_PATH)
        with open(SCALER_PATH, 'rb') as f: QUANT_BRAIN["scaler"] = pickle.load(f)
        QUANT_BRAIN["active"] = True
        logging.info("✅ Quant Brain Online (Hybrid Engine).")
    except Exception as e: logging.error(f"Brain Error: {e}")

def save_black_box_data(df, action, prob, reason):
    """ Saves trade context for future training """
    if not os.path.exists(TRAINING_DIR): os.makedirs(TRAINING_DIR)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_json = f"{TRAINING_DIR}/TRADE_{timestamp}_{action}.json"
    filename_img = f"{TRAINING_DIR}/TRADE_{timestamp}_{action}.png"
    
    # 1. Save Logic
    data = {
        "symbol": SYMBOL,
        "entry_time": str(datetime.datetime.now()),
        "action": action,
        "confidence": float(prob),
        "reason": reason,
        "market_context": {
            "sentiment": MISSION_STATE["SENTIMENT_SCORE"],
            "cio_vote": MISSION_STATE["CIO_VOTE"]
        }
    }
    with open(filename_json, 'w') as f: json.dump(data, f, indent=2)
    
    # 2. Save Chart
    try:
        last_seq = df.iloc[-50:]
        fig = plt.figure(figsize=(2, 2), dpi=32)
        ax = fig.add_subplot(111)
        vals = last_seq['Close'].values
        norm_vals = (vals - np.mean(vals)) / (np.std(vals) + 1e-5)
        ax.plot(norm_vals, color='black', linewidth=2)
        ax.axis('off')
        plt.savefig(filename_img, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        plt.close('all')
    except: pass

def get_quant_signal(df_window):
    if not QUANT_BRAIN["active"] or len(df_window) < 50: return 0.5
    try:
        df = df_window.copy()
        if 'Volume' not in df.columns: df['Volume'] = 1.0
        for c in ['Close','High','Low','Open','Volume']: df[c] = pd.to_numeric(df[c], errors='coerce')
        
        df['Ret_Close'] = df['Close'].pct_change()
        df['Ret_Vol'] = df['Volume'].pct_change().replace([np.inf, -np.inf], 0)
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = (100 - (100 / (1 + rs))) / 100.0
        
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df.dropna(inplace=True)
        
        last_seq = df.iloc[-50:]
        raw_seq = last_seq[['Ret_Close', 'Ret_Vol', 'RSI', 'MACD']].values
        flat_seq = raw_seq.reshape(-1, 4)
        scaled_flat = QUANT_BRAIN["scaler"].transform(flat_seq)
        scaled_seq = scaled_flat.reshape(1, 50, 4)
        
        buf = io.BytesIO()
        fig = plt.figure(figsize=(2, 2), dpi=32)
        ax = fig.add_subplot(111)
        vals = last_seq['Close'].values
        norm_vals = (vals - np.mean(vals)) / (np.std(vals) + 1e-5)
        ax.plot(norm_vals, color='black', linewidth=2)
        ax.axis('off')
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        
        buf.seek(0)
        img = tf.io.decode_png(buf.getvalue(), channels=1)
        img = tf.image.resize(img, (64, 64)) / 255.0
        img_input = tf.reshape(img, (1, 64, 64, 1))
        
        
        meta = QUANT_BRAIN["extractor"].predict([img_input, scaled_seq], verbose=0)
        
        dtest = xgb.DMatrix(meta)
        return QUANT_BRAIN["xgb"].predict(dtest)[0]
    except: return 0.5

# ==========================================
# 🗣️ 3. AGENT LOGIC
# ==========================================
def get_agent_vote(role, df, news_context, model_name):
    latest = df.iloc[-1]
    current_price = latest['Close']
    
    # Define timeframe for each role
    timeframes = {
        "CIO": "30-60 minutes",
        "RISK": "15-30 minutes", 
        "STRAT": "5-15 minutes",
        "SNIPER_LOGIC": "1-5 minutes"
    }
    timeframe = timeframes.get(role, "Unknown")
    
    # Check if position review
    is_position_review = "MANAGEMENT" in news_context or "AUDIT" in news_context or "LONE WOLF" in news_context
    
    if is_position_review:
        # Position review prompt (unchanged from before)
        prompt = f"""
ROLE: {role} of Elite Quant Trading Firm
POSITION REVIEW: {news_context}
CURRENT DATA: Price {current_price:.2f}, RSI {df['RSI'].iloc[-1]:.1f}

DECISION: Should we HOLD or CLOSE this position?

OUTPUT FORMAT (STRICT):
DECISION: [HOLD/CLOSE]
CONFIDENCE: [0-100]%
REASONING: [Brief 1-sentence explanation]
"""
    else:
        # Enhanced forecast prompt with trade intelligence
        prompt = f"""
ROLE: {role} of Elite Quant Trading Firm
TIMEFRAME: {timeframe} trend forecast
CURRENT PRICE: {current_price:.2f}
RSI: {df['RSI'].iloc[-1]:.1f}
NEWS/SENTIMENT: {news_context}

MASTER PLAYBOOK:
{json.dumps(MASTER_PLAYBOOK, indent=2)}

YOUR TASK - Provide ACTIONABLE trade intelligence for your timeframe:
1. Forecast trend direction for next {timeframe}
2. Rate your confidence (0-100%)
3. Identify key Support/Resistance levels on your timeframe chart
4. Suggest optimal Entry/Exit price zones if trading
5. Recommend specific STRATEGY from MASTER_PLAYBOOK (if applicable)
6. Specify RISK_MANAGEMENT approach
7. Provide brief reasoning

OUTPUT FORMAT (STRICT - All fields required):
FORECAST: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]%
STRATEGY: [exact strategy name from playbook or "NONE"]
RISK_RULE: [risk management rule or "NONE"]
RESISTANCE_1: [price level or "NONE"]
RESISTANCE_2: [price level or "NONE"]
SUPPORT_1: [price level or "NONE"]
SUPPORT_2: [price level or "NONE"]
ENTRY_BUY: [ideal buy entry price or "NONE"]
ENTRY_SELL: [ideal sell entry price or "NONE"]
TARGET_TP: [take profit target or "NONE"]
TARGET_SL: [stop loss level or "NONE"]
REASONING: [1-2 sentence analysis]
"""
    
    try:
        resp = client.models.generate_content(model=model_name, contents=prompt)
        text = resp.text.strip()
        
        # Parse response
        if is_position_review:
            vote = "FLAT"
            if "DECISION: HOLD" in text.upper() or "HOLD" in text.upper()[:100]:
                vote = "HOLD"
            elif "DECISION: CLOSE" in text.upper() or "CLOSE" in text.upper()[:100]:
                vote = "CLOSE"
            
            confidence = 0
            conf_match = re.search(r'CONFIDENCE:\s*(\d+)%?', text.upper())
            if conf_match:
                confidence = int(conf_match.group(1))
            
            reasoning = ""
            reason_match = re.search(r'REASONING:\s*(.+)', text, re.IGNORECASE)
            if reason_match:
                reasoning = reason_match.group(1).strip()
            
            return vote, reasoning, confidence, {}  # Empty dict for trade_intel
        
        else:
            # Parse forecast
            vote = "FLAT"
            if "FORECAST: BULLISH" in text.upper():
                vote = "BUY"
            elif "FORECAST: BEARISH" in text.upper():
                vote = "SELL"
            
            # Parse confidence
            confidence = 0
            conf_match = re.search(r'CONFIDENCE:\s*(\d+)%?', text.upper())
            if conf_match:
                confidence = int(conf_match.group(1))
            
            # Parse reasoning
            reasoning = ""
            reason_match = re.search(r'REASONING:\s*(.+)', text, re.IGNORECASE)
            if reason_match:
                reasoning = reason_match.group(1).strip()
            
            # ✅ NEW: Parse trade intelligence
            trade_intel = {
                "strategy": extract_field(text, "STRATEGY"),
                "risk_rule": extract_field(text, "RISK_RULE"),
                "resistance_1": extract_price(text, "RESISTANCE_1"),
                "resistance_2": extract_price(text, "RESISTANCE_2"),
                "support_1": extract_price(text, "SUPPORT_1"),
                "support_2": extract_price(text, "SUPPORT_2"),
                "entry_buy": extract_price(text, "ENTRY_BUY"),
                "entry_sell": extract_price(text, "ENTRY_SELL"),
                "target_tp": extract_price(text, "TARGET_TP"),
                "target_sl": extract_price(text, "TARGET_SL")
            }
            
            return vote, reasoning, confidence, trade_intel
    
    except Exception as e:
        print(f"❌ GEMINI API ERROR ({role}): {e}") 
        return "FLAT", "System Error", 0, {}


def extract_field(text, field_name):
    """Extract text field from agent response"""
    match = re.search(rf'{field_name}:\s*([A-Z_0-9]+)', text.upper())
    return match.group(1) if match and match.group(1) != "NONE" else None

def extract_price(text, field_name):
    """Extract price level from agent response"""
    match = re.search(rf'{field_name}:\s*(\d+\.?\d*)', text.upper())
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None

def update_command_file(df):
    """
    Updates EXISTING command file with agent intelligence
    Preserves all other data in the file
    """
    try:
        current_price = df['Close'].iloc[-1]
        
        # STEP 1: Read existing file (don't overwrite!)
        existing_data = {}
        if os.path.exists(CMD_FILE):
            try:
                with open(CMD_FILE, 'r') as f:
                    existing_data = json.load(f)
            except Exception as e:
                logging.error(f"Cannot read command file: {e}")
                existing_data = {}
        
        # STEP 2: Update only agent sections
        existing_data.update({
            "last_update": str(datetime.datetime.now()),
            "market_status": MISSION_STATE["MARKET_STATUS"],
            "current_price": float(current_price),
            
            "CIO": {
                "timeframe": "30-60 min",
                "forecast": "BULLISH" if MISSION_STATE["CIO_VOTE"] == "BUY" else "BEARISH" if MISSION_STATE["CIO_VOTE"] == "SELL" else "NEUTRAL",
                "confidence": MISSION_STATE.get("CIO_CONFIDENCE", 0),
                "reasoning": MISSION_STATE.get("CIO_REASONING", ""),
                "trade_intel": MISSION_STATE.get("CIO_INTEL", {})
            },
            
            "RISK": {
                "timeframe": "15-30 min",
                "forecast": "BULLISH" if MISSION_STATE["RO_VOTE"] == "BUY" else "BEARISH" if MISSION_STATE["RO_VOTE"] == "SELL" else "NEUTRAL",
                "confidence": MISSION_STATE.get("RISK_CONFIDENCE", 0),
                "reasoning": MISSION_STATE.get("RISK_REASONING", ""),
                "trade_intel": MISSION_STATE.get("RISK_INTEL", {})
            },
            
            "STRAT": {
                "timeframe": "5-15 min",
                "forecast": "BULLISH" if MISSION_STATE["STRAT_VOTE"] == "BUY" else "BEARISH" if MISSION_STATE["STRAT_VOTE"] == "SELL" else "NEUTRAL",
                "confidence": MISSION_STATE.get("STRAT_CONFIDENCE", 0),
                "reasoning": MISSION_STATE.get("STRAT_REASONING", ""),
                "trade_intel": MISSION_STATE.get("STRAT_INTEL", {})
            },
            
            "ML_MODEL": {
                "prediction": "UP" if MISSION_STATE["ML_CONFIDENCE"] > 50 else "DOWN",
                "confidence": MISSION_STATE.get("ML_CONFIDENCE", 0),
                "probability_up": MISSION_STATE.get("ML_CONFIDENCE", 0) / 100.0,
                "last_update": str(datetime.datetime.now())
            },
            
            "BOARD_VOTE": {
                "buy_votes": [MISSION_STATE["CIO_VOTE"], MISSION_STATE["RO_VOTE"], MISSION_STATE["STRAT_VOTE"]].count("BUY"),
                "sell_votes": [MISSION_STATE["CIO_VOTE"], MISSION_STATE["RO_VOTE"], MISSION_STATE["STRAT_VOTE"]].count("SELL"),
                "flat_votes": [MISSION_STATE["CIO_VOTE"], MISSION_STATE["RO_VOTE"], MISSION_STATE["STRAT_VOTE"]].count("FLAT"),
                "consensus": "BUY" if [MISSION_STATE["CIO_VOTE"], MISSION_STATE["RO_VOTE"], MISSION_STATE["STRAT_VOTE"]].count("BUY") >= 2 else "SELL" if [MISSION_STATE["CIO_VOTE"], MISSION_STATE["RO_VOTE"], MISSION_STATE["STRAT_VOTE"]].count("SELL") >= 2 else "FLAT"
            }
        })
        
        # STEP 3: Write merged data back
        with open(CMD_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
            
    except Exception as e:
        logging.error(f"Command File Update Failed: {e}")

# ==========================================
# 🔫 4. THE SNIPER (UPDATED: SIZING + LIMITS + ATR)
# ==========================================
def calculate_atr(df, period=14):
    """Calculate Average True Range for dynamic stops"""
    try:
        df = df.copy()
        df['H-L'] = abs(df['High'] - df['Low'])
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        atr = df['TR'].rolling(window=period).mean().iloc[-1]
        return atr if not pd.isna(atr) else 5.0
    except:
        return 5.0

def execute_trade(action, confidence, reason, df_snapshot):
    """Enhanced version with proper strategy selection and risk management"""
    
    # 🛑 RULE 1: 3-MINUTE COOLDOWN
    if time.time() - MISSION_STATE["LAST_TRADE_TIME"] < 180: 
        return

    try:
        # 1. 🧮 CALCULATE ATR (Dynamic Stops)
        atr_value = calculate_atr(df_snapshot)
        
        # 2. 📋 EXTRACT STRATEGY FROM REASON
        selected_strategy = None
        stop_ticks = None
        tp_ticks = None
        
        # Parse the agent's response for strategy selection
        for category, strategies in MASTER_PLAYBOOK.items():
            if isinstance(strategies, dict):
                for strat_name, strat_info in strategies.items():
                    if strat_name in reason:
                        selected_strategy = strat_name
                        # Get strategy-specific stops if available
                        if isinstance(strat_info, dict):
                            stop_ticks = strat_info.get('stop')
                            tp_ticks = strat_info.get('take_profit')
                        break
        
        # 3. 🎯 DETERMINE STOP LOSS & TAKE PROFIT
        current_price = df_snapshot['Close'].iloc[-1]
        
        if stop_ticks and tp_ticks:
            # Use strategy-specific ticks (e.g., ORB_BREAKOUT: stop=20, tp=40)
            stop_dist = stop_ticks * 0.25  # 0.25 = tick size
            target_dist = tp_ticks * 0.25
            logging.info(f"📋 Using Strategy: {selected_strategy} (SL:{stop_ticks} ticks, TP:{tp_ticks} ticks)")
        else:
            # Fallback to ATR-based stops
            stop_dist = atr_value * 2.0
            target_dist = atr_value * 3.0
            logging.info(f"📊 Using ATR-Based Stops (ATR: {atr_value:.2f})")
        
        sl_price = current_price - stop_dist if action == "BUY" else current_price + stop_dist
        tp_price = current_price + target_dist if action == "BUY" else current_price - target_dist
        
        # Round to nearest 0.25
        sl_price = round(sl_price * 4) / 4
        tp_price = round(tp_price * 4) / 4

        # 4. 🧮 CALCULATE DYNAMIC SIZE
        trade_qty = 1 
        
        if "MNQ" in SYMBOL:
            if confidence >= 0.75: trade_qty = 3
            elif confidence >= 0.50: trade_qty = 2
            else: trade_qty = 1
            max_limit = 3
        else:
            if confidence >= 0.80: trade_qty = 2
            else: trade_qty = 1
            max_limit = 2

        # 5. 🛑 POSITION LIMITS & SIDE CHECK
        current_q = MISSION_STATE["CURRENT_QTY"]
        current_s = MISSION_STATE["CURRENT_SIDE"]

        if current_s != "FLAT" and current_s != action:
             logging.info(f"🚫 SKIPPED: Conflicting Position. Holding {current_s} {current_q}.")
             return

        if (current_q + trade_qty) > max_limit:
             logging.info(f"🚫 SKIPPED: Max Limits ({current_q} + {trade_qty} > {max_limit}).")
             return

        # 6. 🚀 EXECUTE TRADE
        payload = (
            f"key={CT_API_KEY}; command=PLACE; account={ACCOUNT_NAME}; "
            f"instrument={SYMBOL}; action={action}; qty={trade_qty}; "
            f"order_type=MARKET; tif=DAY; stop_loss={sl_price}; take_profit={tp_price};"
        )
        
        logging.info(f"🚀 FIRED {action} x{trade_qty} | Conf: {confidence*100:.1f}%")
        logging.info(f"    🎯 TARGETS: SL {sl_price} | TP {tp_price}")
        if selected_strategy:
            logging.info(f"    📋 STRATEGY: {selected_strategy}")
        
        requests.post(WEBHOOK_URL, data=payload, headers={"Content-Type": "text/plain"}, timeout=2)
        
        # Optimistic Position Update
        if MISSION_STATE["CURRENT_SIDE"] == action:
            MISSION_STATE["CURRENT_QTY"] += trade_qty
        else:
            MISSION_STATE["CURRENT_SIDE"] = action
            MISSION_STATE["CURRENT_QTY"] = trade_qty
        
        logging.info(f"📊 POSITION UPDATE: {MISSION_STATE['CURRENT_SIDE']} x{MISSION_STATE['CURRENT_QTY']}")
            
        MISSION_STATE["LAST_TRADE_TIME"] = time.time()
        save_mission_state()
        save_black_box_data(df_snapshot, action, confidence, reason)

    except Exception as e:
        logging.error(f"❌ FIRE FAIL: {e}")

def force_close_position(reason):
    """ Immediately closes the entire current position """
    qty = MISSION_STATE["CURRENT_QTY"]
    side = MISSION_STATE["CURRENT_SIDE"]
    
    if qty == 0 or side == "FLAT":
        return

    # Determine opposite action to flatten
    action = "SELL" if side == "BUY" else "BUY"
    
    # Payload designed to FLATTEN (Close current quantity)
    # We set SL/TP to 0 or far away because this is an exit order
    payload = (
        f"key={CT_API_KEY}; command=PLACE; account={ACCOUNT_NAME}; "
        f"instrument={SYMBOL}; action={action}; qty={qty}; "
        f"order_type=MARKET; tif=DAY;"
    )

    try:
        requests.post(WEBHOOK_URL, data=payload, headers={"Content-Type": "text/plain"}, timeout=2)
        
        logging.info(f"🚨 MANAGER INTERVENTION: FORCED CLOSE ({side} x{qty}) | Reason: {reason}")
        
        # Reset State immediately
        MISSION_STATE["CURRENT_SIDE"] = "FLAT"
        MISSION_STATE["CURRENT_QTY"] = 0
        MISSION_STATE["LAST_TRADE_TIME"] = time.time() # Add cooldown so we don't re-enter immediately

	save_mission_state()
	logging.info(f"📊 POSITION FLATTENED: {MISSION_STATE['CURRENT_SIDE']} x{MISSION_STATE['CURRENT_QTY']}")
      
    except Exception as e:
        logging.error(f"❌ FORCE CLOSE FAILED: {e}")

def run_sniper_logic(df, quant_prob):
    votes = [MISSION_STATE["CIO_VOTE"], MISSION_STATE["RO_VOTE"], MISSION_STATE["STRAT_VOTE"]]
    buy_votes = votes.count("BUY")
    sell_votes = votes.count("SELL")
    
    # Double check logic with Gemini 2.0 Flash
    sniper_check = get_agent_vote("SNIPER_LOGIC", df, f"Quant Prob: {quant_prob:.2f}", MODEL_AGENTS)
    sniper_vote = sniper_check[0]
    
    action = "FLAT"
    reason = "WAIT"
    
    # Consensus
    if quant_prob > 0.60 and buy_votes >= 2:
        action = "BUY"
        reason = f"Consensus (Quant {quant_prob:.2f} + {buy_votes} Votes)"
    elif quant_prob < 0.40 and sell_votes >= 2:
        action = "SELL"
        reason = f"Consensus (Quant {quant_prob:.2f} + {sell_votes} Votes)"
        
    # Lone Wolf
    if action == "FLAT":
        if quant_prob > 0.75 and sniper_vote == "BUY":
            action = "BUY"
            reason = "Lone Wolf (Quant 75% + Sniper Logic)"
        elif quant_prob < 0.25 and sniper_vote == "SELL":
            action = "SELL"
            reason = "Lone Wolf (Quant 25% + Sniper Logic)"

    if action != "FLAT":
        execute_trade(action, quant_prob, reason, df)
    
    color = "\033[90m"
    if action == "BUY": color = "\033[92m"
    if action == "SELL": color = "\033[91m"
    print(f"   Sniper | Quant: {quant_prob:.0%} | Logic: {sniper_vote} | {color}ACTION: {action}\033[0m")

# ==========================================
# 🔁 5. MAIN COMMANDER LOOP
# ==========================================
def main_loop():
    print("🔵 Initializing V6.0 Commander (Self-Training + Circadian Rhythm)...")
    load_mission_state()	
    load_quant_brain()
    print(f"🟢 LISTENING to {MARKET_DATA}...")
    
    # Initial Briefing
    fmp_data = fetch_fmp_calendar()
    cio_vote, cio_text = get_agent_vote("CIO", pd.DataFrame({'Close':[0], 'RSI':[50]}), fmp_data, MODEL_CIO)
    MISSION_STATE["CIO_VOTE"] = cio_vote
    logging.info(f"   CIO | 10m | {cio_vote} | {cio_text[:100]}...")
    print("---------------------------------------------------------------")

    last_run_minute = -1
    
    while True:
        try:
            # 1. CHECK MARKET HOURS & RISK
            status = check_market_status()
            MISSION_STATE["MARKET_STATUS"] = status
            
            if "DAILY_HALT" in status:
                print(f"\r🛑 {status}: Trading Halted. PnL: ${MISSION_STATE['DAILY_PNL']}", end='')
                time.sleep(60)
                continue
            
            if status == "MAINTENANCE":
                if not MISSION_STATE["TRAINING_COMPLETED_TODAY"]:
                    print("\n🛠️ MARKET CLOSED. INITIATING MAINTENANCE PROTOCOL.")
                    run_auto_training()
                time.sleep(60)
                continue
                
            elif status == "SLEEP":
                print(f"\r💤 AGENTS SLEEPING (Closing Hour). Time: {datetime.datetime.now().strftime('%H:%M')}", end='')
                time.sleep(60)
                continue
            
            # Reset Training Flag if Market is Open
            if status == "OPEN":
                MISSION_STATE["TRAINING_COMPLETED_TODAY"] = False

           # 2. RUN AGENTS (Only if OPEN)
            if os.path.exists(MARKET_DATA):
                try:
                    with open(MARKET_DATA, "r") as f: q = collections.deque(f, 200)
                    df = pd.read_csv(io.StringIO(''.join(q)), header=None)
                    
                    # ✅ FIX: Force keep only the first 6 columns
                    if len(df.columns) >= 6:
                        df = df.iloc[:, :6] 
                        df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
                        
                        # Convert Date
                        df['Date'] = pd.to_datetime(df['Date'])
                        
                        # Calculate Indicators
                        df['Ret'] = df['Close'].pct_change()
                        delta = df['Close'].diff()
                        df['RSI'] = 100 - (100 / (1 + (delta.where(delta>0,0).rolling(14).mean()/(-delta.where(delta<0,0).rolling(14).mean()))))
                        
                        now = datetime.datetime.now()
                        current_price = df['Close'].iloc[-1]
                        
                        # ---------------------------------------------------------
                        # 👮 CIO ENGINE (10m Loop + Position Check)
                        # ---------------------------------------------------------
                        if now.minute % 10 == 0 and now.minute != last_run_minute:
                            news = fetch_fmp_calendar()
                            
                            # A. Standard Market Vote
                            vote, reasoning, confidence, trade_intel = get_agent_vote("CIO", df, news, SMART_MODEL)
			    MISSION_STATE["CIO_VOTE"] = vote
			    MISSION_STATE["CIO_REASONING"] = reasoning
			    MISSION_STATE["CIO_CONFIDENCE"] = confidence
			    MISSION_STATE["CIO_INTEL"] = trade_intel
    
			    forecast = "BULLISH" if vote == "BUY" else "BEARISH" if vote == "SELL" else "NEUTRAL"
			    logging.info(f"[CIO] Forecast: {forecast} ({confidence}%) | Reasoning: {reasoning[:80]}")

                            # B. Position Management (Checks ALL trades every 10 mins)
                            if MISSION_STATE["CURRENT_QTY"] > 0:
                                pos_prompt = f"MANAGEMENT: We are {MISSION_STATE['CURRENT_SIDE']} {MISSION_STATE['CURRENT_QTY']} contracts. Current Price: {current_price}. MARKET NEWS: {news}. DECISION: HOLD or CLOSE? Explain Why."
                                m_vote, m_reasoning, m_conf, m_intel = get_agent_vote("CIO_MANAGER", df, pos_prompt, SMART_MODEL)
			        decision = "HOLD" if m_vote == "HOLD" else "CLOSE"
				logging.info(f"[CIO] Position: {decision} ({m_conf}%). Reason: {m_reasoning[:80]}")

                                # 🛠️ FIX: ACTUALLY CLOSE THE TRADE
                                if "CLOSE" in m_vote or "FLAT" in m_vote:
                                    force_close_position(f"CIO Request: {m_text[:50]}")
                                    
                            print("---------------------------------------------------------------")
                        
                        # ---------------------------------------------------------
                        # 🛡️ RISK ENGINE (3m Loop + Position Check)
                        # ---------------------------------------------------------
                        if now.minute % 3 == 0 and now.minute != last_run_minute:
                            news = fetch_finnhub_sentiment()
                            
                            # A. Standard Market Vote
                            vote, reasoning, confidence, trade_intel = get_agent_vote("RISK", df, news, SMART_MODEL)
			    MISSION_STATE["RO_VOTE"] = vote
			    MISSION_STATE["RISK_REASONING"] = reasoning
			    MISSION_STATE["RISK_CONFIDENCE"] = confidence
			    MISSION_STATE["RISK_INTEL"] = trade_intel
    
			    forecast = "BULLISH" if vote == "BUY" else "BEARISH" if vote == "SELL" else "NEUTRAL"
			    logging.info(f"[RISK] Forecast: {forecast} ({confidence}%) | Reasoning: {reasoning[:80]}")

                            # B. Position Management (Checks ALL trades every 3 mins)
                            if MISSION_STATE["CURRENT_QTY"] > 0:
                                pos_prompt = f"RISK AUDIT: We are {MISSION_STATE['CURRENT_SIDE']} {MISSION_STATE['CURRENT_QTY']} contracts. Volatility is High. DECISION: HOLD or CLOSE?"
                                m_vote, m_reasoning, m_conf, m_intel = get_agent_vote("RISK_MANAGER", df, pos_prompt, SMART_MODEL)
				decision = "HOLD" if m_vote == "HOLD" else "CLOSE"
				logging.info(f"[RISK] Position: {decision} ({m_conf}%). Reason: {m_reasoning[:80]}")

                                # 🛠️ FIX: ACTUALLY CLOSE THE TRADE
                                if "CLOSE" in m_vote or "FLAT" in m_vote:
                                    force_close_position(f"Risk Officer Request: {m_text[:50]}")
                                    
                            print("---------------------------------------------------------------")

                        # ---------------------------------------------------------
                        # ♟️ STRAT ENGINE (1m Loop)
                        # ---------------------------------------------------------
                        if now.minute != last_run_minute:
                            last_run_minute = now.minute # Update Timer
                            
                            # A. Standard 1m Analysis
                            news = f"Sentiment {MISSION_STATE['SENTIMENT_SCORE']}"
                            vote, reasoning, confidence, trade_intel = get_agent_vote("STRAT", df, news, FAST_MODEL)  # ✅ Note: FAST_MODEL
			    MISSION_STATE["STRAT_VOTE"] = vote
			    MISSION_STATE["STRAT_REASONING"] = reasoning
			    MISSION_STATE["STRAT_CONFIDENCE"] = confidence
			    MISSION_STATE["STRAT_INTEL"] = trade_intel
    
			    forecast = "BULLISH" if vote == "BUY" else "BEARISH" if vote == "SELL" else "NEUTRAL"
			    logging.info(f"[STRAT] Forecast: {forecast} ({confidence}%) | Reasoning: {reasoning[:80]}")

                            update_command_file(df)
                            
			    print("---------------------------------------------------------------")

                        # SNIPER (15s)
                        quant_prob = get_quant_signal(df)
                        run_sniper_logic(df, quant_prob)
                
                except Exception as e:
                    logging.error(f"Loop Data Error: {e}")
            
            time.sleep(15)
            
        except KeyboardInterrupt: break
        except Exception as e: 
            logging.error(f"Loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main_loop()