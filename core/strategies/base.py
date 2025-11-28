from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        生成交易信号。
        返回包含 'Signal' 列的 DataFrame: 1 (买入), -1 (卖出), 0 (持仓/中性)
        """
        pass
