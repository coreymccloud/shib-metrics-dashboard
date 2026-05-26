import streamlit as st
import requests
from datetime import datetime

# ========================= CONFIG =========================
st.set_page_config(
    page_title="SHIB Burn & Price Tracker",
    page_icon="🐕",
    layout="centered"
)

# JavaScript Auto-refresh every 15 seconds
st.markdown("""
    <script>
        function autoRefresh() {
            setTimeout(() => window.location.reload(), 15000);
        }
        window.onload = autoRefresh;
    </script>
""", unsafe_allow_html=True)

st.title("🐕 Shiba Inu (SHIB) Burn & Price Tracker")
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Etherscan V2")

# ================== ETHERSCAN API KEY ==================
# Get free key here: https://etherscan.io/apidashboard
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")  # Replace with your key

# SHIB Contract on Ethereum (chainid=1)
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
CHAIN_ID = 1

# Main burn addresses
BURN_ADDRESSES = [
    "0x000000000000000000000000000000000000dead",
    "0xdead000000000000000042069420694206942069"
]

def fetch_price_dexscreener():
    try:
        url = f"https://api.dexscreener.com/token-pairs/v1/ethereum/{SHIB_CONTRACT}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            best_pair = max(data, key=lambda x: x.get('liquidity', {}).get('usd', 0))
            price = float(best_pair.get('priceUsd', 0))
            return price if price > 0 else None
        return None
    except:
        return None

def fetch_supply_and_burn():
    try:
        base_url = "https://api.etherscan.io/v2/api"
        
        # 2. Burned tokens
        burned = 0
        for addr in BURN_ADDRESSES:
            bal_url = f"{base_url}?chainid={CHAIN_ID}&module=account&action=tokenbalance&contractaddress={SHIB_CONTRACT}&address={addr}&tag=latest&apikey={ETHERSCAN_API_KEY}"
            bal_resp = requests.get(bal_url, timeout=10).json()
            burned += int(bal_resp.get('result', 0))
        
        initial_supply = 1_000_000_000_000_000
        burn_percentage = burned / 100 if initial_supply > 0 else 0
        
        return {
            "burn_percentage": burn_percentage,
            "burned": burned
        }
    except Exception as e:
        st.error(f"Etherscan V2 error: {e}")
        return None

# Fetch data
price = fetch_price_dexscreener()
supply_data = fetch_supply_and_burn()

if price is not None and supply_data:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="💰 Current SHIB Price (USD)",
            value=f"${price:.8f}"
        )
    
    with col2:
        st.metric(
            label="🔥 Total Burn Percentage",
            value=f"{supply_data['burn_percentage']:.4f}%"
        )

    with col3:
        st.metric(
            label="🔥 Total Burned",
            value=f"{supply_data['burned']:.0f}"
        )

else:
    st.error("Failed to fetch data. Make sure your Etherscan API key is correct.")

st.markdown("---")
