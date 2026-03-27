import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures
from finvizfinance.screener.overview import Overview

st.set_page_config(page_title="Faridox Auto-Filter", layout="wide", page_icon="🚀")

st.title("🚀 Faridox Filter Pro (Auto-Mode)")
st.markdown("يقوم التطبيق الآن بسحب الأسهم تلقائياً وفلترتها بناءً على استراتيجيتك.")

def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if len(hist) < 50: return None
            
        info = stock.info
        current_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        current_vol = hist['Volume'].iloc[-1]
        
        # الحسابات الفنية
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        avg_vol_10 = hist['Volume'].shift(1).rolling(window=10).mean().iloc[-1]
        rel_vol = current_vol / avg_vol_10 if avg_vol_10 > 0 else 0
        change_pct = ((current_close - prev_close) / prev_close) * 100
        
        market_cap = info.get('marketCap', 0)
        float_shares = info.get('floatShares', 0)

        # تطبيق فلتر فريدوكس الصارم
        if not (1 < current_close < 20): return None
        if not (market_cap > 450_000_000): return None
        if not (current_vol > 100_000): return None
        if not (rel_vol > 2.0): return None
        if not (change_pct > 10.0): return None
        if not (current_close > sma_50): return None
        if not (float_shares < 50_000_000): return None

        return {
            "Ticker": ticker,
            "Price": round(current_close, 2),
            "Change %": round(change_pct, 2),
            "Rel Vol": round(rel_vol, 2),
            "Float": f"{int(float_shares/1e6)}M",
            "Market Cap": f"{int(market_cap/1e6)}M"
        }
    except: return None

if st.button("إبدأ المسح الآلي للسوق الآن", type="primary"):
    with st.spinner("جاري جلب الأسهم النشطة من السوق..."):
        try:
            # جلب قائمة أولية للأسهم الصغيرة والمتوسطة التي ارتفعت اليوم
            foverview = Overview()
            filters_dict = {
                'Market Cap.': 'Small ($300mln to $2bln)', 
                'Price': 'Under $20',
                'Change': 'Up'
            }
            foverview.set_filter(filters_dict=filters_dict)
            df_initial = foverview.screener_view()
            tickers = df_initial['Ticker'].tolist()
            
            st.info(f"تم العثور على {len(tickers)} سهم مرشح أولياً. جاري الفلترة العميقة...")
            
            results = []
            progress_bar = st.progress(0)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(analyze_ticker, t): t for t in tickers}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if res: results.append(res)
                    progress_bar.progress((i + 1) / len(tickers))
            
            if results:
                st.success(f"تم العثور على {len(results)} سهم تطابق استراتيجية فريدوكس تماماً!")
                st.table(pd.DataFrame(results))
            else:
                st.warning("لم يتم العثور على أسهم تطابق الشروط الصارمة حالياً.")
        except Exception as e:
            st.error(f"حدث خطأ في جلب البيانات: {e}")
