import streamlit as st
import requests
from datetime import datetime
import re

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
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Shibburn")

# ================== ETHERSCAN API KEY (still needed for other features if you keep them) ==================
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")

# SHIB Contract on Ethereum (chainid=1)
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
CHAIN_ID = 1

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

def fetch_burn_from_shibburn():
    """Fetch burn percentage and total burned from Shibburn (powered by Burnalytics)"""
    try:
        # Shibburn.com displays the data directly
        url = "https://www.shibburn.com/"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SHIB-Tracker/1.0)"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text
        
        # Look for Total Burned percentage (e.g. "41.08%")
        percent_match = re.search(r'(\d+\.\d+)%', html)
        burned_match = re.search(r'Total Burned[^0-9]*([\d,]+)', html.replace(',', ''))
        
        burn_percentage = float(percent_match.group(1)) if percent_match else None
        burned_str = burned_match.group(1) if burned_match else None
        burned = int(burned_str.replace(',', '')) * 10**12 if burned_str else None  # rough parse, adjust if needed
        
        if burn_percentage is None:
            # Fallback: try Burnalytics asset page
            url2 = f"https://www.burnalytics.com/asset/{SHIB_CONTRACT}"
            resp2 = requests.get(url2, headers=headers, timeout=10)
            html2 = resp2.text
            percent_match2 = re.search(r'(\d+\.\d+)%', html2)
            if percent_match2:
                burn_percentage = float(percent_match2.group(1))
        
        return {
            "burn_percentage": burn_percentage,
            "burned": burned
        }
    except Exception as e:
        st.error(f"Shibburn fetch error: {e}")
        return {"burn_percentage": None, "burned": None}

# ================== MAIN DISPLAY ==================
col1, col2 = st.columns(2)

with col1:
    price = fetch_price_dexscreener()
    if price:
        st.metric("SHIB Price (USD)", f"${price:.8f}")
    else:
        st.metric("SHIB Price", "Loading...")

with col2:
    burn_data = fetch_burn_from_shibburn()
    if burn_data["burn_percentage"] is not None:
        st.metric("Burned %", f"{burn_data['burn_percentage']:.2f}%")
        if burn_data["burned"]:
            st.caption(f"Total Burned: {burn_data['burned']:,} SHIB")
    else:
        st.metric("Burned %", "Loading...")

st.divider()

st.info("💡 Burn data is now sourced from Shibburn.com (the community standard tracker).")
