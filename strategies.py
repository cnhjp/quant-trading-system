import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

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
        signals['Signal'] = 0
        
        # 1. 计算 VWAP (日线数据的月度锚定)
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TPV'] = df['TP'] * df['Volume']
        
        grouper = df.index.to_period('M')
        
        df['CumTPV'] = df.groupby(grouper)['TPV'].cumsum()
        df['CumVol'] = df.groupby(grouper)['Volume'].cumsum()
        df['VWAP'] = df['CumTPV'] / df['CumVol']
        
        # 2. VIX 过滤
        if vix_df is not None:
            vix_aligned = vix_df['Close'].reindex(df.index).fillna(method='ffill')
            vix_ma20 = vix_aligned.rolling(window=20).mean()
            vix_cond = vix_aligned < vix_ma20
        else:
            vix_cond = True
            
        # 3. 生成信号
        # 当 价格 > VWAP 且 VIX < MA20 时买入
        # 当 价格 < VWAP 时平仓 (不做空)
        # 这里不需要 ffill，因为条件是连续覆盖的
        
        buy_cond = (df['Close'] > df['VWAP']) & vix_cond
        sell_cond = (df['Close'] < df['VWAP'])
        
        signals.loc[buy_cond, 'Signal'] = 1
        signals.loc[sell_cond, 'Signal'] = 0 
        
        return signals

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
