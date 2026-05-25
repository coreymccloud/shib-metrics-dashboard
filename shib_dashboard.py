import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# ====================== STRONG MOBILE OPTIMIZATIONS ======================
st.set_page_config(
    page_title="SHIB Metrics",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={"About": "SHIB MVRV & Z-Score Dashboard"}
)

st.html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        .stMetric { font-size: 1.2rem !important; padding: 10px 0 !important; }
        .stMarkdown h1 { font-size: 1.9rem !important; }
        .stMarkdown h2 { font-size: 1.4rem !important; }
        button { min-height: 52px !important; font-size: 1rem !important; }
        .stPlotlyChart { margin: 8px 0 !important; }
        .css-1d391kg { padding-top: 1rem !important; } /* Reduce spacing */
    </style>
""")

st.title("🚀 SHIB Live Metrics")
st.caption("MVRV Ratio + Multi-Period Z-Score")

auto_refresh = st.toggle("🔄 Auto-refresh every 15s", value=True)

# ====================== CONSTANTS ======================
REALIZED_CAP = 3_300_000_000

PERIODS = [
    ("3 Days", 3), ("7 Days", 7), ("30 Days", 30),
    ("90 Days", 90), ("180 Days", 180), ("365 Days", 365)
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
    if zscore is None: return "Not enough data"
    if zscore > 2.0: return "🔴 Strong Sell"
    elif zscore > 1.0: return "🟡 Take Profits"
    elif zscore < -1.5: return "🟢 Strong Buy"
    elif zscore < -1.0: return "🟢 Buy Zone"
    else: return "⚪ Neutral"

# ====================== MAIN DASHBOARD ======================
placeholder = st.empty()

while True:
    with placeholder.container():
        current = get_shib_current()
        hist_df = get_historical_data(days=365)

        if not current:
            st.error("⚠️ Unable to fetch data...")
        else:
            price = current['price']
            mcap = current['market_cap']
            current_mvrv = calculate_mvrv(mcap)

            st.metric("**Current Price**", f"${price:.8f}")

            st.divider()

            # Current MVRV
            st.subheader("Current MVRV")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.metric("MVRV Ratio", f"{current_mvrv:.2f}" if current_mvrv else "—")
            with col2:
                with st.expander("ℹ️", expanded=False):
                    st.markdown("**MVRV** = Market Cap ÷ Realized Cap")

            st.divider()

            # Z-Scores - Better mobile layout
            st.subheader("MVRV Z-Score by Time Period")
            for i in range(0, len(PERIODS), 2):   # 2 per row on mobile
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(PERIODS):
                        label, days = PERIODS[i + j]
                        with cols[j]:
                            period_df = hist_df.tail(days) if not hist_df.empty else hist_df
                            hist_mvrv = (period_df['market_cap'] / REALIZED_CAP).tolist() if not period_df.empty else []
                            zscore = calculate_zscore(current_mvrv, hist_mvrv)
                            st.metric(label, f"{zscore:.2f}" if zscore is not None else "—")
                            st.caption(get_zscore_action(zscore))

            st.divider()

            # Charts - Smaller height for mobile
            st.subheader("Charts")
            tab1, tab2 = st.tabs(["Market Cap", "Price"])

            with tab1:
                if not hist_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['market_cap']/1e9, 
                                           line=dict(color="#1E88E5", width=2.5)))
                    fig.add_hline(y=REALIZED_CAP/1e9, line_dash="dash", line_color="red")
                    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with tab2:
                if not hist_df.empty:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=hist_df.index, y=hist_df['price'], 
                                            line=dict(color="#FF9800", width=2.5)))
                    fig2.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig2, use_container_width=True)

    if not auto_refresh:
        break

    time.sleep(15)
    st.rerun()

if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
    st.rerun()
