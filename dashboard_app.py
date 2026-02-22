import streamlit as st
import pandas as pd
import os
import json
import time
import datetime
import random
import subprocess 

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Quant Firm V7.2",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. FILE & DATA SETTINGS
# ---------------------------------------------------------
LOG_FILE = "trading_log.txt"

def create_mock_data_if_missing():
    """Ensures log file exists so the dashboard is never empty."""
    if not os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now()} - Commander - [SYSTEM] Gemini 2.0 Flash Online\n")
        except Exception as e:
            st.error(f"Error creating mock data: {e}")

# Initialize Data
create_mock_data_if_missing()

# ---------------------------------------------------------
# 3. CUSTOM CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Dark Theme Adjustments */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #1a1c24;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 8px;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1c24;
        border-radius: 4px 4px 0 0;
        padding: 10px 20px;
        color: #aaa;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0e1117;
        border-top: 2px solid #00FF00;
        color: #fff;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. HELPER FUNCTIONS
# ---------------------------------------------------------
def render_trade_card(data):
    """Renders the HTML card for a single trade."""
    action = data.get('action', 'WAIT').upper()
    
    if action == "BUY":
        border = "#00FF00"; bg = "rgba(0, 255, 0, 0.05)"; icon = "🟢"
    elif action == "SELL":
        border = "#FF4B4B"; bg = "rgba(255, 75, 75, 0.05)"; icon = "🔴"
    else:
        border = "#666"; bg = "rgba(255, 255, 255, 0.05)"; icon = "⚪"

    html = f"""
    <div style="border-left: 4px solid {border}; background-color: {bg}; padding: 12px; margin-bottom: 10px; border-radius: 4px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:1.1em; color:#fff;">{icon} {action} {data.get('symbol')}</strong>
            <span style="font-family:monospace; color:#888;">{data.get('timestamp')}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:8px; font-family:monospace; color:#ddd;">
            <span>Price: ${data.get('price')}</span>
            <span>Conf: {data.get('confidence')}%</span>
        </div>
        <hr style="border-color:#333; margin:8px 0;">
        <div style="font-size:0.9em; color:#ccc;">
            <div>🛡️ SL: ${data.get('sl_price')}</div>
            <div>🎯 TP: ${data.get('tp_price')}</div>
            <div style="margin-top:5px; font-style:italic; color:#888;">"{data.get('reason')}"</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. MAIN DASHBOARD LAYOUT
# ---------------------------------------------------------
st.title("🏦 Quant Firm V7.2")

# Top Menu Tabs
tab_live, tab_reports, tab_health = st.tabs(["🖥️ LIVE TERMINAL", "📑 CIO REPORTS", "⚙️ SYSTEM HEALTH"])

# === TAB 1: LIVE TERMINAL ===
with tab_live:
    # A. Top Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("DEFCON Level", "🟢 GOD MODE", "Aggressive")
    m2.metric("Market Sentiment", "Bullish", "+0.45%")
    m3.metric("Daily P&L", "$2,450.00", "+3.1%")
    m4.metric("Latency", "24ms", "-2ms")
    
    st.markdown("---")
    
    # B. Capital Allocation
    st.subheader("💰 Capital Allocation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("APEX-001", "$51,200", "+$1.2k")
    c2.metric("APEX-002", "$49,800", "-$200")
    c3.metric("TOPSTEP", "$102,500", "+$2.5k")
    c4.metric("PERSONAL", "$25,400", "+$400")
    
    st.markdown("---")
    
    # C. Analytics Engine
    st.subheader("📊 Analytics Engine")
    
    trades = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "TRADE_EVENT_JSON:::" in line:
                    try:
                        json_part = line.split("TRADE_EVENT_JSON:::")[1].strip()
                        trades.append(json.loads(json_part))
                    except: pass
    
    if trades:
        df = pd.DataFrame(trades)
        a1, a2, a3, a4 = st.columns(4)
        total = len(df)
        buy_ratio = int(len(df[df['action']=='BUY'])/total*100) if total > 0 else 0
        avg_conf = int(df['confidence'].astype(float).mean()) if total > 0 else 0
        
        a1.metric("Total Trades", total)
        a2.metric("Buy Ratio", f"{buy_ratio}%")
        a3.metric("Avg Conf", f"{avg_conf}%")
        a4.metric("Top Strat", df['atm_used'].mode()[0] if 'atm_used' in df.columns else "N/A")
        
        # Charts
        col_chart, col_msg = st.columns([3, 1])
        with col_chart:
            if 'atm_used' in df.columns:
                st.bar_chart(df['atm_used'].value_counts(), color="#2E86C1")
        with col_msg:
            st.info("**CIO Directive:**\nHigh confidence in Runners detected. Maintain Aggressive allocation.")
    else:
        st.warning("Waiting for trade data...")
    
    st.markdown("---")

    # D. Live Feed & Boardroom
    col_feed, col_chat = st.columns([1.8, 1])
    
    with col_feed:
        st.subheader("📡 Live Neural Feed")
        with st.container(height=600):
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()[::-1]
                    for line in lines:
                        if "TRADE_EVENT_JSON:::" in line:
                            try:
                                json_part = line.split("TRADE_EVENT_JSON:::")[1].strip()
                                render_trade_card(json.loads(json_part))
                            except: pass
                        else:
                            st.caption(line.strip().replace(" - Commander - ", " | "))
    
    with col_chat:
        st.subheader("🏛️ Boardroom")
        agent = st.selectbox("Channel", ["Sniper", "Strategist", "Risk Officer", "CIO"])
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
            
        with st.container(height=450):
            for msg in st.session_state.chat_history:
                st.markdown(msg, unsafe_allow_html=True)
                
        user_input = st.chat_input(f"Message {agent}...")
        if user_input:
            st.session_state.chat_history.append(f"<div style='text-align:right; color:#4CAF50;'><b>You:</b> {user_input}</div>")
            st.session_state.chat_history.append(f"<div style='text-align:left; color:#aaa;'><b>{agent}:</b> Copy that. Analyzing '{user_input}'...</div>")
            st.rerun()

# === TAB 2: CIO REPORTS (UPDATED) ===
with tab_reports:
    st.header("📑 CIO Optimization Reports")
    st.caption("Reports generated during market downtime.")
    
    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        if st.button("Generate Today's Report"):
            with st.spinner("CIO is Analyzing Market Data..."):
                try:
                    # Run the script and capture output
                    result = subprocess.run(["python", "performance_engine.py"], capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success("Report Generated Successfully!")
                        time.sleep(1) # Give file system a moment
                        st.rerun()
                    else:
                        st.error(f"Error: {result.stderr}")
                except Exception as e:
                    st.error(f"Execution Failed: {e}")
    
    files = [f for f in os.listdir(".") if f.endswith(".txt") and "Report" in f]
    # Sort files by date (newest first)
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    if files:
        sel = st.selectbox("Select Report", files)
        with open(sel, "r", encoding="utf-8") as f: 
            st.text_area("Content", f.read(), height=600)
    else:
        st.info("No reports found.")

# === TAB 3: SYSTEM HEALTH (UPDATED) ===
with tab_health:
    st.header("⚙️ System Diagnostics")
    
    # Check if today's CIO report exists
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cio_status = "PENDING (Waiting for Run)"
    cio_color = "warning" # Yellow
    
    # Check logic: Look for any file with today's date AND 'Report' in the name
    if any(today_str in f and "Report" in f for f in os.listdir(".")):
        cio_status = "OPTIMIZATION COMPLETE"
        cio_color = "success" # Green
    
    h1, h2, h3 = st.columns(3)
    h1.success("Sniper: ONLINE (60s)")
    h2.success("Risk: ONLINE (Monitoring)")
    
    # DYNAMIC CIO STATUS
    if cio_color == "success":
        h3.success(f"CIO: {cio_status}")
    else:
        h3.warning(f"CIO: {cio_status}")
    
    st.markdown("### Error Log")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            errs = [l for l in f if "ERROR" in l]
        if errs: st.error(f"{len(errs)} Errors Detected"); st.write(errs)
        else: st.success("System Healthy. No errors in current log.")