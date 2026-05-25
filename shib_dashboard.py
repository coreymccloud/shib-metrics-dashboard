import requests
import time
from datetime import datetime, timedelta
import os

# ============== CONFIG ==============
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "YourFreeEtherscanAPIKeyHere")  # Get free at https://etherscan.io/apis
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
# Main burn addresses (dead / null)
BURN_ADDRESSES = [
    "0xdead000000000000000042069420694206942069",
    "0x000000000000000000000000000000000000dead",
    # Add more if needed from Shibburn
]

# =====================================

def get_current_shib_price():
    """Live SHIB price in USD via CoinGecko (free, no key)"""
    try:
        resp = requests.get(
            COINGECKO_API,
            params={"ids": "shiba-inu", "vs_currencies": "usd"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data["shiba-inu"]["usd"]
    except Exception as e:
        print(f"⚠️ Price fetch failed: {e}")
        return None

def get_24h_burn_amount():
    """
    Fetch SHIB transfers to burn addresses in the last ~24 hours using Etherscan.
    Note: Etherscan free tier has rate limits (~5 calls/sec, 100k results/day).
    """
    total_burned = 0
    one_day_ago = int((datetime.utcnow() - timedelta(days=1)).timestamp())
    
    for burn_addr in BURN_ADDRESSES:
        try:
            url = (
                f"https://api.etherscan.io/api"
                f"?module=account"
                f"&action=tokentx"
                f"&contractaddress={SHIB_CONTRACT}"
                f"&address={burn_addr}"
                f"&startblock=0"
                f"&endblock=99999999"
                f"&sort=desc"
                f"&apikey={ETHERSCAN_API_KEY}"
            )
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data["status"] != "1" or not data.get("result"):
                continue
                
            for tx in data["result"]:
                # Filter by time (timestamp in Unix seconds)
                if int(tx["timeStamp"]) < one_day_ago:
                    break  # Since sorted desc, we can stop early
                
                # Value is in smallest unit (18 decimals for SHIB)
                value = int(tx["value"]) / 10**18
                total_burned += value
                
        except Exception as e:
            print(f"Error querying burn address {burn_addr}: {e}")
    
    return int(total_burned)  # Return whole tokens

def display_live_burn_info():
    print("=" * 70)
    print("🔥 SHIBA INU (SHIB) 24-HOUR BURN TRACKER - LIVE")
    print("=" * 70)
    print(f"Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    price = get_current_shib_price()
    burn_amount = get_24h_burn_amount()
    
    if burn_amount is not None:
        print(f"24-Hour Tokens Burned : {burn_amount:,} SHIB")
        
        if price:
            usd_value = burn_amount * price
            print(f"Approximate USD Value  : ${usd_value:,.2f} (@ ${price:.8f})")
        else:
            print("USD Value: (price fetch unavailable)")
    else:
        print("❌ Failed to fetch burn data")
    
    print("\n💡 Note: This sums transfers to known dead addresses.")
    print("   For more precision, consider Burnalytics paid API.")
    print("\nLive Tracker: https://www.shibburn.com/")
    print("=" * 70)

if __name__ == "__main__":
    display_live_burn_info()
    
    # Optional: Refresh every hour
    # while True:
    #     display_live_burn_info()
    #     time.sleep(3600)
