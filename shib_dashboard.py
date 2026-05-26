import streamlit as st
import requests
from datetime import datetime
import re
import pandas as pd
import numpy as np

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


def fetch_historical_prices(days=365):
    """Fetch historical daily prices from CoinGecko for MVRV Z-score approximation"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days={days}&interval=daily"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        prices = data.get('prices', [])
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df = df.drop_duplicates(subset='date').set_index('date')
        return df['price']
    except:
        return pd.Series()


def calculate_mvrv_z_score(prices: pd.Series, period: int):
    """Approximate MVRV Z-Score using price data over rolling periods"""
    if len(prices) < period:
        return None
    mean = prices.rolling(window=period).mean().iloc[-1]
    std = prices.rolling(window=period).std().iloc[-1]
    current_price = prices.iloc[-1]
    if std == 0:
        return 0.0
    z_score = (current_price - mean) / std
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

# ================== MVRV Z-SCORE SECTION ==================
st.subheader("📊 MVRV Z-Score (Price-Based Approximation)")
st.caption("Calculated using rolling mean & std dev of historical prices (CoinGecko)")

prices_365 = fetch_historical_prices(days=365)  # Fetch enough history

if not prices_365.empty:
    periods = [3, 7, 30, 90, 180]
    z_scores = {}
    
    for p in periods:
        z = calculate_mvrv_z_score(prices_365, p)
        z_scores[p] = z
    
    # Display in columns
    cols = st.columns(len(periods))
    for idx, p in enumerate(periods):
        z = z_scores[p]
        if z is not None:
            delta = "Overvalued" if z > 2 else "Undervalued" if z < -2 else "Neutral"
            cols[idx].metric(f"{p}d MVRV Z", f"{z}", delta=delta)
        else:
            cols[idx].metric(f"{p}d MVRV Z", "N/A")
else:
    st.warning("Could not fetch historical price data for MVRV Z-score calculation.")
