import streamlit as st
import requests
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SHIB Burn & Price Tracker",
    page_icon="🐕",
    layout="centered"
)

# JavaScript Auto-refresh (every 15 seconds)
st.markdown("""
    <script>
        function autoRefresh() {
            setTimeout(function() {
                window.location.reload();
            }, 15000);  // 15000 ms = 15 seconds
        }
        window.onload = autoRefresh;
    </script>
""", unsafe_allow_html=True)

st.title("🐕 Shiba Inu (SHIB) Burn & Price Tracker")
st.caption("🔄 Auto-refreshes every 15 seconds • Live data from CoinGecko")

# Fetch SHIB data
def fetch_shib_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/shiba-inu"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        price = data['market_data']['current_price']['usd']
        
        # Total supply from API (or fallback)
        total_supply = data['market_data'].get('total_supply') or 589_263_580_626_907
        circulating_supply = data['market_data'].get('circulating_supply') or 589_263_580_626_907
        
        initial_supply = 1_000_000_000_000_000  # 1 Quadrillion
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
        st.error(f"Failed to fetch data: {e}")
        return None

# Get data
data = fetch_shib_data()

if data:
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="💰 Current SHIB Price (USD)",
            value=f"${data['price']:.8f}"
        )
    
    with col2:
        st.metric(
            label="🔥 Total Burn Percentage",
            value=f"{data['burn_percentage']:.4f}%"
        )

    st.divider()

    # More stats
    st.subheader("Supply Information")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total Supply", f"{data['total_supply']:,.0f}")
    with col_b:
        st.metric("Circulating Supply", f"{data['circulating']:,.0f}")
    with col_c:
        st.metric("Tokens Burned", f"{data['burned']:,.0f}")

    st.success(f"✅ Last updated: {data['timestamp']}")

else:
    st.error("Could not load data. Please check your internet connection.")

st.markdown("---")
st.caption("Data source: CoinGecko • Initial Supply: 1,000,000,000,000,000 SHIB")
