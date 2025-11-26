import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

DATA_DIR = "data"

class DataLoader:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def fetch_data(self, ticker: str, period: str = "5y", interval: str = "1d", force_update: bool = False) -> pd.DataFrame:
        """
        从 yfinance 或本地缓存获取数据。
        
        参数:
            ticker: 股票代码 (例如 "SPY")
            period: 数据周期 (例如 "5y", "1mo")
            interval: 数据间隔 (例如 "1d", "15m")
            force_update: 是否强制更新数据 (忽略缓存)
        
        返回:
            pd.DataFrame: OHLCV 数据
        """
        # 清理输入以用于文件名
        safe_ticker = ticker.replace("^", "")
        filename = f"{safe_ticker}_{period}_{interval}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        # 检查缓存
        if not force_update and self._is_cache_valid(filepath):
            print(f"Loading {ticker} from cache...")
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            return df
        
        # 如果未缓存或已过期或强制更新，则下载
        print(f"Downloading {ticker} from yfinance...")
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            
            if df.empty:
                print(f"Warning: No data found for {ticker}")
                return pd.DataFrame()

            # 如果存在 MultiIndex 列（yfinance 更新导致），则扁平化
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 确保标准列名
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            # 保存到缓存
            df.to_csv(filepath)
            return df
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    def _is_cache_valid(self, filepath: str) -> bool:
        """检查文件是否存在且小于 24 小时。"""
        if not os.path.exists(filepath):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        if datetime.now() - file_time > timedelta(hours=24):
            return False
            
        return True

    def get_vix(self, period="5y", interval="1d"):
        """获取与主时间范围对齐的 VIX 数据辅助函数。"""
        return self.fetch_data("^VIX", period, interval)
