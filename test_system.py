from data_loader import DataLoader
from strategies import LiquidityGrabStrategy, TrendConfluenceStrategy
from backtester import Backtester
import pandas as pd

def test_system():
    print("Initializing...")
    dl = DataLoader()
    bt = Backtester()
    
    ticker = "SPY"
    print(f"Fetching data for {ticker}...")
    df = dl.fetch_data(ticker, period="1y", interval="1d")
    
    if df.empty:
        print("Error: No data fetched.")
        return

    print(f"Data fetched: {len(df)} rows")
    print(df.head())
    
    # Test Strategy A
    print("\nTesting Liquidity Grab Strategy...")
    strat_a = LiquidityGrabStrategy()
    signals_a = strat_a.generate_signals(df)
    print("Signals generated:")
    print(signals_a['Signal'].value_counts())
    
    # Test Backtest
    print("\nRunning Backtest...")
    results = bt.run_backtest(df, signals_a)
    metrics = bt.calculate_metrics(results)
    print("Metrics:", metrics)
    print("Results Head:")
    print(results[['Close', 'Signal', 'Position', 'NextOpen', 'Strategy_Return', 'Equity']].head(10))

if __name__ == "__main__":
    test_system()
