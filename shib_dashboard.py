import streamlit as st
import requests
import time
from datetime import datetime

# Page config
st.set_page_config(
    page_title="SHIB Burn Tracker",
    page_icon="🐕",
    layout="centered"
)

# Auto-refresh using st_autorefresh component (install if needed)
try:
    from streamlit_autorefresh import st_autorefresh
    # Refresh every 15 seconds
    st_autorefresh(interval=15000, limit=None, key="datarefresh")
except ImportError:
    st.warning("For auto-refresh every 15s, run: `pip install streamlit-autorefresh`")

st.title("🐕 Shiba Inu (SHIB) Burn & Price Tracker")
st.markdown("**Live data • Updates every 15 seconds**")

# Fetch data function
def fetch_shib_data():
    try:
        # CoinGecko API - SHIB data
        url = "https://api.coingecko.com/api/v3/coins/shiba-inu"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        price = data['market_data']['current_price']['usd']
        total_supply = data['market_data'].get('total_supply') or 589_000_000_000_000  # approx
        circulating_supply = data['market_data'].get('circulating_supply') or 589_000_000_000_000
        
        # Initial supply is ~1 quadrillion (1_000_000_000_000_000)
        initial_supply = 1_000_000_000_000_000
        burned = initial_supply - total_supply
        burn_percentage = (burned / initial_supply) * 100
        
        return {
            "price": price,
            "burn_percentage": burn_percentage,
            "burned": burned,
            "total_supply": total_supply,
            "circulating": circulating_supply,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Fetch data
data = fetch_shib_data()

if data:
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="💰 Current SHIB Price (USD)",
            value=f"${data['price']:.8f}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="🔥 Total Burn Percentage",
            value=f"{data['burn_percentage']:.4f}%",
            delta=None
        )
    
    st.divider()
    
    # Additional stats
    st.subheader("Supply Details")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total Supply", f"{data['total_supply']:,.0f}")
    with col_b:
        st.metric("Circulating Supply", f"{data['circulating']:,.0f}")
    with col_c:
        st.metric("Tokens Burned", f"{data['burned']:,.0f}")
    
    st.caption(f"Last updated: {data['timestamp']}")
else:
    st.error("Could not fetch data. Please check your connection.")

st.markdown("---")
st.caption("Data from CoinGecko • Initial supply: 1 Quadrillion SHIB • Burn % calculated as (Initial - Total Supply)/Initial")
