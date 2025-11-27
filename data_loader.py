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

    def _get_period_days(self, period: str) -> int:
        """将周期字符串转换为大致天数，用于比较。"""
        mapping = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180,
            'ytd': 200, '1y': 365, '2y': 730, '5y': 1825, '10y': 3650, 'max': 99999
        }
        return mapping.get(period, 0)

    def fetch_data(self, ticker: str, period: str = "5y", interval: str = "1d", force_update: bool = False) -> pd.DataFrame:
        """
        从 yfinance 或本地缓存获取数据。
        优化逻辑：优先使用已存在的更长周期数据，并清理较短周期的冗余文件。
        """
        safe_ticker = ticker.replace("^", "")
        requested_days = self._get_period_days(period)
        
        # 1. 扫描现有的该标的、该间隔的所有文件
        existing_files = []
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.startswith(f"{safe_ticker}_") and f.endswith(f"_{interval}.csv"):
                    # 解析周期: safe_ticker_PERIOD_interval.csv
                    # 注意 safe_ticker 可能包含 _ (如无)，但通常 ticker 不含 _
                    # 格式: {safe_ticker}_{period}_{interval}.csv
                    # 我们可以用 split('_')，但要注意 ticker 本身
                    # 更稳妥的方法是去掉前缀后缀
                    prefix = f"{safe_ticker}_"
                    suffix = f"_{interval}.csv"
                    if f.startswith(prefix) and f.endswith(suffix):
                        p_str = f[len(prefix):-len(suffix)]
                        p_days = self._get_period_days(p_str)
                        existing_files.append({'file': f, 'period': p_str, 'days': p_days, 'path': os.path.join(self.data_dir, f)})
        
        # 按天数降序排列 (最长的在前面)
        existing_files.sort(key=lambda x: x['days'], reverse=True)
        
        target_file_info = None
        
        # 2. 检查是否有满足要求的缓存 (周期 >= 请求周期 且 未过期)
        # 如果 force_update 为 True，则跳过缓存检查，直接下载
        if not force_update:
            for info in existing_files:
                if info['days'] >= requested_days:
                    if self._is_cache_valid(info['path']):
                        target_file_info = info
                        break # 找到满足条件的最长（或足够长）的有效文件
        
        df = pd.DataFrame()
        
        # 3. 如果找到合适的缓存，直接使用
        if target_file_info:
            print(f"Loading {ticker} from cache ({target_file_info['period']})...")
            df = pd.read_csv(target_file_info['path'], index_col=0, parse_dates=True)
            
            # 裁剪数据到请求的周期
            if target_file_info['period'] != period:
                start_date = pd.Timestamp.now() - pd.Timedelta(days=requested_days + 5) # 多留几天缓冲
                if period == 'ytd':
                    start_date = pd.Timestamp(f"{pd.Timestamp.now().year}-01-01")
                elif period == 'max':
                    start_date = pd.Timestamp.min
                
                df = df[df.index >= start_date]
        
        else:
            # 4. 否则，下载数据
            # 为了最大化利用存储，如果现有的最长文件已经失效，或者根本没有足够长的文件
            # 我们应该下载什么？
            # 用户策略：如果存在更久的数据，直接使用。
            # 如果我们需要下载，是否应该下载更长的？
            # 简单起见，下载请求的周期。但如果之前有 10y 的（失效了），最好还是更新 10y 的。
            # 策略：如果存在任何文件，取其中最长的周期作为下载目标（如果它比请求的还长）。
            # 否则使用请求的周期。
            
            download_period = period
            if existing_files:
                longest_existing = existing_files[0]
                if longest_existing['days'] > requested_days:
                    download_period = longest_existing['period']
            
            print(f"Downloading {ticker} from yfinance (period={download_period})...")
            try:
                df = yf.download(ticker, period=download_period, interval=interval, progress=False)
                
                if not df.empty:
                    # 处理 MultiIndex
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                    
                    # 保存文件
                    new_filename = f"{safe_ticker}_{download_period}_{interval}.csv"
                    new_filepath = os.path.join(self.data_dir, new_filename)
                    df.to_csv(new_filepath)
                    
                    # 更新 target_file_info 以便后续清理
                    target_file_info = {'file': new_filename, 'period': download_period, 'days': self._get_period_days(download_period), 'path': new_filepath}
                    
                    # 如果下载的是更长周期，需要裁剪返回给用户
                    if download_period != period:
                        start_date = pd.Timestamp.now() - pd.Timedelta(days=requested_days + 5)
                        if period == 'ytd':
                            start_date = pd.Timestamp(f"{pd.Timestamp.now().year}-01-01")
                        elif period == 'max':
                            start_date = pd.Timestamp.min
                        df = df[df.index >= start_date]
                        
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                return pd.DataFrame()

        # 5. 清理较短的冗余文件
        # 规则：保留最长的一个文件。如果当前使用的文件就是最长的，删除其他所有比它短的。
        # 重新扫描（因为可能刚下载了新文件）
        current_files = []
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.startswith(f"{safe_ticker}_") and f.endswith(f"_{interval}.csv"):
                    prefix = f"{safe_ticker}_"
                    suffix = f"_{interval}.csv"
                    if f.startswith(prefix) and f.endswith(suffix):
                        p_str = f[len(prefix):-len(suffix)]
                        p_days = self._get_period_days(p_str)
                        current_files.append({'file': f, 'path': os.path.join(self.data_dir, f), 'days': p_days})
        
        # 找到最长的文件
        if current_files:
            current_files.sort(key=lambda x: x['days'], reverse=True)
            longest_file = current_files[0]
            
            # 删除所有其他文件
            for f_info in current_files[1:]:
                try:
                    os.remove(f_info['path'])
                    print(f"Deleted redundant file: {f_info['file']}")
                except OSError as e:
                    print(f"Error deleting file {f_info['file']}: {e}")

        return df

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
