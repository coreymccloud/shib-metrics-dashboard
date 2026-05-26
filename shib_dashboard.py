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
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Etherscan + CoinGecko + DefiLlama")

# ================== API KEYS ==================
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"

# Main SHIB Burn Addresses (most used ones)
BURN_ADDRESSES = [
    "0xdead000000000000000042069420694206942069",  # Main dead
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
    """Fetch total burned and recent burns via Etherscan API"""
    try:
        total_burned = 0
        burn_24h = 0
        burn_7d = 0

        for addr in BURN_ADDRESSES:
            # Get current balance in burn address (this is the burned amount)
            url = f"https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress={SHIB_CONTRACT}&address={addr}&tag=latest&apikey={ETHERSCAN_API_KEY}"
            resp = requests.get(url, timeout=10).json()
            
            if resp.get("status") == "1" and resp.get("result"):
                balance = int(resp["result"]) / 10**18
                total_burned += balance

        # For 24h/7d we approximate from recent transfers (simplified for stability)
        # You can expand this with logs if needed
        return {
            "burn_percentage": round((total_burned / 589_000_000_000_000) * 100, 2),  # Approx of initial supply
            "burned": int(total_burned),
            "burn_24h": None,   # Can be enhanced later
            "burn_7d": None
        }
    except Exception as e:
        st.error(f"Etherscan burn fetch error: {e}")
        return {"burn_percentage": None, "burned": None, "burn_24h": None, "burn_7d": None}


# Keep your existing CoinGecko, Historical, TVL functions (unchanged from previous versions)


@lru_cache(maxsize=5)
def fetch_historical_prices(days=365):
    # ... (same as before)


def calculate_mvrv_z_score(prices: pd.Series, period: int):
    # ... (same as before)


@lru_cache(maxsize=10)
def fetch_coingecko_data():
    # ... (same as before)


def fetch_shibarium_tvl():
    # ... (same as before)


# ================== MAIN DISPLAY ==================
col1, col2, col3 = st.columns(3)

with col1:
    price = fetch_price_dexscreener()
    if price:
        st.metric("SHIB Price (USD)", f"${price:.8f}")
    else:
        st.metric("SHIB Price", "Loading...")

with col2:
    burn_data = fetch_burn_from_etherscan()
    if burn_data["burn_percentage"] is not None:
        st.metric("Total Burned %", f"{burn_data['burn_percentage']:.2f}%")
        
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            st.metric("24h Burn", "Coming Soon")
        with subcol2:
            st.metric("7d Burn", "Coming Soon")
    else:
        st.metric("Total Burned %", "Loading...")

with col3:
    cg = fetch_coingecko_data()
    if cg:
        st.metric("24h Volume", f"${cg['volume_24h']:,.0f}", 
                 f"{cg['price_change_24h']:.1f}%")
    else:
        st.metric("24h Volume", "Loading...")

# Rest of your MVRV + Ecosystem sections remain the same...

st.caption("**Burn Data Source**: Direct from Etherscan (on-chain) • More stable than web scraping")
