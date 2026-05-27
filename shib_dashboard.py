import streamlit as st
import requests
from datetime import datetime, timedelta
import time

# ========================= CONFIG =========================
st.set_page_config(
    page_title="SHIB Burn & Price Tracker",
    page_icon="🐕",
    layout="centered"
)

# Auto-refresh every 15s
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
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")

SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
CHAIN_ID = 1
INITIAL_SUPPLY = 1_000_000_000_000_000

# Expanded burn addresses (main ones from Etherscan)
BURN_ADDRESSES = [
    "0x000000000000000000000000000000000000dead",
    "0xdead000000000000000042069420694206942069",
    "0xf7a0383750fef5abace57cc4c9ff98e3790202b3",
    "0xadf86e75d8f0f57e0288d0970e7407eaa49b3cab",
    "0x556219c84974ada96e9382e041bac26398d9e214",
    "0x9813037ee2218799597d83d4a5b6f3b6778218d9",
    "0x11450058d796b02eb53e65374be59cff65d3fe7f",
    "0x27c70cd1946795b66be9d954418546998b546634",
    "0x8b3192f5eebd8579568a2ed41e6feb402f93f73f",
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

def fetch_current_supply_and_burn():
    try:
        base_url = "https://api.etherscan.io/v2/api"
        
        # Total Supply
        supply_url = f"{base_url}?chainid={CHAIN_ID}&module=stats&action=tokensupply&contractaddress={SHIB_CONTRACT}&apikey={ETHERSCAN_API_KEY}"
        supply_resp = requests.get(supply_url, timeout=10).json()
        total_supply = int(supply_resp.get('result', 0))
        
        # Current burned balance
        burned = 0
        for addr in BURN_ADDRESSES:
            bal_url = f"{base_url}?chainid={CHAIN_ID}&module=account&action=tokenbalance&contractaddress={SHIB_CONTRACT}&address={addr}&tag=latest&apikey={ETHERSCAN_API_KEY}"
            bal_resp = requests.get(bal_url, timeout=10).json()
            burned += int(bal_resp.get('result', 0))
        
        burn_percentage = (burned / INITIAL_SUPPLY) * 100 if INITIAL_SUPPLY > 0 else 0
        
        return {
            "total_supply": total_supply,
            "burned": burned,
            "burn_percentage": burn_percentage
        }
    except Exception as e:
        st.error(f"Etherscan error: {e}")
        return None

def fetch_burn_rates():
    """Fetch 24h/7d/30d burns with caching"""
    now = time.time()
    
    # Cache for 90 seconds
    if ("burn_rates_cache" in st.session_state and 
        "burn_rates_time" in st.session_state and 
        now - st.session_state.burn_rates_time < 90):
        return st.session_state.burn_rates_cache
    
    try:
        base_url = "https://api.etherscan.io/v2/api"
        periods = {
            "24h": int(now) - 86400,
            "7d": int(now) - 86400 * 7,
            "30d": int(now) - 86400 * 30
        }
        
        results = {"24h": 0, "7d": 0, "30d": 0}
        
        for addr in BURN_ADDRESSES:
            tx_url = (
                f"{base_url}?chainid={CHAIN_ID}&module=account&action=tokentx"
                f"&contractaddress={SHIB_CONTRACT}&address={addr}"
                f"&sort=desc&page=1&offset=5000&apikey={ETHERSCAN_API_KEY}"
            )
            resp = requests.get(tx_url, timeout=15).json()
            
            if resp.get("status") != "1" or not resp.get("result"):
                continue
                
            for tx in resp["result"]:
                if tx.get("to", "").lower() != addr.lower():
                    continue
                timestamp = int(tx.get("timeStamp", 0))
                value = int(tx.get("value", 0)) // 10**18  # to whole SHIB
                
                for period, cutoff in periods.items():
                    if timestamp >= cutoff:
                        results[period] += value
                    else:
                        break  # older transactions
        
        # Cache it
        st.session_state.burn_rates_cache = results
        st.session_state.burn_rates_time = now
        return results
        
    except Exception as e:
        st.warning(f"Burn rate fetch issue: {e}")
        # Fallback to zero
        return {"24h": 0, "7d": 0, "30d": 0}

# ===================== FETCH DATA =====================
price = fetch_price_dexscreener()
supply_data = fetch_current_supply_and_burn()
burn_rates = fetch_burn_rates()

if price is not None and supply_data:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Current SHIB Price", f"${price:.8f}")
    with col2:
        st.metric("🔥 Total Burned", f"{supply_data['burn_percentage']:.4f}%")

    st.divider()

    # ================= BURN RATES =================
    st.subheader("🔥 Burn Rates")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("24h Burn", f"{burn_rates['24h']:,.0f} SHIB")
    with r2:
        st.metric("7d Burn", f"{burn_rates['7d']:,.0f} SHIB")
    with r3:
        st.metric("30d Burn", f"{burn_rates['30d']:,.0f} SHIB")

    st.divider()

    st.subheader("Supply Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Supply", f"{supply_data['total_supply']:,.0f}")
    with c2:
        st.metric("Tokens Burned", f"{supply_data['burned']:,.0f}")
    with c3:
        st.metric("Circulating Supply", f"{supply_data['total_supply'] - supply_data['burned']:,.0f}")

    st.success(f"✅ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    st.caption("Price: DexScreener • Burn Data: Etherscan (multiple addresses + caching)")

else:
    st.error("Failed to fetch data. Check your Etherscan API key.")

st.markdown("---")
st.caption("Initial Supply: 1,000,000,000,000,000 SHIB")
