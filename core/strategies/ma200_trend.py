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
        
        # 保存指标用于前端显示原因
        signals['MA200'] = df['MA200']
        
        return signals

    def get_action_info(self, current_row, prev_row=None, market_row=None):
        today_sig = current_row['Signal']
        prev_sig = prev_row['Signal'] if prev_row is not None else 0
        ma200 = current_row.get('MA200', 0)
        close = market_row['Close'] if market_row is not None else 0
        
        if today_sig == 1:
            action = "持仓" if prev_sig == 1 else "买入"
            reason = f"收盘价 ({close:.2f}) > MA200 ({ma200:.2f})"
        else:
            action = "空仓" if prev_sig == 0 else "卖出"
            reason = f"收盘价 ({close:.2f}) < MA200 ({ma200:.2f})"
            
        return action, reason
