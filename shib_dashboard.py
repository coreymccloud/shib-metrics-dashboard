import streamlit as st
import requests
from datetime import datetime
import re

# Page config
st.set_page_config(
    page_title="SHIB Burn Tracker",
    page_icon="🐕",
    layout="centered"
)

# JavaScript Auto-refresh every 15 seconds
st.markdown("""
    <script>
        function autoRefresh() {
            setTimeout(function() {
                window.location.reload();
            }, 15000);
        }
        window.onload = autoRefresh;
    </script>
""", unsafe_allow_html=True)

st.title("🐕 Shiba Inu (SHIB) Burn & Price Tracker")
st.caption("🔄 Auto-refreshes every 15 seconds • Burn data from Shibburn.com")

def fetch_shib_data():
    try:
        # 1. Get burn data from Shibburn
        burn_url = "https://www.shibburn.com/"
        headers = {"User-Agent": "Mozilla/5.0"}
        burn_resp = requests.get(burn_url, headers=headers, timeout=10)
        burn_resp.raise_for_status()
        
        # Extract numbers using regex
        burned_match = re.search(r'Total Burned.*?([\d,]+)', burn_resp.text)
        supply_match = re.search(r'Total Supply.*?([\d,]+)', burn_resp.text)
        percent_match = re.search(r'(\d+\.\d+)%', burn_resp.text)
        
        burned = int(burned_match.group(1).replace(',', '')) if burned_match else 410_840_050_460_000
        total_supply = int(supply_match.group(1).replace(',', '')) if supply_match else 589_159_949_539_502
        burn_percentage = float(percent_match.group(1)) if percent_match else (burned / 1_000_000_000_000_000) * 100
        
        # 2. Get price from CoinGecko
        price_url = "https://api.coingecko.com/api/v3/coins/shiba-inu"
        price_resp = requests.get(price_url, timeout=10)
        price_resp.raise_for_status()
        price_data = price_resp.json()
        price = price_data['market_data']['current_price']['usd']
        
        return {
            "price": price,
            "burn_percentage": burn_percentage,
            "burned": burned,
            "total_supply": total_supply,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

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

    st.subheader("Supply & Burn Details")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total Supply", f"{data['total_supply']:,.0f}")
    with col_b:
        st.metric("Tokens Burned", f"{data['burned']:,.0f}")
    with col_c:
        st.metric("Remaining Supply", f"{data['total_supply'] - data['burned']:,.0f}")

    st.success(f"✅ Last updated: {data['timestamp']}")
    st.caption("Burn data scraped from Shibburn.com (powered by Burnalytics) • Price from CoinGecko")

else:
    st.error("Could not load data. Please check your connection.")

st.markdown("---")
st.caption("Initial Supply: 1 Quadrillion SHIB")
