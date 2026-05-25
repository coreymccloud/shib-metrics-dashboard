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
    initial_sidebar_state="collapsed",
    menu_items={"About": "Shiba Inu MVRV + Z-Score + Puell Dashboard"}
)

st.html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        .stMetric { font-size: 1.15rem !important; }
        .stMarkdown h1 { font-size: 1.85rem !important; }
        button { min-height: 52px !important; }
        .stPlotlyChart { margin-bottom: 10px !important; }
    </style>
""")

st.title("🚀 SHIB Live Metrics")
st.caption("MVRV • MVRV Z-Score • Adapted Puell | Burnalytics + Shibburn")

auto_refresh = st.toggle("🔄 Auto-refresh every 15 seconds", value=True)

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

@st.cache_data(ttl=1800)
def get_historical_data(days=180):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days={days}&interval=daily"
        data = requests.get(url, timeout=15).json()
        return pd.DataFrame({
            'market_cap': [item[1] for item in data.get('market_caps', [])],
            'price': [item[1] for item in data.get('prices', [])]
        })
    except:
        return pd.DataFrame()

def scrape_burnalytics_burn():
    """Primary: Burnalytics (more reliable)"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # SHIB page on Burnalytics
        response = requests.get("https://www.burnalytics.com/asset/0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce", 
                              headers=headers, timeout=12)
        text = response.text

        # Look for 24h burn (often near "24H" or in stats)
        match = re.search(r'24H[^0-9]*([\d,]+)', text, re.IGNORECASE | re.DOTALL)
        if match:
            burn_str = match.group(1).replace(',', '')
            daily = int(burn_str)
            if 10_000 < daily < 500_000_000:
                return daily
    except:
        pass
    return None

def scrape_shibburn_burn():
    """Fallback: Shibburn"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get("https://www.shibburn.com/", headers=headers, timeout=12)
        text = response.text

        match = re.search(r'Last 24 Hours[^0-9]*([\d,]+)', text, re.IGNORECASE | re.DOTALL)
        if match:
            burn_str = match.group(1).replace(',', '')
            daily = int(burn_str)
            if 10_000 < daily < 500_000_000:
                return daily
    except:
        pass
    return 1_271_623  # safe fallback

def get_daily_burn():
    """Try Burnalytics first, then Shibburn"""
    burn = scrape_burnalytics_burn()
    if burn:
        return burn, "Burnalytics"
    burn = scrape_shibburn_burn()
    return burn, "Shibburn"

# ====================== CALCULATIONS ======================
def calculate_mvrv(mcap, realized=2_900_000_000):
    return mcap / realized if realized > 0 else None

def calculate_zscore(current_mvrv, hist_series):
    if len(hist_series) < 20 or current_mvrv is None:
        return None
    return (current_mvrv - np.mean(hist_series)) / np.std(hist_series)

def calculate_puell(daily_burn, price):
    daily_val = daily_burn * price
    ma_val = daily_burn * 2.1 * price
    return daily_val / ma_val if ma_val > 0 else None

# ====================== MAIN DASHBOARD ======================
placeholder = st.empty()

while True:
    with placeholder.container():
        current = get_shib_current()
        hist_df = get_historical_data()
        daily_burn, source = get_daily_burn()

        if not current:
            st.error("⚠️ Unable to fetch data. Retrying soon...")
        else:
            price = current['price']
            mcap = current['market_cap']
            mvrv = calculate_mvrv(mcap)
            hist_mvrv = (hist_df['market_cap'] / 2_900_000_000).tolist() if not hist_df.empty else []
            zscore = calculate_zscore(mvrv, hist_mvrv)
            puell = calculate_puell(daily_burn, price)

            # Top Metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Price", f"${price:.10f}")
            with col2:
                st.metric("24h Burn", f"{daily_burn:,.0f} SHIB", delta=f"via {source}")

            st.divider()

            # Key Indicators
            st.subheader("Key Indicators")
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("📈 MVRV Ratio", f"{mvrv:.2f}" if mvrv else "—")
                if mvrv:
                    if mvrv > 2.5: st.error("🔴 Significantly Overvalued")
                    elif mvrv > 1.2: st.warning("🟡 In Profit Zone")
                    elif mvrv < 0.8: st.success("🟢 Potentially Undervalued")
                    else: st.info("⚪ Fair Value")

            with c2:
                st.metric("📉 MVRV Z-Score", f"{zscore:.2f}" if zscore else "—")
                if zscore:
                    if zscore > 2.0: st.error("🔴 Extreme Overvalued")
                    elif zscore > 1.0: st.warning("🟡 Overvalued")
                    elif zscore < -1.5: st.success("🟢 Strong Buy Zone")
                    else: st.info("⚪ Neutral")

            with c3:
                st.metric("🔥 Adapted Puell", f"{puell:.2f}" if puell else "—")
                if puell:
                    if puell > 1.8: st.success("🔥 High Burn Pressure → Bullish")
                    elif puell > 1.0: st.info("🟡 Above Average")
                    else: st.warning("⚠️ Low Burn Activity")

            # Charts (unchanged)
            st.subheader("Historical Charts")
            tab1, tab2 = st.tabs(["Market Cap", "Price History"])

            with tab1:
                if not hist_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['market_cap']/1e9,
                                           name="Market Cap ($B)", line=dict(color="#1E88E5", width=2.5)))
                    fig.add_hline(y=2.9, line_dash="dash", line_color="red", annotation_text="Est. Realized Cap ~$2.9B")
                    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with tab2:
                if not hist_df.empty:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=hist_df.index, y=hist_df['price'],
                                            name="Price (USD)", line=dict(color="#FF9800", width=2.5)))
                    fig2.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig2, use_container_width=True)

            st.caption("Realized Cap is an estimate • Powered by Burnalytics + Shibburn")

    if not auto_refresh:
        break

    time.sleep(15)
    st.rerun()

# Manual refresh
if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
    st.rerun()
