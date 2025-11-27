import os
from datetime import datetime
from core.data_loader import DataLoader
from config.settings import TICKER_MAP

def update_data():
    print(f"[{datetime.now()}] Starting daily data update...")
    
    # Ensure data directory exists
    if not os.path.exists("data"):
        os.makedirs("data")
        
    loader = DataLoader()
    
    # Update all tickers in map
    for name, ticker in TICKER_MAP.items():
        print(f"Updating {name} ({ticker})...")
        try:
            # Force update with a long period (5y)
            loader.fetch_data(ticker, period="5y", interval="1d", force_update=True)
            print(f"Successfully updated {ticker}")
        except Exception as e:
            print(f"Failed to update {ticker}: {e}")
            
    # Update VIX
    print("Updating VIX...")
    try:
        loader.get_vix(period="5y", interval="1d", force_update=True)
        print("Successfully updated VIX")
    except Exception as e:
        print(f"Failed to update VIX: {e}")
        
    print(f"[{datetime.now()}] Data update process completed.")

if __name__ == "__main__":
    update_data()
