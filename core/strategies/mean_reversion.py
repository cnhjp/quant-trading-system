import pandas as pd
import numpy as np
from .base import BaseStrategy

class MeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Mean Reversion (RSI)")

    def generate_signals(self, df: pd.DataFrame, period=14, **kwargs) -> pd.DataFrame:
        """
        均值回归 (RSI):
        - 买入: RSI < 45 (优化参数) 且 价格 > MA200 (趋势过滤)
        - 卖出: RSI > 70 (平仓)
        - 只做多
        """
        signals = pd.DataFrame(index=df.index)
        # 使用 NaN 初始化以便于 ffill
        signals['Signal'] = np.nan
        
        # 计算 RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 计算 MA200
        df['MA200'] = df['Close'].rolling(window=200).mean()
        
        # 信号
        # 优化: RSI 阈值从 30 提高到 45
        # 过滤: 增加 MA200 趋势过滤 (入场和出场)
        buy_cond = (df['RSI'] < 45) & (df['Close'] > df['MA200'])
        sell_cond = (df['RSI'] > 70) | (df['Close'] < df['MA200'])
        
        signals.loc[buy_cond, 'Signal'] = 1  # 买入
        signals.loc[sell_cond, 'Signal'] = 0 # 平仓
        
        # 向前填充信号 (持有仓位直到出现卖出信号)
        signals['Signal'] = signals['Signal'].ffill().fillna(0)
        
        return signals

    def get_action_info(self, current_row, prev_row=None, market_row=None):
        today_sig = current_row['Signal']
        prev_sig = prev_row['Signal'] if prev_row is not None else 0
        
        if today_sig == 1:
            action = "持仓" if prev_sig == 1 else "买入"
            if prev_sig == 0 and market_row is not None:
                rsi = market_row.get('RSI', 0)
                reason = f"RSI ({rsi:.1f}) < 45 且价格 > MA200 (超卖反弹)"
            else:
                reason = "持续持有均值回归仓位"
        else:
            action = "空仓" if prev_sig == 0 else "卖出"
            if prev_sig == 1:
                reason = "RSI > 70 或价格跌破MA200"
            else:
                reason = "无信号"
            
        return action, reason
