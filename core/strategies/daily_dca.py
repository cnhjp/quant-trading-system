import pandas as pd
from .base import BaseStrategy

class DailyDCAStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Daily DCA")

    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        每日定投 (Daily DCA): 总是买入。
        """
        signals = pd.DataFrame(index=df.index)
        signals['Signal'] = 1 # 总是买入
        return signals
