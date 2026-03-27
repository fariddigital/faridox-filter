import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Faridox Filter Pro", layout="wide", page_icon="📈")

# Dark theme is handled natively by Streamlit's settings, but we can force some styles
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    th {
        text-align: left !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Faridox Filter Pro")
st.markdown("**Small-Cap Momentum Scanner** | Identifying low-float, high-relative-volume setups.")

# --- SCANNER LOGIC ---
def analyze_ticker(ticker):
    """Fetches data and checks against Faridox Strategy Parameters."""
    try:
        stock = yf.Ticker(ticker)
        # Fetch 3 months of daily data to ensure we can calculate SMA(50) and 10-day Avg Vol
        hist = stock.history(period="3mo")
        
        if len(hist) < 50:
            return None # Not enough data for SMA 50
            
        info = stock.info
        
        # Current Day Stats
        current_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        current_low = hist['Low'].iloc[-1]
        current_high = hist['High'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        
        # Strategy Calculations
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        
        # 10-day average volume (using the previous 10 days to avoid skewing with today's incomplete volume)
        avg_vol_10 = hist['Volume'].shift(1).rolling(window=10).mean().iloc[-1]
        rel_vol = current_vol / avg_vol_10 if avg_vol_10 > 0 else 0
        
        change_pct = ((current_close - prev_close) / prev_close) * 100
        
        # Info Fetching (with fallbacks, as yfinance float data can be inconsistent)
        market_cap = info.get('marketCap', 0)
        float_shares = info.get('floatShares', info.get('sharesOutstanding', float('inf')))

        # --- FARIDOX FILTER PARAMETERS ---
        if not (1 < current_low and current_high < 20): return None
        if not (market_cap > 450_000_000): return None
        if not (current_vol > 100_000): return None
        if not (rel_vol > 2.0): return None
        if not (change_pct > 10.0): return None
        if not (current_close > sma_50): return None
        if not (float_shares < 50_000_000): return None

        return {
            "Ticker": ticker.upper(),
            "Price ($)": round(current_close, 2),
            "Change (%)": round(change_pct, 2),
            "Volume": f"{int(current_vol):,}",
            "Rel Vol": round(rel_vol, 2),
            "SMA 50": round(sma_50, 2),
            "Market Cap": f"${int(market_cap):,}",
            "Float": f"{int(float_shares):,}" if float_shares != float('inf') else "N/A"
        }
    except Exception:
        # Silently skip tickers that fail or have missing data
        return None

# --- SIDEBAR & INPUT ---
st.sidebar.header("Scanner Settings")
st.sidebar.markdown("""
**Current Parameters Active:**
* Price: $1 - $20
* Market Cap: > $450M
* Volume: > 100K
* Rel Volume: > 2
* Change %: > 10%
* Price > SMA (50)
* Float < 50M
""")

default_tickers = "MARA, RIOT, SOFI, PLTR, NIO, AMC, GME, LCID, CHPT, MVIS"
ticker_input = st.text_area("Enter Tickers to Scan (comma-separated):", value=default_tickers)

if st.button("Run Faridox Filter", type="primary"):
    # Clean up input list
    tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
    
    if not tickers:
        st.warning("Please enter at least one ticker.")
    else:
        results = []
        progress_text = "Scanning market data... Please wait."
        my_bar = st.progress(0, text=progress_text)
        
        # Asynchronous fetching to speed up yfinance
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_ticker):
                res = future.result()
                if res:
                    results.append(res)
                
                completed += 1
                my_bar.progress(completed / len(tickers), text=progress_text)
                
        my_bar.empty()
        
        # --- RESULTS DISPLAY ---
        if results:
            st.success(f"Found {len(results)} stocks matching the Faridox criteria!")
            df = pd.DataFrame(results)
            # Formatting the dataframe for cleaner display
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No stocks matched the exact Faridox criteria in this batch.")
