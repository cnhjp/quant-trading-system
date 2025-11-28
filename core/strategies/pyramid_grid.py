import pandas as pd
import numpy as np
from .base import BaseStrategy

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
        signals['CurrentLevel'] = 0  # 当前层级 (追踪状态)
        
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
        current_level = 0        # 当前已达到的最高层级 (初始为0)
        
        # 新增: 记录每一层的买入价格
        buy_prices = {}          # {level: price}
        
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
                
                buy_prices[0] = current_price # 记录 Level 0 价格
                signals.iloc[i, signals.columns.get_loc('CurrentLevel')] = current_level
                continue
            
            # 检查止盈条件 (上涨5%)
            if last_buy_price is not None and last_buy_level > 0:  # 不卖Level 0底仓
                profit_pct = (current_price - last_buy_price) / last_buy_price
                if profit_pct >= self.profit_trigger:
                    # 触发止盈：卖出最近一笔的80%
                    signals.iloc[i, signals.columns.get_loc('Signal')] = -1
                    signals.iloc[i, signals.columns.get_loc('SellRatio')] = self.sell_ratio
                    
                    # 更新状态：回退一个层级
                    current_level = max(0, last_buy_level - 1)
                    
                    # 关键修复: 恢复上一层的买入信息
                    last_buy_level = current_level
                    last_buy_price = buy_prices.get(current_level)
                    
                    # 如果回退到了 Level 0, last_buy_price 应该是 Level 0 的买入价
                    # buy_prices[0] 在第一天已经记录
                    
                    # 如果买入信息丢失(防御性编程), 重置
                    if last_buy_price is None:
                        last_buy_price = avg_cost # 回退到均价作为近似
                    
                    signals.iloc[i, signals.columns.get_loc('CurrentLevel')] = current_level
                    continue
            
            # 检查加仓条件 (相对持仓均价下跌)
            if avg_cost is not None:
                # 遍历网格层级 (从Level 1开始，跳过Level 0)
                triggered = False
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
                        
                        buy_prices[level] = current_price # 记录该层价格
                        triggered = True
                        break  # 一天只买入一个层级
                
                if not triggered:
                    # 保持当前状态
                    pass
            
            # 记录当天的 Level
            signals.iloc[i, signals.columns.get_loc('CurrentLevel')] = current_level
        
        return signals
