import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import random
import base64
import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def analyze_with_gemini(file_bytes, mime_type):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        return '{"error": "Please insert your Gemini API Key in the app.py code."}'
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    
    payload = {
        "contents": [{
            "parts": [
                {"text": "Analyze this media for unauthorized use, brand anomalies, copyright infringement, or deepfakes. Provide a concise JSON response with keys: 'violations_found' (int), 'confidence_score' (string), 'details' (string), and 'threat_level' (CRITICAL, HIGH, MEDIUM, LOW)."},
                {"inline_data": {
                    "mime_type": mime_type,
                    "data": b64_data
                }}
            ]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        res_json = response.json()
        text_resp = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return text_resp
    except Exception as e:
        return json.dumps({"error": str(e), "details": response.text if 'response' in locals() else ""})

def run_playwright_search():
    import subprocess, sys, os
    
    crawler_path = os.path.join(os.path.dirname(__file__), "crawler.py")
    
    try:
        result = subprocess.run(
            [sys.executable, crawler_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown subprocess error."
            return [{"error": error_msg}]
        
        output = result.stdout.strip()
        if not output:
            return [{"error": "Crawler returned no output. The browser may have been blocked."}]
        
        return json.loads(output)
        
    except subprocess.TimeoutExpired:
        return [{"error": "Crawler timed out after 120 seconds."}]
    except Exception as e:
        return [{"error": str(e)}]

def analyze_links_with_gemini(scraped_data):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        return '{"error": "Please insert your Gemini API Key in the app.py code."}'
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    You are a cybersecurity threat intelligence analyst for SportsGuardian AI. 
    Review the following scraped search results regarding live sports streaming:
    {json.dumps(scraped_data, indent=2)}
    
    Identify which links appear to be highly suspicious, illegal piracy sites, or unauthorized streaming domains.
    Provide a brief JSON response evaluating the threats. Ensure your response is purely valid JSON without markdown formatting.
    Format:
    {{
      "total_analyzed": 5,
      "high_risk_threats": [
        {{"url": "example.com", "reason": "Offers free unauthorized live streams"}}
      ],
      "summary": "Brief summary of the threat landscape found."
    }}
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except Exception as e:
        return json.dumps({"error": str(e)})

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SportsGuardian AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── GLOBAL STYLES ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Barlow+Condensed:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

/* ── Root Variables ── */
:root {
    --bg-deep:    #050911;
    --bg-panel:   #0a1020;
    --bg-card:    #0d1628;
    --border:     rgba(0,200,255,0.15);
    --cyan:       #00c8ff;
    --orange:     #ff6b2b;
    --green:      #00ff88;
    --red:        #ff2b5e;
    --yellow:     #ffd600;
    --text-main:  #e8f4ff;
    --text-dim:   #5a7a9a;
    --glow-cyan:  0 0 20px rgba(0,200,255,0.4);
    --glow-orange:0 0 20px rgba(255,107,43,0.5);
}

/* ── Base ── */
.stApp { background: var(--bg-deep) !important; font-family: 'Barlow Condensed', sans-serif; }
html, body, [class*="css"] { background: var(--bg-deep) !important; color: var(--text-main) !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 2rem !important; max-width: 100% !important; }
.stDeployButton { display: none; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--bg-panel) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { color: var(--text-main) !important; }

/* ── Custom scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--cyan); border-radius: 2px; }

/* ── Header Bar ── */
.top-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.75rem 1.5rem;
    background: linear-gradient(90deg, rgba(0,200,255,0.08), transparent 60%);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin-bottom: 1rem;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-icon { font-size: 2rem; filter: drop-shadow(0 0 8px var(--cyan)); }
.brand-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.6rem; font-weight: 700;
    color: var(--text-main); letter-spacing: 3px; text-transform: uppercase;
}
.brand-sub { font-family: 'Share Tech Mono', monospace; font-size: 0.65rem; color: var(--cyan); letter-spacing: 4px; }
.header-status {
    display: flex; gap: 1.5rem; align-items: center;
}
.status-pill {
    font-family: 'Share Tech Mono', monospace; font-size: 0.7rem;
    padding: 4px 12px; border-radius: 2px; letter-spacing: 2px;
}
.status-live { background: rgba(0,255,136,0.1); border: 1px solid var(--green); color: var(--green); }
.status-time { background: rgba(0,200,255,0.1); border: 1px solid var(--cyan); color: var(--cyan); }
.pulse { animation: pulse 2s infinite; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--green); margin-right: 6px; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(1.3)} }

/* ── Metric Cards ── */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem; }
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px; padding: 1rem 1.25rem;
    position: relative; overflow: hidden;
    transition: transform 0.2s;
}
.metric-card::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
}
.metric-card.cyan::before  { background: var(--cyan); box-shadow: var(--glow-cyan); }
.metric-card.orange::before { background: var(--orange); box-shadow: var(--glow-orange); }
.metric-card.green::before  { background: var(--green); }
.metric-card.red::before    { background: var(--red); }
.metric-card:hover { transform: translateY(-2px); }
.metric-label { font-family: 'Share Tech Mono', monospace; font-size: 0.65rem; color: var(--text-dim); letter-spacing: 3px; margin-bottom: 4px; }
.metric-value { font-family: 'Rajdhani', sans-serif; font-size: 2.2rem; font-weight: 700; line-height: 1; }
.metric-value.cyan  { color: var(--cyan); text-shadow: var(--glow-cyan); }
.metric-value.orange { color: var(--orange); text-shadow: var(--glow-orange); }
.metric-value.green  { color: var(--green); }
.metric-value.red    { color: var(--red); }
.metric-delta { font-size: 0.75rem; margin-top: 4px; color: var(--text-dim); }
.metric-delta .up   { color: var(--green); }
.metric-delta .down { color: var(--red); }

/* ── Panel ── */
.panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px; padding: 1.25rem;
    margin-bottom: 1rem; height: 100%;
}
.panel-title {
    font-family: 'Rajdhani', sans-serif; font-weight: 700;
    font-size: 0.8rem; letter-spacing: 4px; text-transform: uppercase;
    color: var(--cyan); margin-bottom: 1rem;
    padding-bottom: 0.5rem; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
}

/* ── Threat Table ── */
.threat-row {
    display: flex; align-items: center; gap: 10px;
    padding: 0.6rem 0; border-bottom: 1px solid rgba(0,200,255,0.07);
    font-size: 0.82rem;
}
.threat-row:last-child { border-bottom: none; }
.threat-badge {
    font-family: 'Share Tech Mono', monospace; font-size: 0.62rem;
    padding: 2px 8px; border-radius: 2px; white-space: nowrap; letter-spacing: 1px;
}
.badge-critical { background: rgba(255,43,94,0.2); border: 1px solid var(--red); color: var(--red); }
.badge-high     { background: rgba(255,107,43,0.2); border: 1px solid var(--orange); color: var(--orange); }
.badge-medium   { background: rgba(255,214,0,0.15); border: 1px solid var(--yellow); color: var(--yellow); }
.badge-resolved { background: rgba(0,255,136,0.1); border: 1px solid var(--green); color: var(--green); }
.threat-platform { color: var(--text-dim); font-size: 0.75rem; min-width: 60px; }
.threat-action {
    margin-left: auto;
    font-family: 'Share Tech Mono', monospace; font-size: 0.6rem;
    padding: 2px 10px; border-radius: 2px; cursor: pointer; letter-spacing: 1px;
    background: rgba(0,200,255,0.1); border: 1px solid var(--cyan); color: var(--cyan);
}

/* ── Upload Zone ── */
.upload-zone {
    border: 2px dashed rgba(0,200,255,0.3);
    border-radius: 6px; padding: 2.5rem;
    text-align: center; background: rgba(0,200,255,0.03);
    transition: all 0.3s;
}
.upload-zone:hover { border-color: var(--cyan); background: rgba(0,200,255,0.06); }
.upload-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.upload-title { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-weight: 600; letter-spacing: 2px; }
.upload-sub { font-size: 0.75rem; color: var(--text-dim); margin-top: 4px; }

/* ── Scan Progress ── */
.scan-step {
    display: flex; align-items: center; gap: 10px;
    padding: 0.5rem 0; font-size: 0.82rem;
}
.scan-step-icon { font-size: 1rem; min-width: 20px; text-align: center; }
.scan-step-label { flex: 1; }
.scan-step-status { font-family: 'Share Tech Mono', monospace; font-size: 0.65rem; }
.scan-done   { color: var(--green); }
.scan-active { color: var(--cyan); animation: blink 1s infinite; }
.scan-wait   { color: var(--text-dim); }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Platform Grid ── */
.platform-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; }
.platform-tile {
    background: rgba(0,200,255,0.04);
    border: 1px solid var(--border);
    border-radius: 4px; padding: 0.7rem;
    display: flex; align-items: center; gap: 8px;
    font-size: 0.8rem;
}
.platform-name { font-weight: 600; }
.platform-count { margin-left: auto; font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; color: var(--orange); }

/* ── Buttons ── */
.stButton > button {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important; letter-spacing: 3px !important;
    text-transform: uppercase !important; border-radius: 3px !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--cyan), #0088ff) !important;
    color: var(--bg-deep) !important; border: none !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: var(--glow-cyan) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-panel) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important; letter-spacing: 3px !important;
    text-transform: uppercase !important; font-size: 0.78rem !important;
    color: var(--text-dim) !important;
    background: transparent !important; border: none !important;
    padding: 0.5rem 1.2rem !important;
}
.stTabs [aria-selected="true"] {
    color: var(--cyan) !important; border-bottom: 2px solid var(--cyan) !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent !important; }

/* ── Selectbox / Input ── */
.stSelectbox > div > div, .stTextInput > div > div {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-main) !important;
    border-radius: 3px !important;
}

/* ── Alert Feed ── */
.alert-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 0.6rem; margin-bottom: 0.4rem;
    border-radius: 3px; font-size: 0.8rem;
    border-left: 3px solid;
    animation: slideIn 0.3s ease;
}
@keyframes slideIn { from{transform:translateX(-10px);opacity:0} to{transform:translateX(0);opacity:1} }
.alert-critical { background: rgba(255,43,94,0.08); border-color: var(--red); }
.alert-high     { background: rgba(255,107,43,0.08); border-color: var(--orange); }
.alert-medium   { background: rgba(255,214,0,0.06);  border-color: var(--yellow); }
.alert-time { font-family: 'Share Tech Mono', monospace; font-size: 0.62rem; color: var(--text-dim); margin-top: 2px; }
.alert-msg  { font-weight: 500; }

/* ── Watermark Visual ── */
.wm-visual {
    background: linear-gradient(135deg, #0a1628, #0d1f3c);
    border: 1px solid var(--border); border-radius: 4px;
    padding: 1.5rem; text-align: center; position: relative; overflow: hidden;
}
.wm-visual::after {
    content: 'GUARDIAN PROTECTED';
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%,-50%) rotate(-30deg);
    font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700;
    color: rgba(0,200,255,0.06); letter-spacing: 8px; white-space: nowrap;
    pointer-events: none;
}

/* ── Hash Display ── */
.hash-display {
    font-family: 'Share Tech Mono', monospace; font-size: 0.7rem;
    color: var(--green); background: rgba(0,255,136,0.05);
    border: 1px solid rgba(0,255,136,0.2); border-radius: 3px;
    padding: 0.5rem; word-break: break-all; letter-spacing: 1px;
}

/* ── Score Ring ── */
.score-ring-wrap { text-align: center; padding: 0.5rem; }
.score-label { font-family: 'Share Tech Mono', monospace; font-size: 0.65rem; color: var(--text-dim); letter-spacing: 3px; margin-top: 4px; }

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Sidebar Nav ── */
.nav-item {
    padding: 0.5rem 0.75rem; border-radius: 3px; cursor: pointer;
    font-family: 'Rajdhani', sans-serif; font-weight: 600;
    font-size: 0.85rem; letter-spacing: 2px; text-transform: uppercase;
    display: flex; align-items: center; gap: 8px;
    transition: all 0.2s; margin-bottom: 3px;
}
.nav-item:hover, .nav-item.active {
    background: rgba(0,200,255,0.1); color: var(--cyan) !important;
    border-left: 2px solid var(--cyan);
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ───────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "scan_running" not in st.session_state:
    st.session_state.scan_running = False
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "scan_done" not in st.session_state:
    st.session_state.scan_done = False

# ─── MOCK DATA ───────────────────────────────────────────────────────────────────
THREATS = [
    {"id":"TH-4421","title":"Champions League Final Highlights Repost","platform":"TikTok","severity":"critical","time":"2m ago","match":"99.2%","action":"FLAG"},
    {"id":"TH-4420","title":"NBA Playoffs Game 7 Clip – Unauthorized","platform":"YouTube","severity":"high","time":"8m ago","match":"96.7%","action":"FLAG"},
    {"id":"TH-4419","title":"NFL Logo Removed – Branded Repost","platform":"Instagram","severity":"high","time":"14m ago","match":"91.3%","action":"REVIEW"},
    {"id":"TH-4418","title":"Deepfake Player Promo Content","platform":"X (Twitter)","severity":"critical","time":"31m ago","match":"87.5%","action":"TAKEDOWN"},
    {"id":"TH-4417","title":"F1 Race Replay – Watermark Stripped","platform":"Telegram","severity":"medium","time":"45m ago","match":"82.1%","action":"REVIEW"},
    {"id":"TH-4416","title":"EPL Match Broadcast Fragment","platform":"Reddit","severity":"medium","time":"1h ago","match":"78.4%","action":"REVIEW"},
    {"id":"TH-4415","title":"NIL Athlete Image Misuse","platform":"Facebook","severity":"high","time":"2h ago","match":"94.0%","action":"FLAG"},
    {"id":"TH-4414","title":"Cricket World Cup Goal Replay","platform":"TikTok","severity":"resolved","time":"3h ago","match":"88.9%","action":"DONE"},
]

PLATFORMS = [
    ("🎵","TikTok","1,284"),("▶️","YouTube","967"),("📸","Instagram","731"),
    ("🐦","X / Twitter","512"),("📘","Facebook","438"),("💬","Telegram","291"),
]

ALERTS_LIVE = [
    ("critical","TH-4421","New deepfake athlete promo detected — Champions League Final","30s ago"),
    ("high","TH-4420","Unauthorized NBA clip circulating — 2.1M views","2m ago"),
    ("high","SYS-001","Gemini Vision flagged logo-removed clip — NFL Game","5m ago"),
    ("medium","TH-4419","Possible watermark strip attempt on F1 content","11m ago"),
    ("medium","SYS-002","Scheduled scan completed — 4,221 assets checked","18m ago"),
]

GEO_DATA = {
    "lat":[40.7,-33.9,51.5,48.9,35.7,19.1,-23.5,55.8,1.3,25.2],
    "lon":[-74.0,151.2,-0.1,2.35,139.7,72.9,-46.6,37.6,103.8,55.3],
    "city":["New York","Sydney","London","Paris","Tokyo","Mumbai","São Paulo","Moscow","Singapore","Dubai"],
    "count":[342,128,287,201,156,98,174,89,112,143],
    "severity":["critical","medium","high","medium","high","medium","high","low","medium","high"]
}

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:1rem 0.5rem 1.5rem'>
        <div style='font-family:Rajdhani,sans-serif;font-size:1.2rem;font-weight:700;
                    letter-spacing:3px;color:#00c8ff;'>⚡ SPORTSGUARDIAN</div>
        <div style='font-family:Share Tech Mono,monospace;font-size:0.6rem;
                    color:#5a7a9a;letter-spacing:3px;'>AI PROTECTION SUITE v2.4</div>
    </div>
    """, unsafe_allow_html=True)

    pages = [
        ("📊","Dashboard","dashboard"),
        ("🔍","Scan & Detect","scan"),
        ("🗺️","Infringement Map","map"),
        ("📡","Alert Feed","alerts"),
        ("🔐","Watermarking","watermark"),
        ("📈","Analytics","analytics"),
        ("⚙️","Settings","settings"),
        ("🌐","Auto Browser","auto_browser"),
    ]
    for icon, label, key in pages:
        active = "active" if st.session_state.page == key else ""
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style='font-family:Share Tech Mono,monospace;font-size:0.62rem;color:#5a7a9a;
                padding:0 0.5rem;line-height:1.8;'>
        ORG: <span style='color:#00c8ff'>NFL OFFICIAL</span><br>
        TIER: <span style='color:#ffd600'>ENTERPRISE</span><br>
        ASSETS: <span style='color:#00ff88'>12,441 PROTECTED</span><br>
        SCANS TODAY: <span style='color:#00c8ff'>4,221</span>
    </div>
    """, unsafe_allow_html=True)

# ─── HEADER ──────────────────────────────────────────────────────────────────────
now = datetime.now().strftime("%H:%M:%S UTC")
st.markdown(f"""
<div class='top-header'>
    <div class='brand'>
        <span class='brand-icon'>🛡️</span>
        <div>
            <div class='brand-title'>SportsGuardian AI</div>
            <div class='brand-sub'>Digital Media Protection Platform</div>
        </div>
    </div>
    <div class='header-status'>
        <span class='status-pill status-live'><span class='pulse'></span>SCANNING LIVE</span>
        <span class='status-pill status-time'>⏱ {now}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dashboard":
    # Metric Cards
    st.markdown("""
    <div class='metric-grid'>
        <div class='metric-card cyan'>
            <div class='metric-label'>THREATS DETECTED (24H)</div>
            <div class='metric-value cyan'>1,284</div>
            <div class='metric-delta'><span class='up'>▲ 18%</span> vs yesterday</div>
        </div>
        <div class='metric-card red'>
            <div class='metric-label'>CRITICAL VIOLATIONS</div>
            <div class='metric-value red'>47</div>
            <div class='metric-delta'><span class='down'>▲ 5</span> new this hour</div>
        </div>
        <div class='metric-card green'>
            <div class='metric-label'>TAKEDOWNS ISSUED</div>
            <div class='metric-value green'>892</div>
            <div class='metric-delta'><span class='up'>▲ 23%</span> faster than manual</div>
        </div>
        <div class='metric-card orange'>
            <div class='metric-label'>REVENUE PROTECTED ($)</div>
            <div class='metric-value orange'>$2.4M</div>
            <div class='metric-delta'><span class='up'>▲ 30%</span> recovery rate</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📡  Live Threat Feed</div>", unsafe_allow_html=True)
        for t in THREATS[:6]:
            badge_cls = f"badge-{t['severity']}"
            st.markdown(f"""
            <div class='threat-row'>
                <span class='threat-badge {badge_cls}'>{t['severity'].upper()}</span>
                <span style='flex:1;'>{t['title']}</span>
                <span class='threat-platform'>{t['platform']}</span>
                <span style='font-family:Share Tech Mono;font-size:0.65rem;color:#5a7a9a;'>{t['match']}</span>
                <span style='font-family:Share Tech Mono;font-size:0.65rem;color:#5a7a9a;'>{t['time']}</span>
                <span class='threat-action'>{t['action']}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📊  Platform Distribution</div>", unsafe_allow_html=True)

        # Donut chart
        labels = ["TikTok", "YouTube", "Instagram", "X/Twitter", "Facebook", "Telegram"]
        values = [1284, 967, 731, 512, 438, 291]
        colors = ["#00c8ff","#ff6b2b","#ff2b5e","#ffd600","#00ff88","#a855f7"]
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.65,
            marker=dict(colors=colors, line=dict(color="#050911", width=2)),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value} detections<extra></extra>"
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10,b=10,l=10,r=10), height=200,
            legend=dict(font=dict(color="#e8f4ff", size=10), bgcolor="rgba(0,0,0,0)"),
            annotations=[dict(text="<b>4,223</b>", x=0.5, y=0.5, font_size=20,
                              font_color="#00c8ff", showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # Threat Timeline
    col3, col4 = st.columns([2,1])
    with col3:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📈  Detection Timeline (7 days)</div>", unsafe_allow_html=True)
        dates = [(datetime.now() - timedelta(days=i)).strftime("%b %d") for i in range(6,-1,-1)]
        tiktok = [820,940,1100,980,1230,1050,1284]
        youtube = [620,700,780,650,890,820,967]
        insta   = [450,510,590,480,680,600,731]
        fig2 = go.Figure()
        for name, vals, col in [("TikTok",tiktok,"#00c8ff"),("YouTube",youtube,"#ff6b2b"),("Instagram",insta,"#ff2b5e")]:
            fig2.add_trace(go.Scatter(
                x=dates, y=vals, name=name, mode="lines+markers",
                line=dict(color=col, width=2),
                marker=dict(size=5, color=col),
                fill="tonexty" if name != "TikTok" else "none",
                fillcolor=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},0.05)"
            ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10,b=10,l=10,r=10), height=200,
            xaxis=dict(showgrid=False, color="#5a7a9a", tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,200,255,0.07)", color="#5a7a9a"),
            legend=dict(font=dict(color="#e8f4ff", size=10), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🏅  Top Offending Platforms</div>", unsafe_allow_html=True)
        for icon, name, count in PLATFORMS:
            st.markdown(f"""
            <div class='platform-tile'>
                <span style='font-size:1.1rem'>{icon}</span>
                <span class='platform-name'>{name}</span>
                <span class='platform-count'>{count}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SCAN & DETECT PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "scan":
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🔍  Upload & Scan Asset</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class='upload-zone'>
            <div class='upload-icon'>📤</div>
            <div class='upload-title'>DROP MEDIA FILE HERE</div>
            <div class='upload-sub'>MP4, MOV, AVI, JPG, PNG — Max 500MB</div>
        </div>""", unsafe_allow_html=True)

        uploaded = st.file_uploader("", type=["mp4","mov","avi","jpg","png","jpeg"],
                                     label_visibility="collapsed")

        col_a, col_b = st.columns(2)
        with col_a:
            scan_depth = st.selectbox("Scan Depth", ["Quick (2 FPS)","Standard (4 FPS)","Deep (8 FPS)"])
        with col_b:
            platforms_sel = st.multiselect("Target Platforms", ["TikTok","YouTube","Instagram","X/Twitter","Facebook","All"], default=["All"])

        st.markdown("---")
        
        run_scan = st.button("⚡ RUN AI SCAN", use_container_width=True)
        
        if run_scan:
            if uploaded is None:
                st.error("Please upload a media file first.")
            else:
                import streamlit.components.v1 as components
                with open(r"D:\Hackathon\stream\gemini_ultra_scan_prev_fixed (1).html", "r", encoding="utf-8") as f:
                    html_data = f.read()
                
                # Make background transparent
                html_data = html_data.replace("body{background:#02050d;", "body{background:transparent;")
                components.html(html_data, height=450, scrolling=True)
                
                with st.spinner("Analyzing media with Gemini 1.5 Flash..."):
                    mime_type = uploaded.type
                    result_text = analyze_with_gemini(uploaded.getvalue(), mime_type)
                    
                    st.markdown("### 🧠 Gemini Analysis Results")
                    try:
                        # Try to parse as JSON if the model returned JSON block
                        clean_text = result_text.replace('```json', '').replace('```', '').strip()
                        res_obj = json.loads(clean_text)
                        st.json(res_obj)
                    except:
                        # Fallback to markdown text
                        st.markdown(f"<div style='background:rgba(0,200,255,0.05); padding:16px; border:1px solid rgba(0,200,255,0.2); border-radius:4px;'>{result_text}</div>", unsafe_allow_html=True)
        else:
            # Show static placeholder animation when not running
            import streamlit.components.v1 as components
            with open(r"D:\Hackathon\stream\gemini_ultra_scan_prev_fixed (1).html", "r", encoding="utf-8") as f:
                html_data = f.read()
            html_data = html_data.replace("body{background:#02050d;", "body{background:transparent;")
            components.html(html_data, height=450, scrolling=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📋  Recent Scans</div>", unsafe_allow_html=True)
        for t in THREATS[:5]:
            badge_cls = f"badge-{t['severity']}"
            st.markdown(f"""
            <div class='threat-row'>
                <span class='threat-badge {badge_cls}'>{t['severity'].upper()}</span>
                <div style='flex:1'>
                    <div style='font-size:0.78rem'>{t['title'][:32]}…</div>
                    <div style='font-size:0.67rem;color:#5a7a9a'>{t['id']} · {t['time']}</div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel' style='margin-top:1rem'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>⚡  AI Confidence Score</div>", unsafe_allow_html=True)
        score = 94
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix":"%","font":{"color":"#00c8ff","size":36,"family":"Rajdhani"}},
            gauge={
                "axis":{"range":[0,100],"tickcolor":"#5a7a9a","tickwidth":1},
                "bar":{"color":"#00c8ff","thickness":0.25},
                "bgcolor":"rgba(0,0,0,0)",
                "borderwidth":0,
                "steps":[
                    {"range":[0,50],"color":"rgba(255,43,94,0.15)"},
                    {"range":[50,80],"color":"rgba(255,214,0,0.1)"},
                    {"range":[80,100],"color":"rgba(0,255,136,0.1)"},
                ],
                "threshold":{"line":{"color":"#00ff88","width":2},"thickness":0.8,"value":80}
            }
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", height=180,
            margin=dict(t=20,b=10,l=20,r=20),
            font=dict(color="#5a7a9a")
        )
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar":False})
        st.markdown("<div class='score-label'>GEMINI VISION CONFIDENCE</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAP PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "map":
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>🗺️  Global Infringement Heatmap</div>", unsafe_allow_html=True)

    df = pd.DataFrame(GEO_DATA)
    color_map = {"critical":"#ff2b5e","high":"#ff6b2b","medium":"#ffd600","low":"#00ff88"}
    df["color"] = df["severity"].map(color_map)
    df["size"] = df["count"] / df["count"].max() * 40 + 10

    fig_map = go.Figure(go.Scattergeo(
        lat=df["lat"], lon=df["lon"],
        text=df.apply(lambda r: f"{r['city']}<br>{r['count']} violations<br>Severity: {r['severity'].upper()}", axis=1),
        mode="markers",
        marker=dict(
            size=df["size"], color=df["color"],
            line=dict(width=1, color="rgba(0,200,255,0.4)"),
            opacity=0.85,
        ),
        hovertemplate="%{text}<extra></extra>"
    ))
    fig_map.update_layout(
        geo=dict(
            bgcolor="rgba(5,9,17,1)",
            showland=True, landcolor="#0a1628",
            showocean=True, oceancolor="#050911",
            showcoastlines=True, coastlinecolor="rgba(0,200,255,0.2)",
            showframe=False,
            projection_type="natural earth",
            showcountries=True, countrycolor="rgba(0,200,255,0.1)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=10,r=10), height=450,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e8f4ff"))
    )
    st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar":False})

    cols = st.columns(len(df))
    for i, row in df.iterrows():
        with cols[i]:
            st.markdown(f"""
            <div style='text-align:center;padding:0.4rem;border:1px solid {row.color}20;border-radius:3px;'>
                <div style='font-family:Share Tech Mono;font-size:0.65rem;color:{row.color}'>{row['count']}</div>
                <div style='font-size:0.65rem;color:#5a7a9a'>{row.city}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─── ALERTS PAGE ──────────────────────────────────────────────────────────────
elif st.session_state.page == "alerts":
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🚨  Live Alert Feed</div>", unsafe_allow_html=True)
        for sev, tid, msg, t in ALERTS_LIVE:
            st.markdown(f"""
            <div class='alert-item alert-{sev}'>
                <div>
                    <span class='threat-badge badge-{sev}'>{sev.upper()}</span>
                    <span class='alert-msg' style='margin-left:8px'>[{tid}] {msg}</span>
                    <div class='alert-time'>⏱ {t}</div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>⚡  Quick Actions</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🚨  Issue Mass Takedown", type="primary", use_container_width=True)
        st.button("📧  Email DMCA Report", use_container_width=True)
        st.button("📊  Export to BigQuery", use_container_width=True)
        st.button("🔄  Rescan All Platforms", use_container_width=True)

        st.markdown("---")
        st.markdown("<div class='panel-title'>📊  Alert Stats</div>", unsafe_allow_html=True)
        for label, val, col_ in [("Critical",47,"#ff2b5e"),("High",156,"#ff6b2b"),("Medium",312,"#ffd600"),("Resolved",892,"#00ff88")]:
            st.markdown(f"""
            <div style='display:flex;justify-content:space-between;padding:0.35rem 0;
                        border-bottom:1px solid rgba(0,200,255,0.07);font-size:0.82rem'>
                <span style='color:#5a7a9a'>{label}</span>
                <span style='font-family:Share Tech Mono;color:{col_}'>{val}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# WATERMARKING PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "watermark":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🔐  Embed Invisible Watermark</div>", unsafe_allow_html=True)

        asset_id   = st.text_input("Asset ID / Title", value="NFL_SB58_Highlight_Official")
        org_name   = st.text_input("Organization", value="NFL Media Group")
        wm_strength= st.slider("Watermark Strength (Invisibility ↔ Robustness)", 1, 10, 7)
        wm_type    = st.selectbox("Watermark Type", ["Perceptual Hash + DCT","LSB Steganography","Frequency Domain (DWT)"])

        if st.button("⚡  EMBED WATERMARK & MINT BLOCKCHAIN RECORD", type="primary", use_container_width=True):
            with st.spinner("Embedding via Gemini + GCP Blockchain Node…"):
                time.sleep(1.5)
            st.markdown("""
            <div style='background:rgba(0,255,136,0.07);border:1px solid #00ff88;
                        border-radius:4px;padding:1rem;margin-top:0.5rem'>
                <div style='color:#00ff88;font-family:Rajdhani;font-weight:700;letter-spacing:2px'>
                    ✅ WATERMARK EMBEDDED SUCCESSFULLY
                </div>
                <div style='margin-top:0.5rem'>
                    <div class='hash-display'>
                    ASSET_ID: NFL_SB58_HIGHLIGHT_OFFICIAL_v1<br>
                    WM_HASH:  3a7f9b2c4e1d8056a2f3e4b5c6d7e8f9<br>
                    TX_HASH:  0x7f3a...c9b2 (GCP Blockchain)<br>
                    EMBED_TS: 2025-01-26T14:32:00Z<br>
                    STATUS:   IMMUTABLE_RECORD_CREATED
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🖼️  Visual Preview</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='wm-visual'>
            <div style='font-size:3rem;margin-bottom:0.5rem'>🏈</div>
            <div style='font-family:Rajdhani;font-size:1.1rem;font-weight:700;color:#00c8ff;
                        letter-spacing:3px'>NFL_SB58_HIGHLIGHT_OFFICIAL</div>
            <div style='font-family:Share Tech Mono;font-size:0.65rem;color:#5a7a9a;margin-top:4px'>
                Watermark invisible to human eye · strength 7/10
            </div>
            <div style='display:flex;justify-content:center;gap:1rem;margin-top:1rem'>
                <span style='font-family:Share Tech Mono;font-size:0.6rem;
                              color:#00ff88;border:1px solid rgba(0,255,136,0.3);
                              padding:3px 10px;border-radius:2px'>PROTECTED</span>
                <span style='font-family:Share Tech Mono;font-size:0.6rem;
                              color:#00c8ff;border:1px solid rgba(0,200,255,0.3);
                              padding:3px 10px;border-radius:2px'>BLOCKCHAIN VERIFIED</span>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📋  Protected Assets</div>", unsafe_allow_html=True)
        assets = [("NFL_SB58_Official","✅ Active","2h ago"),
                  ("NBA_G7_Highlights","✅ Active","5h ago"),
                  ("EPL_Final_BTS","⚠️ Tamper Alert","12h ago"),
                  ("F1_Monaco_Broadcast","✅ Active","1d ago")]
        for name, status, when in assets:
            color = "#00ff88" if "Active" in status else "#ffd600"
            st.markdown(f"""
            <div class='threat-row'>
                <span style='flex:1;font-size:0.78rem'>{name}</span>
                <span style='color:{color};font-size:0.72rem'>{status}</span>
                <span style='color:#5a7a9a;font-size:0.68rem'>{when}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "analytics":
    st.markdown("""
    <div class='metric-grid'>
        <div class='metric-card cyan'>
            <div class='metric-label'>AVG TAKEDOWN TIME</div>
            <div class='metric-value cyan'>4.2s</div>
            <div class='metric-delta'><span class='up'>90% faster</span> than manual</div>
        </div>
        <div class='metric-card green'>
            <div class='metric-label'>DETECTION ACCURACY</div>
            <div class='metric-value green'>97.3%</div>
            <div class='metric-delta'><span class='up'>▲ 2.1%</span> this week</div>
        </div>
        <div class='metric-card orange'>
            <div class='metric-label'>ASSETS MONITORED</div>
            <div class='metric-value orange'>12.4K</div>
            <div class='metric-delta'>Across 6 platforms</div>
        </div>
        <div class='metric-card red'>
            <div class='metric-label'>FALSE POSITIVE RATE</div>
            <div class='metric-value red'>0.8%</div>
            <div class='metric-delta'><span class='up'>▼ 0.3%</span> improved</div>
        </div>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📊  Threat Severity Breakdown</div>", unsafe_allow_html=True)
        fig_bar = go.Figure(go.Bar(
            x=["Critical","High","Medium","Low","Resolved"],
            y=[47,156,312,89,892],
            marker_color=["#ff2b5e","#ff6b2b","#ffd600","#00c8ff","#00ff88"],
            marker_line_color="rgba(0,0,0,0)"
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10,b=10,l=10,r=10), height=220,
            xaxis=dict(showgrid=False, color="#5a7a9a"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,200,255,0.07)", color="#5a7a9a"),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>💰  Revenue Recovery Impact</div>", unsafe_allow_html=True)
        months = ["Aug","Sep","Oct","Nov","Dec","Jan"]
        recovered = [0.8,1.1,1.4,1.8,2.1,2.4]
        fig_rev = go.Figure(go.Scatter(
            x=months, y=recovered, mode="lines+markers",
            line=dict(color="#00ff88", width=3),
            marker=dict(size=8, color="#00ff88"),
            fill="tozeroy", fillcolor="rgba(0,255,136,0.08)"
        ))
        fig_rev.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10,b=10,l=10,r=10), height=220,
            xaxis=dict(showgrid=False, color="#5a7a9a"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,200,255,0.07)",
                       color="#5a7a9a", tickprefix="$", ticksuffix="M"),
        )
        st.plotly_chart(fig_rev, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "settings":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>⚙️  Scan Configuration</div>", unsafe_allow_html=True)
        st.selectbox("Default Scan Depth", ["Standard (4 FPS)","Quick (2 FPS)","Deep (8 FPS)"])
        st.multiselect("Monitored Platforms", ["TikTok","YouTube","Instagram","X/Twitter","Facebook","Telegram","Reddit"], default=["TikTok","YouTube","Instagram"])
        st.slider("Similarity Threshold (%)", 70, 99, 85)
        st.slider("Auto-Takedown Confidence (%)", 90, 99, 95)
        st.toggle("Enable Real-Time Monitoring", value=True)
        st.toggle("Auto-Issue DMCA on Critical", value=True)
        st.toggle("Blockchain Watermark Verification", value=True)
        st.button("💾  Save Configuration", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🔐  GCP Integration</div>", unsafe_allow_html=True)
        st.text_input("Gemini API Project ID", value="sportsguardian-prod-001")
        st.text_input("Vertex AI Endpoint", value="us-central1-aiplatform.googleapis.com")
        st.text_input("BigQuery Dataset", value="sg_media_metadata")
        st.selectbox("Cloud Run Region", ["us-central1","europe-west1","asia-east1"])
        st.toggle("Enable Pub/Sub Streaming", value=True)
        st.toggle("GPU Acceleration (A100)", value=True)
        st.button("🔗  Test GCP Connection", use_container_width=True)
        st.markdown("<div style='color:#00ff88;font-size:0.75rem;margin-top:0.5rem'>✅ All services connected — latency: 12ms</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ─── AUTO BROWSER PAGE ────────────────────────────────────────────────────────
elif st.session_state.page == "auto_browser":
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>🌐  Autonomous Browser Execution</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='color: var(--text-dim); margin-bottom: 24px;'>
        Real-time view of the Gemini Ultra scanning engine simulating headless browser traversal across platforms.
    </div>
    """, unsafe_allow_html=True)
    
    # --- The Trigger Button ---
    run_crawler = st.button("🚀 INITIATE AUTONOMOUS BROWSER CRAWLER", use_container_width=True)
    
    if run_crawler:
        with st.spinner("🤖 Autonomous Agent spinning up headless Chrome instance & searching for piracy streams..."):
            # Step 1: Run Playwright
            scraped_results = run_playwright_search()
            
            if len(scraped_results) > 0 and "error" in scraped_results[0]:
                st.error(f"Crawler Failed: {scraped_results[0]['error']}")
            else:
                # Step 2: Show HTML Animation (simulating scanning)
                import streamlit.components.v1 as components
                with open(r"D:\Hackathon\stream\gemini_ultra_scan_prev_fixed (1).html", "r", encoding="utf-8") as f:
                    html_data = f.read()
                html_data = html_data.replace("body{background:#02050d;", "body{background:transparent;")
                components.html(html_data, height=450, scrolling=True)
                
                # Step 3: Analyze with Gemini
                st.info("📡 Streams located. Sending payloads to Gemini AI for Threat Intelligence evaluation...")
                gemini_eval = analyze_links_with_gemini(scraped_results)
                
                st.markdown("### 🛑 Threat Intelligence Report")
                try:
                    clean_text = gemini_eval.replace('```json', '').replace('```', '').strip()
                    res_obj = json.loads(clean_text)
                    st.json(res_obj)
                except:
                    st.markdown(f"<div style='background:rgba(255,43,94,0.05); padding:16px; border:1px solid rgba(255,43,94,0.2); border-radius:4px;'>{gemini_eval}</div>", unsafe_allow_html=True)
                
                with st.expander("Raw Scraped Telemetry"):
                    st.json(scraped_results)

    else:
        # Default state - just show the animation
        import streamlit.components.v1 as components
        with open(r"D:\Hackathon\stream\gemini_ultra_scan_prev_fixed (1).html", "r", encoding="utf-8") as f:
            html_data = f.read()
        html_data = html_data.replace("body{background:#02050d;", "body{background:transparent;")
        components.html(html_data, height=800, scrolling=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
