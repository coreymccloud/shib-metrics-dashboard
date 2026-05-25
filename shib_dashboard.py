import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

st.set_page_config(page_title="🔥 SHIB Burn Dashboard", layout="centered")

st.title("🔥 SHIBA INU 24H BURN DASHBOARD")
st.markdown("**Live data from Shibburn • Powered by community trackers**")

# Sidebar
st.sidebar.header("Settings")
refresh_interval = st.sidebar.slider("Auto-refresh (seconds)", 30, 300, 60)
show_details = st.sidebar.checkbox("Show latest burns", value=True)

@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_shibburn_data():
    try:
        headers = {"User-Agent": "SHIB-Dashboard/1.0"}
        resp = requests.get("https://www.shibburn.com/", headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract 24h burn
        burn_text = None
        for elem in soup.find_all(['div', 'span', 'p', 'h']):
            if 'Last 24 Hours' in elem.get_text() or '24h' in elem.get_text().lower():
                parent = elem.parent
                if parent:
                    numbers = [t for t in parent.get_text().split() if t.replace(',', '').replace('.', '').isdigit()]
                    if numbers:
                        burn_text = numbers[0]
                        break
        
        # Fallback regex search
        import re
        match = re.search(r'Last 24 Hours.*?([\d,]+)', resp.text, re.IGNORECASE | re.DOTALL)
        if match and not burn_text:
            burn_text = match.group(1)
        
        burn_24h = int(burn_text.replace(',', '')) if burn_text else None
        
        # Price from CoinGecko
        price_resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=shiba-inu&vs_currencies=usd",
            timeout=10
        )
        price = price_resp.json().get("shiba-inu", {}).get("usd")
        
        return burn_24h, price
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return None, None

# Main display
burn_24h, price = fetch_shibburn_data()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("24H Burned", f"{burn_24h:,} SHIB" if burn_24h else "N/A")
with col2:
    usd_value = burn_24h * price if burn_24h and price else None
    st.metric("USD Value", f"${usd_value:,.2f}" if usd_value else "N/A")
with col3:
    st.metric("SHIB Price", f"${price:.8f}" if price else "N/A")

# Progress / Impact
if burn_24h:
    circulating = 585_000_000_000_000  # Approx
    impact = (burn_24h / circulating) * 100
    st.progress(impact / 0.01, text=f"Supply Impact: {impact:.6f}%")

st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

if show_details:
    st.subheader("Latest Burns (from Shibburn)")
    st.info("Check https://www.shibburn.com/burns for full live list")

# Auto-refresh
if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption("💡 Pro tip: Deploy free on Streamlit Cloud. For production use Burnalytics API (requires key).")

# Footer
st.markdown("---")
st.markdown("[Shibburn.com](https://www.shibburn.com/) • [Burnalytics](https://www.burnalytics.com/) • Data is on-chain aggregated")
