import streamlit as st
import requests
import pandas as pd
from functools import lru_cache

# ========================= CONFIG =========================
st.set_page_config(
    page_title="SHIB Burn & Price Tracker",
    page_icon="🐕",
    layout="wide"
)

# Auto-refresh every 15 seconds
st.markdown("""
    <script>
        function autoRefresh() {
            setTimeout(() => window.location.reload(), 15000);
        }
        window.onload = autoRefresh;
    </script>
""", unsafe_allow_html=True)

st.title("🐕 Shiba Inu (SHIB) Burn & Price Tracker")
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Etherscan (On-Chain) + CoinGecko + DefiLlama")

# ================== API KEYS & CONSTANTS ==================
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"

# Main Burn Addresses (on-chain dead wallets)
BURN_ADDRESSES = [
    "0xdead000000000000000042069420694206942069",  # Primary dead
    "0x000000000000000000000000000000000000dead",  # Null
    "0x0000000000000000000000000000000000000000",  # Zero
]

# ================== FETCH FUNCTIONS ==================
def fetch_price_dexscreener():
    try:
        url = f"https://api.dexscreener.com/token-pairs/v1/ethereum/{SHIB_CONTRACT}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            best_pair = max(data, key=lambda x: x.get('liquidity', {}).get('usd', 0))
            return float(best_pair.get('priceUsd', 0))
        return None
    except:
        return None


def fetch_burn_from_etherscan():
    """On-chain burn data from Etherscan (most reliable)"""
    try:
        total_burned = 0.0

        for addr in BURN_ADDRESSES:
            url = (
                f"https://api.etherscan.io/api"
                f"?module=account"
                f"&action=tokenbalance"
                f"&contractaddress={SHIB_CONTRACT}"
                f"&address={addr}"
                f"&tag=latest"
                f"&apikey={ETHERSCAN_API_KEY}"
            )
            resp = requests.get(url, timeout=12).json()
            
            if resp.get("status") == "1" and resp.get("result"):
                balance = int(resp["result"]) / 1e18  # SHIB has 18 decimals
                total_burned += balance

        # Approximate percentage
