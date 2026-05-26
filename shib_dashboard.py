import streamlit as st
import requests
from datetime import datetime, timedelta
import re
import numpy as np
from collections import defaultdict

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

def fetch_burn_from_shibburn():
    """Fetch burn percentage and total burned from Shibburn (powered by Burnalytics)"""
    try:
        url = "https://www.shibburn.com/"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SHIB-Tracker/1.0)"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text
        
        percent_match = re.search(r'(\d+\.\d+)%', html)
        burned_match = re.search(r'Total Burned[^0-9]*([\d,]+)', html)
        
        burn_percentage = float(percent_match.group(1)) if percent_match else None
        burned_str = burned_match.group(1).replace(',', '') if burned_match else None
        burned = int(burned_str) if burned_str else None
        
        if burn_percentage is None:
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

def fetch_historical_burns(days=180):
    """Fetch approximate daily burns using Etherscan token tx (limited but works for Z-score)"""
    try:
        daily_burns = defaultdict(int)
        end_block = "latest"
        
        for addr in BURN_ADDRESSES:
            url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={SHIB_CONTRACT}&address={addr}&startblock=0&endblock={end_block}&sort=desc&apikey={ETHERSCAN_API_KEY}"
            resp = requests.get(url, timeout=15).json()
            
            if resp.get('status') == '1' and resp.get('result'):
                for tx in resp['result']:
                    ts = int(tx['timeStamp'])
                    date = datetime.fromtimestamp(ts).date()
                    value = int(tx['value']) // 10**18  # SHIB has 18 decimals
                    if date >= (datetime.now().date() - timedelta(days=days)):
                        daily_burns[date] += value
        
        # Convert to list of daily burns (sorted)
        sorted_dates = sorted(daily_burns.keys())
        burns_list = [daily_burns[d] for d in sorted_dates]
        
        return burns_list
    except:
        return []

def calculate_z_score(burns_list, period_days):
    """Calculate Z-score for recent burn vs historical mean/std for the period"""
    if len(burns_list) < period_days * 2:  # Need enough history
        return None
    
    # Recent average (last period_days)
    recent = np.mean(burns_list[-period_days:]) if burns_list else 0
    
    # Historical mean and std (excluding the most recent period to avoid bias)
    historical = burns_list[:-period_days]
    if len(historical) < 10:
        return None
    
    mean_hist = np.mean(historical)
    std_hist = np.std(historical) if np.std(historical) > 0 else 1
    
    z_score = (recent - mean_hist) / std_hist if std_hist > 0 else 0
    return round(z_score, 2)

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
    else:
        st.metric("Burned %", "Loading...")

# ================== Z-SCORE SECTION ==================
st.divider()
st.subheader("🔥 Burn Rate Z-Scores")

# Fetch historical burns once
with st.spinner("Calculating Z-Scores from historical burn data..."):
    historical_burns = fetch_historical_burns(days=180)

periods = {
    "3 Days": 3,
    "7 Days": 7,
    "30 Days": 30,
    "90 Days": 90,
    "180 Days": 180
}

z_cols = st.columns(len(periods))

for i, (label, days) in enumerate(periods.items()):
    with z_cols[i]:
        z = calculate_z_score(historical_burns, days)
        if z is not None:
            delta = "🚀 High" if z > 1.5 else "📉 Low" if z < -1.5 else "Normal"
            st.metric(label, f"{z}", delta=delta)
        else:
            st.metric(label, "—", delta="Insufficient data")

st.caption("Z-Score measures how unusual the recent burn rate is compared to history (higher = hotter burns). Data from Etherscan burn transactions.")
