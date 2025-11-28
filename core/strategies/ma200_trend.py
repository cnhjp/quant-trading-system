import pandas as pd
from .base import BaseStrategy

class MA200TrendStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("MA200 Trend")

    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        经典均线趋势策略 (The 200-Day SMA Trend Strategy)
        - 买入/持有: 收盘价 > MA200
        - 卖出/空仓: 收盘价 < MA200
        """
        signals = pd.DataFrame(index=df.index)
        signals['Signal'] = 0
        
        # 计算 MA200
        df['MA200'] = df['Close'].rolling(window=200).mean()
        
        # 信号生成
        buy_cond = df['Close'] > df['MA200']
        signals.loc[buy_cond, 'Signal'] = 1
        
        return signals
