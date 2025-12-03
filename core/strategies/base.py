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

    def get_action_info(self, current_row, prev_row=None, market_row=None):
        """
        获取操作描述和原因。
        默认实现适用于标准的 0/1 信号策略。
        """
        today_sig = current_row['Signal']
        prev_sig = prev_row['Signal'] if prev_row is not None else 0
        
        action = "?"
        reason = "策略信号触发"
        
        if today_sig == 1:
            action = "持仓" if prev_sig == 1 else "买入"
        elif today_sig == -1:
             action = "卖出"
        else:
            action = "空仓" if prev_sig == 0 else "卖出"
            
        return action, reason
