import pandas as pd
from .base import BaseStrategy

class VIXSwitchStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("VIX Switch")

    def generate_signals(self, df: pd.DataFrame, vix_df: pd.DataFrame = None, **kwargs) -> pd.DataFrame:
        """
        波动率控制策略 (VIX Switch)
        - 持有: VIX < VIX的50日均线
        - 空仓: VIX > VIX的50日均线
        """
        signals = pd.DataFrame(index=df.index)
        signals['Signal'] = 0
        
        if vix_df is not None:
            # 对齐 VIX 数据
            if not isinstance(vix_df.index, pd.DatetimeIndex):
                vix_df.index = pd.to_datetime(vix_df.index)
            
            vix_aligned = vix_df['Close'].reindex(df.index).ffill()
            
            # 计算 VIX MA50
            vix_ma50 = vix_aligned.rolling(window=50).mean()
            
            # 生成信号
            # VIX < MA50 -> 买入/持有 (Signal 1)
            buy_cond = vix_aligned < vix_ma50
            signals.loc[buy_cond, 'Signal'] = 1
        
        return signals
