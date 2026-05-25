import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(
    page_title="SHIB Metrics",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        .stMetric { font-size: 1.25rem !important; margin: 4px 0 !important; }
        .stMarkdown h1 { font-size: 1.75rem !important; margin-bottom: 0.3rem !important; }
        .stMarkdown h2 { font-size: 1.25rem !important; margin: 8px 0 !important; }
        button { min-height: 48px !important; }
        .stPlotlyChart { margin: 4px 0 !important; }
        .stDivider { margin: 8px 0 !important; }
    </style>
""")

st.title("🚀 SHIB Metrics")
st.caption("MVRV + Z-Score")

auto_refresh = st.toggle("Auto-refresh 15s", value=True)

# ====================== CONSTANTS ======================
REALIZED_CAP = 3_300_000_000

PERIODS = [
    ("3D", 3), ("5D", 5), ("30D", 30),
    ("90D", 90), ("180D", 180), ("365D", 365)
]

# ====================== DATA ======================
@st.cache_data(ttl=60)
def get_current():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/coins/shiba-inu", timeout=10).json()
        return {
            'price': data['market_data']['current_price']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
        }
    except:
        return None

@st.cache_data(ttl=3600)
def get_history():
    try:
        url = "https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days=365&interval=daily"
        data = requests.get(url, timeout=20).json()
        return pd.DataFrame({
            'market_cap': [item[1] for item in data.get('market_caps', [])],
            'price': [item[1] for item in data.get('prices', [])]
        })
    except:
        return pd.DataFrame()

# ====================== CALCULATIONS ======================
def mvrv(mcap): 
    return mcap / REALIZED_CAP if REALIZED_CAP else None

def zscore(current, hist):
    if len(hist) < 2 or current is None: 
        return None
    return (current - np.mean(hist)) / np.std(hist)

def action(z):
    if z is None: return "—"
    if z > 2.0: return "🔴 Strong Sell"
    if z > 1.0: return "🟡 Take Profit"
    if z < -1.5: return "🟢 Strong Buy"
    if z < -1.0: return "🟢 Buy Zone"
    return "⚪ Neutral"

# ====================== MAIN ======================
placeholder = st.empty()

while True:
    with placeholder.container():
        current = get_current()
        hist = get_history()

        if not current:
            st.error("Loading data...")
        else:
            price = current['price']
            mcap = current['market_cap']
            cur_mvrv = mvrv(mcap)

            # Price changed to 8 decimal places
            st.metric("Price", f"${price:.8f}")

            st.divider()

            # MVRV
            col1, col2 = st.columns([3,1])
            with col1:
                st.metric("MVRV", f"{cur_mvrv:.2f}" if cur_mvrv else "—")
            with col2:
                with st.expander("ℹ️", expanded=False):
                    st.caption("Market Cap / Realized Cap")

            st.divider()

            # Z-Scores
            st.subheader("Z-Score")
            for i in range(0, len(PERIODS), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(PERIODS):
                        label, days = PERIODS[i + j]
                        with cols[j]:
                            data = hist.tail(days) if not hist.empty else hist
                            series = (data['market_cap'] / REALIZED_CAP).tolist() if not data.empty else []
                            zs = zscore(cur_mvrv, series)
                            st.metric(label, f"{zs:.2f}" if zs is not None else "—")
                            st.caption(action(zs))

            st.divider()

            # Charts
            st.subheader("Charts")
            tab1, tab2 = st.tabs(["Market Cap", "Price"])

            with tab1:
                if not hist.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['market_cap']/1e9, line=dict(width=2.5)))
                    fig.add_hline(y=REALIZED_CAP/1e9, line_dash="dash", line_color="red")
                    fig.update_layout(height=280, margin=dict(l=10,r=10,t=20,b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with tab2:
                if not hist.empty:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=hist.index, y=hist['price'], line=dict(width=2.5)))
                    fig2.update_layout(height=280, margin=dict(l=10,r=10,t=20,b=10))
                    st.plotly_chart(fig2, use_container_width=True)

    if not auto_refresh:
        break

    time.sleep(15)
    st.rerun()

if st.button("🔄 Refresh", use_container_width=True, type="primary"):
    st.rerun()
