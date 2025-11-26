import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, initial_capital=100000, commission=0.001):
        self.initial_capital = initial_capital
        self.commission = commission # 每笔交易 0.1%

    def run_backtest(self, df: pd.DataFrame, signals: pd.DataFrame, benchmark_df: pd.DataFrame = None):
        """
        运行回测模拟。
        逻辑: 在 Close[t] 产生信号 -> 在 Open[t+1] 交易。
        """
        # 对齐数据
        data = df.copy()
        data['Signal'] = signals['Signal']
        
        # 将信号后移 1 位以模拟“次日开盘交易”
        # 如果 Signal[t] 为 1，我们在 Open[t+1] 入场。
        # 所以我们在 t+1 的持仓由 Signal[t] 决定。
        data['Position'] = data['Signal'].shift(1).fillna(0)
        
        # 计算收益
        # 我们在 Open[t] 买入，在 Open[t+1] 卖出（概念上用于每日再平衡）
        # 或者更简单地说：
        # 如果 Position[t] == 1 (意味着 Signal[t-1] 是买入)，我们从 Open[t] 持有到 Open[t+1]。
        # 收益 = (Open[t+1] - Open[t]) / Open[t]
        
        data['NextOpen'] = data['Open'].shift(-1)
        data['Market_Return'] = (data['NextOpen'] - data['Open']) / data['Open']
        
        # 策略收益
        data['Strategy_Return'] = data['Position'] * data['Market_Return']
        
        # 交易成本
        # 当持仓发生变化时产生费用
        data['Trade_Count'] = data['Position'].diff().abs()
        data['Cost'] = data['Trade_Count'] * self.commission
        
        data['Net_Return'] = data['Strategy_Return'] - data['Cost']
        
        # 资金曲线
        data['Equity'] = self.initial_capital * (1 + data['Net_Return'].fillna(0)).cumprod()
        
        # 基准 (买入并持有 SPY)
        # 在第一个 Open 买入，永远持有。
        # 基准收益 = 市场收益 (Open 到 Open)
        data['Benchmark_Return'] = data['Market_Return']
        data['Benchmark_Equity'] = self.initial_capital * (1 + data['Benchmark_Return'].fillna(0)).cumprod()
        
        return data

    def run_dca_backtest(self, df: pd.DataFrame):
        """
        运行定投 (Dollar Cost Averaging) 回测。
        将初始资金平分到每一天进行定投。
        """
        data = df.copy()
        data['Signal'] = 1 # 总是买入
        
        # 计算每日定投金额
        days = len(data)
        daily_amount = self.initial_capital / days
        
        # 我们在 Open 价格买入
        data['Invested_Amount'] = daily_amount
        data['Shares_Bought'] = daily_amount / data['Open']
        
        # 累积份额
        data['Total_Shares'] = data['Shares_Bought'].cumsum()
        data['Total_Invested'] = data['Invested_Amount'].cumsum()
        
        # 净值 = 总份额 * 收盘价 + 剩余现金 (未投入部分)
        # 实际上 DCA 通常假设现金是逐步流入的，或者我们假设有一笔初始资金在场外生息(这里忽略利息)，或者就是单纯比较“逐步建仓”的效果。
        # 用户要求“将初始资金拆分”，意味着我们有一笔总资金，每天投一部分。
        # 剩余现金 = Initial Capital - Total Invested
        data['Cash'] = self.initial_capital - data['Total_Invested']
        
        # 总资产 = 持仓市值 + 现金
        data['Equity'] = (data['Total_Shares'] * data['Close']) + data['Cash']
        
        # 基准: 一次性投入 (Lump Sum)
        # 假设第一天 Open 买入持有。
        initial_price = data['Open'].iloc[0]
        data['Benchmark_Equity'] = (data['Close'] / initial_price) * self.initial_capital
        
        return data

    def calculate_metrics(self, results: pd.DataFrame, is_dca=False):
        """计算性能指标。"""
        if is_dca:
            # 对于拆分资金的 DCA，Total Return = (Final Equity - Initial Capital) / Initial Capital
            # 因为我们现在包含了 Cash 在 Equity 中
            final_equity = results['Equity'].iloc[-1]
            total_return = (final_equity - self.initial_capital) / self.initial_capital
            
            # 基准收益 (Lump Sum)
            benchmark_final = results['Benchmark_Equity'].iloc[-1]
            benchmark_return = (benchmark_final - self.initial_capital) / self.initial_capital
            
            # 胜率 (对于 DCA 不太适用，置为 0)
            win_rate = 0 
            
            # 最大回撤
            rolling_max = results['Equity'].cummax()
            drawdown = (results['Equity'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            return {
                "Total Return": total_return,
                "Benchmark Return": benchmark_return,
                "Win Rate": win_rate,
                "Max Drawdown": max_drawdown
            }
        else:
            total_return = (results['Equity'].iloc[-2] / self.initial_capital) - 1 # iloc[-2] 因为最后一行 NextOpen 是 NaN
            benchmark_return = (results['Benchmark_Equity'].iloc[-2] / self.initial_capital) - 1
            
            # 胜率 (活跃且收益为正的天数)
            active_days = results[results['Position'] != 0]
            if len(active_days) > 0:
                win_rate = len(active_days[active_days['Net_Return'] > 0]) / len(active_days)
            else:
                win_rate = 0
                
            # 最大回撤
            rolling_max = results['Equity'].cummax()
            drawdown = (results['Equity'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            return {
                "Total Return": total_return,
                "Benchmark Return": benchmark_return,
                "Win Rate": win_rate,
                "Max Drawdown": max_drawdown
            }
