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

class PyramidGridStrategy(BaseStrategy):
    def __init__(self):
        """
        高级金字塔网格策略 (Advanced Pyramid Grid Strategy)
        
        资金分配:
        - 20% 底仓 (Core Position)
        - 60% 网格子弹 (Grid Capital)
        - 20% 备用金 (Reserve)
        
        网格层级:
        - Level 0: 初始底仓 20%
        - Level 1: 跌5% + RSI<40 -> 买入10%
        - Level 2: 再跌8% -> 买入15%
        - Level 3: 再跌12% -> 买入15%
        - Level 4: 再跌15% -> 买入20%
        
        止盈逻辑:
        - 上涨5% -> 卖出最近一笔的80% (LIFO)
        - 留存20%转为底仓
        """
        super().__init__("Pyramid Grid")
        
        # 资金分配
        self.core_ratio = 0.20      # 底仓比例
        self.grid_ratio = 0.60      # 网格子弹
        self.reserve_ratio = 0.20   # 备用金
        
        # 网格层级配置 [跌幅%, 买入比例%]
        self.grid_levels = [
            {'level': 0, 'drop': 0.00, 'buy': 0.20, 'rsi_filter': False},   # 初始底仓
            {'level': 1, 'drop': 0.05, 'buy': 0.10, 'rsi_filter': True},    # RSI<40
            {'level': 2, 'drop': 0.08, 'buy': 0.15, 'rsi_filter': False},
            {'level': 3, 'drop': 0.12, 'buy': 0.15, 'rsi_filter': False},
            {'level': 4, 'drop': 0.15, 'buy': 0.20, 'rsi_filter': False}
        ]
        
        # 止盈参数
        self.profit_trigger = 0.05   # 5%止盈
        self.sell_ratio = 0.80       # 卖出80%
        self.retain_ratio = 0.20     # 留存20%
    
    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        生成金字塔网格交易信号
        
        返回:
            包含 'Signal', 'BuyLevel', 'BuyAmount', 'SellRatio' 的 DataFrame
        """
        signals = pd.DataFrame(index=df.index)
        signals['Signal'] = 0
        signals['BuyLevel'] = -1     # 买入层级 (-1表示无买入)
        signals['BuyAmount'] = 0.0   # 买入金额比例
        signals['SellRatio'] = 0.0   # 卖出比例 (针对最近一笔)
        
        # 计算 RSI (用于 Level 1 过滤)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 追踪变量
        avg_cost = None          # 持仓均价
        last_buy_price = None    # 最近一次买入价
        last_buy_level = -1      # 最近一次买入层级
        current_level = -1       # 当前已达到的最高层级
        
        for i in range(len(df)):
            current_price = df['Close'].iloc[i]
            current_rsi = df['RSI'].iloc[i] if not pd.isna(df['RSI'].iloc[i]) else 50
            
            # Level 0: 第一天建仓
            if i == 0:
                signals.iloc[i, signals.columns.get_loc('Signal')] = 1
                signals.iloc[i, signals.columns.get_loc('BuyLevel')] = 0
                signals.iloc[i, signals.columns.get_loc('BuyAmount')] = self.grid_levels[0]['buy']
                avg_cost = current_price
                last_buy_price = current_price
                last_buy_level = 0
                current_level = 0
                continue
            
            # 检查止盈条件 (上涨5%)
            if last_buy_price is not None and last_buy_level > 0:  # 不卖Level 0底仓
                profit_pct = (current_price - last_buy_price) / last_buy_price
                if profit_pct >= self.profit_trigger:
                    # 触发止盈：卖出最近一笔的80%
                    signals.iloc[i, signals.columns.get_loc('Signal')] = -1
                    signals.iloc[i, signals.columns.get_loc('SellRatio')] = self.sell_ratio
                    # 重置last_buy_price，避免重复触发
                    last_buy_price = None
                    last_buy_level = -1
                    continue
            
            # 检查加仓条件 (相对持仓均价下跌)
            if avg_cost is not None:
                # 遍历网格层级 (从Level 1开始，跳过Level 0)
                for level_config in self.grid_levels[1:]:
                    level = level_config['level']
                    
                    # 确保不重复买入同一层级
                    if level <= current_level:
                        continue
                    
                    # 计算相对前一层级的跌幅
                    if level == 1:
                        # Level 1: 相对持仓均价
                        drop_pct = (avg_cost - current_price) / avg_cost
                    else:
                        # Level 2+: 相对上一个买入价
                        if last_buy_price is None:
                            continue
                        drop_pct = (last_buy_price - current_price) / last_buy_price
                    
                    # 检查是否触发该层级
                    trigger = drop_pct >= level_config['drop']
                    
                    # Level 1 需要额外的RSI过滤
                    if level == 1 and level_config['rsi_filter']:
                        trigger = trigger and (current_rsi < 40)
                    
                    if trigger:
                        # 触发买入
                        signals.iloc[i, signals.columns.get_loc('Signal')] = 1
                        signals.iloc[i, signals.columns.get_loc('BuyLevel')] = level
                        signals.iloc[i, signals.columns.get_loc('BuyAmount')] = level_config['buy']
                        last_buy_price = current_price
                        last_buy_level = level
                        current_level = level
                        break  # 一天只买入一个层级
        
        return signals
