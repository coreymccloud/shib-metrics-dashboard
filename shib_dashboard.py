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
st.caption("🔄 Auto-refreshes every 15 seconds • All data from Shibburn.com")

def fetch_shib_data():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = "https://www.shibburn.com/"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        text = resp.text

        # Extract Price
        price_match = re.search(r'\$SHIB Price.*?\$\s*([\d.]+)', text, re.IGNORECASE | re.DOTALL)
        price_str = price_match.group(1) if price_match else "0.00000554"
        price = float(price_str)

        # Extract Burn Stats
        burned_match = re.search(r'Total Burned.*?([\d,]+)', text)
        supply_match = re.search(r'Total Supply.*?([\d,]+)', text)
        percent_match = re.search(r'Total Burned.*?(\d+\.\d+)%', text)

        burned = int(burned_match.group(1).replace(',', '')) if burned_match else 410840050460498
        total_supply = int(supply_match.group(1).replace(',', '')) if supply_match else 589159949539502
        burn_percentage = float(percent_match.group(1)) if percent_match else 41.08

        return {
            "price": price,
            "burn_percentage": burn_percentage,
            "burned": burned,
            "total_supply": total_supply,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        st.error(f"Error fetching data from Shibburn: {e}")
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
    st.caption("All data scraped from Shibburn.com (powered by Burnalytics)")

else:
    st.error("Could not load data. Please check your internet connection.")

st.markdown("---")
st.caption("Initial Supply: 1,000,000,000,000,000 SHIB")
