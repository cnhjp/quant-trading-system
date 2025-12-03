import pandas as pd
import numpy as np
from .base import BaseStrategy

class LiquidityGrabStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Liquidity Grab (SFP)")

    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        日线: Swing Failure Pattern (SFP)。
        - 看跌 SFP: 最高价 > 昨日最高价，收盘价 < 昨日最高价 (作为平仓信号)
        - 看涨 SFP: 最低价 < 昨日最低价，收盘价 > 昨日最低价
        
        过滤条件:
        - 只做多 (Long Only)
        - 趋势过滤: 价格 > MA200 才开多; 价格 < MA200 平仓
        """
        signals = pd.DataFrame(index=df.index)
        # 使用 NaN 初始化以便于 ffill (持有状态)
        signals['Signal'] = np.nan
        
        # 计算昨日最高价/最低价 (PDH/PDL)
        df['PDH'] = df['High'].shift(1)
        df['PDL'] = df['Low'].shift(1)
        
        # 计算 MA200
        df['MA200'] = df['Close'].rolling(window=200).mean()
        
        # 买入条件: 看涨 SFP 且 价格 > MA200
        bullish_cond = (df['Low'] < df['PDL']) & (df['Close'] > df['PDL']) & (df['Close'] > df['MA200'])
        
        # 卖出条件: 看跌 SFP 或 价格跌破 MA200
        bearish_sfp = (df['High'] > df['PDH']) & (df['Close'] < df['PDH'])
        trend_break = (df['Close'] < df['MA200'])
        sell_cond = bearish_sfp | trend_break
        
        signals.loc[bullish_cond, 'Signal'] = 1
        signals.loc[sell_cond, 'Signal'] = 0
        
        # 向前填充信号 (持有仓位直到出现卖出信号)
        signals['Signal'] = signals['Signal'].ffill().fillna(0)
        
        return signals

    def get_action_info(self, current_row, prev_row=None, market_row=None):
        today_sig = current_row['Signal']
        prev_sig = prev_row['Signal'] if prev_row is not None else 0
        
        if today_sig == 1:
            action = "持仓" if prev_sig == 1 else "买入"
            if prev_sig == 0 and market_row is not None:
                reason = f"看涨SFP触发 (Low < PDL, Close > PDL), 价格 > MA200"
            else:
                reason = "持续持有看涨仓位"
        else:
            action = "空仓" if prev_sig == 0 else "卖出"
            if prev_sig == 1:
                reason = "看跌SFP或价格跌破MA200"
            else:
                reason = "无信号"
            
        return action, reason
