import streamlit as st
import requests
import re
import pandas as pd
from functools import lru_cache
from datetime import datetime

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
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Shibburn + CoinGecko + DefiLlama")

# ================== API KEYS & CONSTANTS ==================
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"

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

def fetch_burn_from_shibburn():
    try:
        url = "https://www.shibburn.com/"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SHIB-Tracker/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text
        
        # Total Burned %
        percent_match = re.search(r'(\d+\.\d+)%', html)
        burned_match = re.search(r'Total Burned[^0-9]*([\d,]+)', html.replace(',', ''))
        
        burn_percentage = float(percent_match.group(1)) if percent_match else None
        burned = int(burned_match.group(1).replace(',', '')) * 10**12 if burned_match else None
        
        # 24h Burn
        burn_24h_match = re.search(r'Last 24 Hours[^0-9]*([\d,]+)', html.replace(',', ''))
        burn_24h = int(burn_24h_match.group(1).replace(',', '')) * 10**0 if burn_24h_match else None  # usually already full number
        
        # 7d Burn
        burn_7d_match = re.search(r'Last 7 Days[^0-9]*([\d,]+)', html.replace(',', ''))
        burn_7d = int(burn_7d_match.group(1).replace(',', '')) * 10**0 if burn_7d_match else None
        
        return {
            "burn_percentage": burn_percentage,
            "burned": burned,
            "burn_24h": burn_24h,
            "burn_7d": burn_7d
        }
    except Exception as e:
        st.error(f"Burn data fetch error: {e}")
        return {"burn_percentage": None, "burned": None, "burn_24h": None, "burn_7d": None}

@lru_cache(maxsize=5)
def fetch_historical_prices(days=365):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days={days}&interval=daily"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        prices = pd.DataFrame(data.get('prices', []), columns=['timestamp', 'price'])
        market_caps = pd.DataFrame(data.get('market_caps', []), columns=['timestamp', 'market_cap'])
        
        prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms').dt.date
        market_caps['date'] = pd.to_datetime(market_caps['timestamp'], unit='ms').dt.date
        
        df = prices.merge(market_caps, on='date').drop_duplicates(subset='date').set_index('date')
        return df[['price', 'market_cap']]
    except:
        return pd.DataFrame()

def calculate_mvrv_z_score(prices: pd.Series, period: int):
    if len(prices) < max(period * 2, 30):
        return None
    mean = prices.rolling(window=period).mean().iloc[-1]
    std = prices.rolling(window=period).std().iloc[-1]
    current = prices.iloc[-1]
    if std == 0 or pd.isna(std):
        return 0.0
    z_score = (current - mean) / std
    return round(z_score, 2)

@lru_cache(maxsize=10)
def fetch_coingecko_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/shiba-inu"
        data = requests.get(url, timeout=10).json()
        return {
            "market_cap": data['market_data']['market_cap']['usd'],
            "volume_24h": data['market_data']['total_volume']['usd'],
            "price_change_24h": data['market_data']['price_change_percentage_24h']
        }
    except:
        return None

def fetch_shibarium_tvl():
    try:
        resp = requests.get("https://api.llama.fi/chains", timeout=10)
        data = resp.json()
        for chain in data:
            if chain.get('name', '').lower() == 'shibarium':
                return chain.get('tvl', 0), chain.get('change_24h', 0)
        return None, None
    except:
        return None, None

# ================== MAIN DISPLAY ==================
col1, col2, col3 = st.columns(3)

with col1:
    price = fetch_price_dexscreener()
    if price:
        st.metric("SHIB Price (USD)", f"${price:.8f}")
    else:
        st.metric("SHIB Price", "Loading...")

with col2:
    burn_data = fetch_burn_from_shibburn()
    if burn_data["burn_percentage"] is not None:
        st.metric("Total Burned %", f"{burn_data['burn_percentage']:.2f}%")
        
        # New: 24h and 7d burn rates directly under Total Burned %
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            if burn_data["burn_24h"]:
                st.metric("24h Burn", f"{burn_data['burn_24h']:,} SHIB")
        with subcol2:
            if burn_data["burn_7d"]:
                st.metric("7d Burn", f"{burn_data['burn_7d']:,} SHIB")
    else:
        st.metric("Total Burned %", "Loading...")

with col3:
    cg = fetch_coingecko_data()
    if cg:
        st.metric("24h Volume", f"${cg['volume_24h']:,.0f}", 
                 f"{cg['price_change_24h']:.1f}%")
    else:
        st.metric("24h Volume", "Loading...")

# ================== MVRV Z-SCORE SECTION ==================
st.subheader("📊 MVRV Z-Score (Price-Based Approximation)")
st.caption("True on-chain Realized Cap for ERC-20s like SHIB is not freely available. This uses rolling price statistics.")

df_hist = fetch_historical_prices(days=365)

if not df_hist.empty:
    current_mcap = df_hist['market_cap'].iloc[-1]
    st.metric("Current Market Cap", f"${current_mcap:,.0f}")
    
    periods = [3, 7, 30, 90, 180]
    cols = st.columns(len(periods))
    
    for idx, p in enumerate(periods):
        z = calculate_mvrv_z_score(df_hist['price'], p)
        with cols[idx]:
            if z is not None:
                if z > 2.0:
                    delta = "Overvalued"
                    color = "inverse"
                elif z < -1.5:
                    delta = "Undervalued"
                    color = "normal"
                else:
                    delta = "Neutral"
                    color = "normal"
                st.metric(f"{p}d Z-Score", f"{z:.2f}", delta=delta, delta_color=color)
            else:
                st.metric(f"{p}d Z-Score", "N/A")
else:
    st.warning("Could not load historical data for MVRV calculation.")

# ================== ECOSYSTEM METRICS ==================
st.subheader("🌐 Ecosystem & Activity Metrics")

tvl, tvl_24h = fetch_shibarium_tvl()
col_a, col_b, col_c = st.columns(3)

with col_a:
    if tvl is not None:
        st.metric("Shibarium TVL", f"${tvl:,.0f}", f"{tvl_24h:.1f}% 24h")
    else:
        st.metric("Shibarium TVL", "N/A")

with col_b:
    st.info("**Burn Activity**\n24h / 7d burns updated live from Shibburn")

with col_c:
    st.info("**Decision Signals**\n• Low Z-Score + Rising Burns/TVL = **Buy**\n• High Z-Score + Declining Activity = **Sell**")

st.caption("**Disclaimer**: SHIB is a high-risk meme coin. These metrics are for informational purposes only. Always DYOR and manage risk.")import streamlit as st
import requests
import re
import pandas as pd
from functools import lru_cache
from datetime import datetime

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
st.caption("🔄 Auto-refreshes every 15s • DexScreener + Shibburn + CoinGecko + DefiLlama")

# ================== API KEYS & CONSTANTS ==================
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", "S1JBXUTRAPY3WGTA5ZA4N7IRZEFVR25ZIC")
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"

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

def fetch_burn_from_shibburn():
    try:
        url = "https://www.shibburn.com/"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SHIB-Tracker/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text
        
        # Total Burned %
        percent_match = re.search(r'(\d+\.\d+)%', html)
        burned_match = re.search(r'Total Burned[^0-9]*([\d,]+)', html.replace(',', ''))
        
        burn_percentage = float(percent_match.group(1)) if percent_match else None
        burned = int(burned_match.group(1).replace(',', '')) * 10**12 if burned_match else None
        
        # 24h Burn
        burn_24h_match = re.search(r'Last 24 Hours[^0-9]*([\d,]+)', html.replace(',', ''))
        burn_24h = int(burn_24h_match.group(1).replace(',', '')) * 10**0 if burn_24h_match else None  # usually already full number
        
        # 7d Burn
        burn_7d_match = re.search(r'Last 7 Days[^0-9]*([\d,]+)', html.replace(',', ''))
        burn_7d = int(burn_7d_match.group(1).replace(',', '')) * 10**0 if burn_7d_match else None
        
        return {
            "burn_percentage": burn_percentage,
            "burned": burned,
            "burn_24h": burn_24h,
            "burn_7d": burn_7d
        }
    except Exception as e:
        st.error(f"Burn data fetch error: {e}")
        return {"burn_percentage": None, "burned": None, "burn_24h": None, "burn_7d": None}

@lru_cache(maxsize=5)
def fetch_historical_prices(days=365):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/shiba-inu/market_chart?vs_currency=usd&days={days}&interval=daily"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        prices = pd.DataFrame(data.get('prices', []), columns=['timestamp', 'price'])
        market_caps = pd.DataFrame(data.get('market_caps', []), columns=['timestamp', 'market_cap'])
        
        prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms').dt.date
        market_caps['date'] = pd.to_datetime(market_caps['timestamp'], unit='ms').dt.date
        
        df = prices.merge(market_caps, on='date').drop_duplicates(subset='date').set_index('date')
        return df[['price', 'market_cap']]
    except:
        return pd.DataFrame()

def calculate_mvrv_z_score(prices: pd.Series, period: int):
    if len(prices) < max(period * 2, 30):
        return None
    mean = prices.rolling(window=period).mean().iloc[-1]
    std = prices.rolling(window=period).std().iloc[-1]
    current = prices.iloc[-1]
    if std == 0 or pd.isna(std):
        return 0.0
    z_score = (current - mean) / std
    return round(z_score, 2)

@lru_cache(maxsize=10)
def fetch_coingecko_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/shiba-inu"
        data = requests.get(url, timeout=10).json()
        return {
            "market_cap": data['market_data']['market_cap']['usd'],
            "volume_24h": data['market_data']['total_volume']['usd'],
            "price_change_24h": data['market_data']['price_change_percentage_24h']
        }
    except:
        return None

def fetch_shibarium_tvl():
    try:
        resp = requests.get("https://api.llama.fi/chains", timeout=10)
        data = resp.json()
        for chain in data:
            if chain.get('name', '').lower() == 'shibarium':
                return chain.get('tvl', 0), chain.get('change_24h', 0)
        return None, None
    except:
        return None, None

# ================== MAIN DISPLAY ==================
col1, col2, col3 = st.columns(3)

with col1:
    price = fetch_price_dexscreener()
    if price:
        st.metric("SHIB Price (USD)", f"${price:.8f}")
    else:
        st.metric("SHIB Price", "Loading...")

with col2:
    burn_data = fetch_burn_from_shibburn()
    if burn_data["burn_percentage"] is not None:
        st.metric("Total Burned %", f"{burn_data['burn_percentage']:.2f}%")
        
        # New: 24h and 7d burn rates directly under Total Burned %
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            if burn_data["burn_24h"]:
                st.metric("24h Burn", f"{burn_data['burn_24h']:,} SHIB")
        with subcol2:
            if burn_data["burn_7d"]:
                st.metric("7d Burn", f"{burn_data['burn_7d']:,} SHIB")
    else:
        st.metric("Total Burned %", "Loading...")

with col3:
    cg = fetch_coingecko_data()
    if cg:
        st.metric("24h Volume", f"${cg['volume_24h']:,.0f}", 
                 f"{cg['price_change_24h']:.1f}%")
    else:
        st.metric("24h Volume", "Loading...")

# ================== MVRV Z-SCORE SECTION ==================
st.subheader("📊 MVRV Z-Score (Price-Based Approximation)")
st.caption("True on-chain Realized Cap for ERC-20s like SHIB is not freely available. This uses rolling price statistics.")

df_hist = fetch_historical_prices(days=365)

if not df_hist.empty:
    current_mcap = df_hist['market_cap'].iloc[-1]
    st.metric("Current Market Cap", f"${current_mcap:,.0f}")
    
    periods = [3, 7, 30, 90, 180]
    cols = st.columns(len(periods))
    
    for idx, p in enumerate(periods):
        z = calculate_mvrv_z_score(df_hist['price'], p)
        with cols[idx]:
            if z is not None:
                if z > 2.0:
                    delta = "Overvalued"
                    color = "inverse"
                elif z < -1.5:
                    delta = "Undervalued"
                    color = "normal"
                else:
                    delta = "Neutral"
                    color = "normal"
                st.metric(f"{p}d Z-Score", f"{z:.2f}", delta=delta, delta_color=color)
            else:
                st.metric(f"{p}d Z-Score", "N/A")
else:
    st.warning("Could not load historical data for MVRV calculation.")

# ================== ECOSYSTEM METRICS ==================
st.subheader("🌐 Ecosystem & Activity Metrics")

tvl, tvl_24h = fetch_shibarium_tvl()
col_a, col_b, col_c = st.columns(3)

with col_a:
    if tvl is not None:
        st.metric("Shibarium TVL", f"${tvl:,.0f}", f"{tvl_24h:.1f}% 24h")
    else:
        st.metric("Shibarium TVL", "N/A")

with col_b:
    st.info("**Burn Activity**\n24h / 7d burns updated live from Shibburn")

with col_c:
    st.info("**Decision Signals**\n• Low Z-Score + Rising Burns/TVL = **Buy**\n• High Z-Score + Declining Activity = **Sell**")

st.caption("**Disclaimer**: SHIB is a high-risk meme coin. These metrics are for informational purposes only. Always DYOR and manage risk.")
