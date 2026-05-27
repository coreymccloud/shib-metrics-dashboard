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
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")

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
        
        initial_supply = 1_000_000_000_000_000
        burn_percentage = (burned / initial_supply) * 100 if initial_supply > 0 else 0
        
        return {
            "total_supply": total_supply,
            "burned": burned,
            "burn_percentage": burn_percentage
        }
    except Exception as e:
        st.error(f"Etherscan V2 error: {e}")
        return None

def fetch_burn_rates():
    """Fetch 24h, 7d, and 30d burned amounts using tokentx API"""
    try:
        base_url = "https://api.etherscan.io/v2/api"
        now = int(time.time())
        
        periods = {
            "24h": now - 86400,
            "7d": now - 86400 * 7,
            "30d": now - 86400 * 30
        }
        
        results = {"24h": 0, "7d": 0, "30d": 0}
        
        for addr in BURN_ADDRESSES:
            # Fetch recent token transfers TO this burn address (burns)
            # offset=10000 should cover way more than 30 days for burns
            tx_url = (
                f"{base_url}?chainid={CHAIN_ID}&module=account&action=tokentx"
                f"&contractaddress={SHIB_CONTRACT}&address={addr}"
                f"&sort=desc&page=1&offset=10000&apikey={ETHERSCAN_API_KEY}"
            )
            resp = requests.get(tx_url, timeout=15).json()
            
            if resp.get("status") != "1" or not resp.get("result"):
                continue
                
            tx_list = resp["result"]
            
            for tx in tx_list:
                # Only count transfers INTO the burn address (from != burn)
                if tx.get("to", "").lower() != addr.lower():
                    continue
                    
                timestamp = int(tx.get("timeStamp", 0))
                value = int(tx.get("value", 0))  # raw (18 decimals)
                
                for period_name, cutoff in periods.items():
                    if timestamp >= cutoff:
                        results[period_name] += value
                    else:
                        # Since sorted desc (newest first), we can break early for this address
                        break
                        
        # Convert from wei (18 decimals) to whole SHIB
        for k in results:
            results[k] = results[k] // 10**18
            
        return results
        
    except Exception as e:
        st.warning(f"Could not fetch burn rates: {e}")
        return {"24h": 0, "7d": 0, "30d": 0}

# ===================== FETCH DATA =====================
price = fetch_price_dexscreener()
supply_data = fetch_supply_and_burn()
burn_rates = fetch_burn_rates()

if price is not None and supply_data:
    col1, col2 = st.columns(2)
    
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

    st.divider()

    # ================= BURN RATES SECTION =================
    st.subheader("🔥 Burn Rates")
    col_r1, col_r2, col_r3 = st.columns(3)
    
    with col_r1:
        st.metric(
            label="24h Burn",
            value=f"{burn_rates['24h']:,.0f} SHIB",
            delta=None
        )
    with col_r2:
        st.metric(
            label="7d Burn",
            value=f"{burn_rates['7d']:,.0f} SHIB",
            delta=None
        )
    with col_r3:
        st.metric(
            label="30d Burn",
            value=f"{burn_rates['30d']:,.0f} SHIB",
            delta=None
        )

    st.divider()

    st.subheader("Supply & Burn Details")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total Supply", f"{supply_data['total_supply']:,.0f}")
    with col_b:
        st.metric("Tokens Burned (Total)", f"{supply_data['burned']:,.0f}")
    with col_c:
        st.metric("Remaining Supply", f"{supply_data['total_supply'] - supply_data['burned']:,.0f}")

    st.success(f"✅ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("Price: DexScreener • Supply & Burn: Etherscan API V2 (on-chain)")

else:
    st.error("Failed to fetch data. Make sure your Etherscan API key is correct.")

st.markdown("---")
st.caption("Initial Supply: 1,000,000,000,000,000 SHIB")
