import pandas as pd
import numpy as np
from .base import BaseStrategy

class TrendConfluenceStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Trend Confluence")

    def generate_signals(self, df: pd.DataFrame, vix_df: pd.DataFrame = None, **kwargs) -> pd.DataFrame:
        """
        趋势共振 (Trend Confluence):
        - 价格 > 锚定 VWAP (日线数据使用月度锚定)
        - VIX < MA20
        
        过滤条件:
        - 只做多 (Long Only)
        """
        signals = pd.DataFrame(index=df.index)
        signals['Signal'] = np.nan
        
        # 1. 计算 VWAP (日线数据的月度锚定)
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TPV'] = df['TP'] * df['Volume']
        
        grouper = df.index.to_period('M')
        
        df['CumTPV'] = df.groupby(grouper)['TPV'].cumsum()
        df['CumVol'] = df.groupby(grouper)['Volume'].cumsum()
        df['VWAP'] = df['CumTPV'] / df['CumVol']
        
        # 2. VIX 过滤
        if vix_df is not None:
            vix_aligned = vix_df['Close'].reindex(df.index).ffill()
            vix_ma20 = vix_aligned.rolling(window=20).mean()
            vix_cond = vix_aligned < vix_ma20
        else:
            vix_cond = True
            
        # 3. 生成信号
        # 当 价格 > VWAP 且 VIX < MA20 时买入
        # 当 价格 < VWAP 时平仓 (不做空)
        
        buy_cond = (df['Close'] > df['VWAP']) & vix_cond
        sell_cond = (df['Close'] < df['VWAP'])
        
        signals.loc[buy_cond, 'Signal'] = 1
        signals.loc[sell_cond, 'Signal'] = 0 
        
        # 向前填充信号 (持有仓位直到出现卖出信号)
        signals['Signal'] = signals['Signal'].ffill().fillna(0)
        
        return signals
