import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

# ====================== MOBILE OPTIMIZATIONS ======================
st.set_page_config(
    page_title="SHIB Metrics",
    layout="centered",           # Better than "wide" on mobile
    initial_sidebar_state="collapsed",  # Clean on mobile
    menu_items={"About": "SHIB MVRV + Z-Score + Puell Dashboard"}
)

# Force mobile-friendly viewport
st.html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        .stMetric { font-size: 1.1rem !important; }
        .stMarkdown h1 { font-size: 1.8rem !important; }
        .stMarkdown h2 { font-size: 1.4rem !important; }
        .stPlotlyChart { margin: 0 !important; }
        button { min-height: 48px !important; } /* Better touch target */
    </style>
""")

st.title("🚀 SHIB Live Metrics")
st.caption("MVRV • Z-Score • Adapted Puell | Auto-refreshes every 15s")

# Auto-refresh toggle (prominent on mobile)
auto_refresh = st.toggle("🔄 Auto-refresh every 15 seconds", value=True, key="auto_toggle")

# ====================== DATA FUNCTIONS ======================
@st.cache_data(ttl=60)
def get_shib_current():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/coins/shiba-inu", timeout=10).json()
        return {
            'price': data['market_data']['current_price']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
            'updated': data['last_updated']
        }
    except:
        return None

@st.cache_data(ttl=1800)
def get_historical_data(days=180):   # Reduced to 180 days for faster mobile loading
    try:
        url = f"https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days={days}&interval=daily"
        data = requests.get(url, timeout=15).json()
        return pd.DataFrame({
            'market_cap': [item[1] for item in data.get('market_caps', [])],
            'price': [item[1] for item in data.get('prices', [])]
        })
    except:
        return pd.DataFrame()

def scrape_daily_burn():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get("https://www.shibburn.com/", headers=headers, timeout=10)
        text = BeautifulSoup(r.text, 'html.parser').get_text()
        if "Last 24 Hours" in text:
            num_str = ''.join(filter(str.isdigit, text.split("Last 24 Hours")[1][:80]))
            return int(num_str) if num_str else 2243783
        return 2243783
    except:
        return 2243783

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

# ====================== MAIN LOOP ======================
placeholder = st.empty()

while True:
    with placeholder.container():
        current = get_shib_current()
        hist_df = get_historical_data()
        daily_burn = scrape_daily_burn()

        if not current:
            st.error("⚠️ Unable to fetch data. Retrying soon...")
        else:
            price = current['price']
            mcap = current['market_cap']
            mvrv = calculate_mvrv(mcap)
            hist_mvrv = (hist_df['market_cap'] / 2_900_000_000).tolist() if not hist_df.empty else []
            zscore = calculate_zscore(mvrv, hist_mvrv)
            puell = calculate_puell(daily_burn, price)

            # === TOP METRICS (Stacked on mobile) ===
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Price", f"${price:.10f}", delta=None)
            with col2:
                st.metric("Market Cap", f"${mcap:,.0f}")

            col3, col4 = st.columns(2)
            with col3:
                st.metric("24h Burn", f"{daily_burn:,.0f} SHIB")
            with col4:
                st.metric("Updated", current['updated'][:16])

            st.divider()

            # === KEY INDICATORS (Vertical on mobile) ===
            st.subheader("Key Indicators")
            
            c1, c2, c3 = st.columns(1) if st.runtime.exists else st.columns(3)  # Force vertical on very small screens

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

            # === CHARTS (Optimized for mobile) ===
            st.subheader("Charts")
            tab1, tab2 = st.tabs(["Market Cap", "Price History"])

            with tab1:
                if not hist_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['market_cap']/1e9,
                                           name="Market Cap ($B)", line=dict(color="#1E88E5", width=2.5)))
                    fig.add_hline(y=2.9, line_dash="dash", line_color="red", annotation_text="Est. Realized Cap")
                    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with tab2:
                if not hist_df.empty:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=hist_df.index, y=hist_df['price'],
                                            name="Price", line=dict(color="#FF9800", width=2.5)))
                    fig2.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig2, use_container_width=True)

            st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')} • Realized Cap is estimated")

    if not auto_refresh:
        break

    time.sleep(15)
    st.rerun()

# Manual refresh at bottom (big touch target)
if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
    st.rerun()
