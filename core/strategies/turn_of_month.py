import pandas as pd
from .base import BaseStrategy

class TurnOfTheMonthStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Turn of the Month")

    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        月底效应策略 (Turn of the Month)
        - 买入: 月底倒数第4个交易日收盘
        - 卖出: 下月初第3个交易日收盘
        - 逻辑: 在每个月的最后4个交易日和前3个交易日持有仓位
        """
        signals = pd.DataFrame(index=df.index)
        signals['Signal'] = 0
        
        # 确保索引是 DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # 按年-月分组
        grouper = df.groupby(df.index.to_period('M'))
        
        for name, group in grouper:
            days = group.index
            if len(days) >= 7:
                # 月底最后4天
                last_4 = days[-4:]
                # 月初前3天
                first_3 = days[:3]
                
                signals.loc[last_4, 'Signal'] = 1
                signals.loc[first_3, 'Signal'] = 1
                
        return signals
