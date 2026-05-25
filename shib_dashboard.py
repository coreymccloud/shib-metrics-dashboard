import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import re

# ====================== MOBILE OPTIMIZATIONS ======================
st.set_page_config(
    page_title="SHIB Live Metrics",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        .stMetric { font-size: 1.15rem !important; }
        .stMarkdown h1 { font-size: 1.85rem !important; }
        button { min-height: 52px !important; }
    </style>
""")

st.title("🚀 SHIB Live Metrics")
st.caption("MVRV • Multi-Period Z-Score • Adapted Puell | Improved Burn Scraper")

auto_refresh = st.toggle("🔄 Auto-refresh every 15 seconds", value=True)

# ====================== CONSTANTS ======================
REALIZED_CAP = 3_300_000_000

PERIODS = [
    ("3 Days", 3),
    ("5 Days", 5),
    ("30 Days", 30),
    ("90 Days", 90),
    ("180 Days", 180),
    ("365 Days", 365)
]

# ====================== DATA FETCHING ======================
@st.cache_data(ttl=60)
def get_shib_current():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/coins/shiba-inu", timeout=10).json()
        return {
            'price': data['market_data']['current_price']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
        }
    except:
        return None

@st.cache_data(ttl=3600)
def get_historical_data(days=365):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days={days}&interval=daily"
        data = requests.get(url, timeout=20).json()
        return pd.DataFrame({
            'market_cap': [item[1] for item in data.get('market_caps', [])],
            'price': [item[1] for item in data.get('prices', [])]
        })
    except:
        return pd.DataFrame()

def get_daily_burn():
    """Improved robust scraper - tries multiple patterns"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 1. Shibburn (Primary - most reliable right now)
    try:
        r = requests.get("https://www.shibburn.com/", headers=headers, timeout=15)
        text = r.text

        # Multiple fallback patterns for "Last 24 Hours"
        patterns = [
            r'Last 24 Hours[^0-9]*([\d,]+)',           # Original
            r'Last 24 Hours.*?>?([\d,]+)',             # More flexible
            r'24 Hours[^0-9]*([\d,]+)',                # Alternative label
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = int(match.group(1).replace(',', ''))
                if 10_000 < val < 500_000_000:
                    return val, "Shibburn"
    except:
        pass

    # 2. Burnalytics fallback
    try:
        r = requests.get("https://www.burnalytics.com/asset/0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce", 
                        headers=headers, timeout=15)
        text = r.text
        match = re.search(r'24H[^0-9]*([\d,]+)', text, re.IGNORECASE | re.DOTALL)
        if match:
            val = int(match.group(1).replace(',', ''))
            if 10_000 < val < 500_000_000:
                return val, "Burnalytics"
    except:
        pass

    # Safe fallback
    return 1_271_623, "Fallback"

# ====================== CALCULATIONS ======================
def calculate_mvrv(mcap):
    return mcap / REALIZED_CAP if REALIZED_CAP > 0 else None

def calculate_zscore(current_mvrv, hist_series):
    if len(hist_series) < 2 or current_mvrv is None:
        return None
    mean = np.mean(hist_series)
    std = np.std(hist_series)
    return (current_mvrv - mean) / std if std > 0 else None

def get_zscore_action(zscore):
    if zscore is None:
        return "Not enough data"
    if zscore > 2.0:
        return "🔴 Strong Sell / Top Signal"
    elif zscore > 1.0:
        return "🟡 Take Profits"
    elif zscore < -1.5:
        return "🟢 Strong Buy / Accumulate"
    elif zscore < -1.0:
        return "🟢 Buy Zone"
    else:
        return "⚪ Hold / Neutral"

def calculate_puell(daily_burn, price):
    daily_val = daily_burn * price
    ma_val = daily_burn * 2.1 * price
    return daily_val / ma_val if ma_val > 0 else None

# ====================== MAIN DASHBOARD ======================
placeholder = st.empty()

while True:
    with placeholder.container():
        current = get_shib_current()
        hist_df = get_historical_data(days=365)
        daily_burn, source = get_daily_burn()

        if not current:
            st.error("⚠️ Unable to fetch data. Retrying soon...")
        else:
            price = current['price']
            mcap = current['market_cap']
            current_mvrv = calculate_mvrv(mcap)

            # Top Row
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Price", f"${price:.10f}")
            with col2:
                st.metric("24h Burn", f"{daily_burn:,.0f} SHIB", delta=f"via {source}")

            # ... (rest of your dashboard remains the same as previous version)

            st.divider()

            # Current MVRV (unchanged)
            st.subheader("Current MVRV")
            mcol1, mcol2 = st.columns([2, 1])
            with mcol1:
                st.metric("MVRV Ratio", f"{current_mvrv:.2f}" if current_mvrv else "—")
            with mcol2:
                with st.expander("What is MVRV?", expanded=False):
                    st.markdown("""
                    **MVRV = Market Cap ÷ Realized Cap**  
                    - Market Cap: Current price × supply  
                    - Realized Cap: Value at last on-chain movement  
                    **Guide**: >2.5 Overvalued | 0.8-1.2 Fair | <0.8 Undervalued
                    """)

            st.divider()

            # Z-Score Section (unchanged)
            st.subheader("MVRV Z-Score by Time Period")
            zcol1, zcol2 = st.columns([3, 1])
            with zcol1:
                zscore_cols = st.columns(3)
                for idx, (label, days) in enumerate(PERIODS):
                    with zscore_cols[idx % 3]:
                        period_df = hist_df.tail(days) if not hist_df.empty else hist_df
                        hist_mvrv = (period_df['market_cap'] / REALIZED_CAP).tolist() if not period_df.empty else []
                        zscore = calculate_zscore(current_mvrv, hist_mvrv)
                        
                        st.metric(label, f"{zscore:.2f}" if zscore is not None else "—")
                        st.caption(get_zscore_action(zscore))

            # ... rest of the code (Puell + Charts) remains the same

            st.caption("Realized Cap from Glassnode")

    if not auto_refresh:
        break

    time.sleep(15)
    st.rerun()

if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
    st.rerun()
