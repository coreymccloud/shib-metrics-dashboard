import streamlit as st
import requests
from datetime import datetime
import time

# ========================= CONFIG =========================
st.set_page_config(
    page_title="SHIB Burn & Price Tracker",
    page_icon="🐕",
    layout="centered"
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
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Burnalytics")

# ================== API KEYS ==================
BURNALYTICS_API_KEY = st.secrets.get("BURNALYTICS_API_KEY", "")  # Add this in Streamlit secrets
ETHERSCAN_FALLBACK = False  # Removed Etherscan as requested

SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
CHAIN_ID = 1
INITIAL_SUPPLY = 1_000_000_000_000_000

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

def fetch_burnalytics_stats():
    """Main stats: total burned + percentage"""
    if not BURNALYTICS_API_KEY:
        st.error("Burnalytics API key is missing. Add `BURNALYTICS_API_KEY` to Streamlit secrets.")
        return None
    
    try:
        url = f"https://www.burnalytics.com/api/v1/chain/{CHAIN_ID}/token/{SHIB_CONTRACT}/stats"
        headers = {"X-API-Key": BURNALYTICS_API_KEY}
        resp = requests.get(url, headers=headers, timeout=12)
        data = resp.json()
        
        total_burned = int(data.get("total_burned", 0))
        burn_percentage = (total_burned / INITIAL_SUPPLY) * 100
        
        return {
            "total_burned": total_burned,
            "burn_percentage": burn_percentage
        }
    except Exception as e:
        st.error(f"Burnalytics stats error: {e}")
        return None

def fetch_burnalytics_burn_rates():
    """24h, 7d, 30d burn amounts using chart endpoints"""
    if not BURNALYTICS_API_KEY:
        return {"24h": 0, "7d": 0, "30d": 0}
    
    try:
        rates = {}
        headers = {"X-API-Key": BURNALYTICS_API_KEY}
        
        for period in ["24h", "7d", "30d"]:
            url = f"https://www.burnalytics.com/api/v1/chain/{CHAIN_ID}/token/{SHIB_CONTRACT}/chart/{period}"
            resp = requests.get(url, headers=headers, timeout=12)
            data = resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                # Sum amounts across the period (in raw wei)
                total = sum(int(item.get("amount", 0)) for item in data)
                rates[period] = total // 10**18  # Convert to whole SHIB
            else:
                rates[period] = 0
                
        return rates
    except Exception as e:
        st.warning(f"Burnalytics burn rates error: {e}")
        return {"24h": 0, "7d": 0, "30d": 0}

# ===================== FETCH DATA =====================
price = fetch_price_dexscreener()
burn_stats = fetch_burnalytics_stats()
burn_rates = fetch_burnalytics_burn_rates()

st.write("Burnalytics Key Loaded:", "✅ Yes" if st.secrets.get("BURNALYTICS_API_KEY") else "❌ No")
st.metric("BURNALYTICS_API_KEY")

if price is not None and burn_stats:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Current SHIB Price (USD)", f"${price:.8f}")
    with col2:
        st.metric("🔥 Total Burned", f"{burn_stats['burn_percentage']:.4f}%")

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
        st.metric("Initial Supply", f"{INITIAL_SUPPLY:,.0f}")
    with c2:
        st.metric("Tokens Burned", f"{burn_stats['total_burned']:,.0f}")
    with c3:
        st.metric("Remaining Supply", f"{INITIAL_SUPPLY - burn_stats['total_burned']:,.0f}")

    st.success(f"✅ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    st.caption("• Price: DexScreener • Burn Data: Burnalytics API")

else:
    st.error("Failed to fetch data. Check your Burnalytics API key and internet connection.")

st.markdown("---")
st.caption("Initial Supply: 1,000,000,000,000,000 SHIB | Powered by Burnalytics")
