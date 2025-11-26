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
        
        # 将信号后移 1 位以模拟"次日开盘交易"
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
        # 实际上 DCA 通常假设现金是逐步流入的，或者我们假设有一笔初始资金在场外生息(这里忽略利息)，或者就是单纯比较"逐步建仓"的效果。
        # 用户要求"将初始资金拆分"，意味着我们有一笔总资金，每天投一部分。
        # 剩余现金 = Initial Capital - Total Invested
        data['Cash'] = self.initial_capital - data['Total_Invested']
        
        # 总资产 = 持仓市值 + 现金
        data['Equity'] = (data['Total_Shares'] * data['Close']) + data['Cash']
        
        # 基准: 一次性投入 (Lump Sum)
        # 假设第一天 Open 买入持有。
        initial_price = data['Open'].iloc[0]
        data['Benchmark_Equity'] = (data['Close'] / initial_price) * self.initial_capital
        
        return data

class Portfolio:
    """
    投资组合类，用于事件驱动回测
    跟踪现金、持仓、净值变化
    """
    def __init__(self, initial_capital: float, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        
        # 核心状态
        self.cash = initial_capital
        self.core_positions = []  # 底仓列表: [{'shares': float, 'price': float, 'level': 0}, ...]
        self.tradable_positions = []  # 可交易仓位栈 (LIFO): [{'shares': float, 'price': float, 'level': int}, ...]
        
        # 历史记录
        self.equity_history = []
        self.cash_history = []
        self.daily_returns = []
        
    def get_total_shares(self):
        """获取总持仓股数"""
        core_shares = sum(p['shares'] for p in self.core_positions)
        tradable_shares = sum(p['shares'] for p in self.tradable_positions)
        return core_shares + tradable_shares
    
    def get_avg_cost(self, current_price):
        """计算持仓均价"""
        total_shares = self.get_total_shares()
        if total_shares == 0:
            return 0
        
        # 使用当前价格估算底仓价值（因为底仓可能没有记录买入价）
        core_value = sum(p['shares'] * p.get('price', current_price) for p in self.core_positions)
        tradable_value = sum(p['shares'] * p['price'] for p in self.tradable_positions)
        
        return (core_value + tradable_value) / total_shares
    
    def buy(self, price: float, amount: float, level: int):
        """
        买入操作
        
        Args:
            price: 买入价格
            amount: 买入金额（非股数）
            level: 买入层级
        """
        if amount > self.cash:
            amount = self.cash
        
        if amount <= 0:
            return 0
        
        # 扣除手续费
        commission_fee = amount * self.commission
        net_amount = amount - commission_fee
        
        # 计算股数
        shares = net_amount / price
        
        # 记录持仓
        position = {'shares': shares, 'price': price, 'level': level}
        
        if level == 0:
            # 底仓
            self.core_positions.append(position)
        else:
            # 可交易仓位，压入栈
            self.tradable_positions.append(position)
        
        # 更新现金
        self.cash -= amount
        
        return shares
    
    def sell_lifo(self, price: float, sell_ratio: float):
        """
        LIFO卖出操作
        
        Args:
            price: 卖出价格
            sell_ratio: 卖出比例（针对最近一笔）
        
        Returns:
            卖出股数
        """
        if len(self.tradable_positions) == 0:
            return 0
        
        # 获取栈顶（最近一笔买入）
        last_position = self.tradable_positions[-1]
        shares_to_sell = last_position['shares'] * sell_ratio
        
        if shares_to_sell <= 0:
            return 0
        
        # 计算卖出收入
        sell_proceeds = shares_to_sell * price
        commission_fee = sell_proceeds * self.commission
        net_proceeds = sell_proceeds - commission_fee
        
        # 更新现金
        self.cash += net_proceeds
        
        # 更新栈顶仓位
        last_position['shares'] -= shares_to_sell
        
        # 留存部分转为底仓
        retained_shares = last_position['shares']
        if retained_shares > 0:
            self.core_positions.append({
                'shares': retained_shares,
                'price': last_position['price'],
                'level': last_position['level']
            })
        
        # 移除栈顶
        self.tradable_positions.pop()
        
        return shares_to_sell
    
    def update_value(self, current_price: float):
        """
        更新组合净值
        
        Args:
            current_price: 当前市场价格
        """
        total_shares = self.get_total_shares()
        market_value = total_shares * current_price
        total_equity = self.cash + market_value
        
        # 计算日收益率
        if len(self.equity_history) > 0:
            daily_return = (total_equity - self.equity_history[-1]) / self.equity_history[-1]
            self.daily_returns.append(daily_return)
        else:
            self.daily_returns.append(0)
        
        # 记录历史
        self.equity_history.append(total_equity)
        self.cash_history.append(self.cash)
        
        return total_equity
    
    def get_metrics(self):
        """计算组合指标"""
        if len(self.equity_history) == 0:
            return {}
        
        final_equity = self.equity_history[-1]
        
        # 总回报率
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 最大回撤
        equity_array = np.array(self.equity_history)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 夏普比率 (年化)
        if len(self.daily_returns) > 1:
            daily_returns_array = np.array(self.daily_returns)
            mean_daily_return = np.mean(daily_returns_array)
            std_daily_return = np.std(daily_returns_array)
            
            if std_daily_return > 0:
                # 年化夏普比率 (假设252个交易日)
                sharpe_ratio = (mean_daily_return / std_daily_return) * np.sqrt(252)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # 胜率 (正收益天数占比)
        if len(self.daily_returns) > 1:
            positive_days = np.sum(np.array(self.daily_returns) > 0)
            win_rate = positive_days / len(self.daily_returns)
        else:
            win_rate = 0
        
        return {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'final_equity': final_equity
        }

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
        
        # 将信号后移 1 位以模拟"次日开盘交易"
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
        # 实际上 DCA 通常假设现金是逐步流入的，或者我们假设有一笔初始资金在场外生息(这里忽略利息)，或者就是单纯比较"逐步建仓"的效果。
        # 用户要求"将初始资金拆分"，意味着我们有一笔总资金，每天投一部分。
        # 剩余现金 = Initial Capital - Total Invested
        data['Cash'] = self.initial_capital - data['Total_Invested']
        
        # 总资产 = 持仓市值 + 现金
        data['Equity'] = (data['Total_Shares'] * data['Close']) + data['Cash']
        
        # 基准: 一次性投入 (Lump Sum)
        # 假设第一天 Open 买入持有。
        initial_price = data['Open'].iloc[0]
        data['Benchmark_Equity'] = (data['Close'] / initial_price) * self.initial_capital
        
        return data

    def run_pyramid_backtest(self, df: pd.DataFrame, signals: pd.DataFrame):
        """
        运行金字塔网格策略回测 - Event-Driven (事件驱动)
        使用 Portfolio 对象管理复杂的资金进出
        """
        # 创建投资组合对象
        portfolio = Portfolio(self.initial_capital, self.commission)
        
        # 准备数据
        data = df.copy()
        
        # 事件驱动循环 - 逐行遍历
        for idx, row in data.iterrows():
            current_price = row['Open']  # 在开盘价交易
            close_price = row['Close']   # 用收盘价估值
            
            # 获取当天的信号
            if idx in signals.index:
                signal = signals.loc[idx, 'Signal']
                buy_level = signals.loc[idx, 'BuyLevel'] if 'BuyLevel' in signals.columns else -1
                buy_amount_ratio = signals.loc[idx, 'BuyAmount'] if 'BuyAmount' in signals.columns else 0
                sell_ratio = signals.loc[idx, 'SellRatio'] if 'SellRatio' in signals.columns else 0
            else:
                signal = 0
                buy_level = -1
                buy_amount_ratio = 0
                sell_ratio = 0
            
            # 执行买入
            if signal == 1 and buy_amount_ratio > 0:
                buy_amount = self.initial_capital * buy_amount_ratio
                portfolio.buy(current_price, buy_amount, buy_level)
            
            # 执行卖出 (LIFO)
            elif signal == -1 and sell_ratio > 0:
                portfolio.sell_lifo(current_price, sell_ratio)
            
            # 更新当日净值（使用收盘价）
            portfolio.update_value(close_price)
        
        # 将Portfolio数据转换为DataFrame
        data['Cash'] = portfolio.cash_history
        data['Equity'] = portfolio.equity_history
        data['Total_Shares'] = [portfolio.get_total_shares()] * len(data)  # 简化处理
        
        # 计算详细的每日持仓信息（需要重新遍历）
        core_shares_list = []
        tradable_shares_list = []
        avg_cost_list = []
        
        # 重新创建portfolio来追踪详细信息
        portfolio_track = Portfolio(self.initial_capital, self.commission)
        for idx, row in data.iterrows():
            current_price = row['Open']
            close_price = row['Close']
            
            if idx in signals.index:
                signal = signals.loc[idx, 'Signal']
                buy_level = signals.loc[idx, 'BuyLevel'] if 'BuyLevel' in signals.columns else -1
                buy_amount_ratio = signals.loc[idx, 'BuyAmount'] if 'BuyAmount' in signals.columns else 0
                sell_ratio = signals.loc[idx, 'SellRatio'] if 'SellRatio' in signals.columns else 0
            else:
                signal = 0
                buy_level = -1
                buy_amount_ratio = 0
                sell_ratio = 0
            
            if signal == 1 and buy_amount_ratio > 0:
                buy_amount = self.initial_capital * buy_amount_ratio
                portfolio_track.buy(current_price, buy_amount, buy_level)
            elif signal == -1 and sell_ratio > 0:
                portfolio_track.sell_lifo(current_price, sell_ratio)
            
            # 记录当日信息
            core_shares = sum(p['shares'] for p in portfolio_track.core_positions)
            tradable_shares = sum(p['shares'] for p in portfolio_track.tradable_positions)
            avg_cost = portfolio_track.get_avg_cost(close_price)
            
            core_shares_list.append(core_shares)
            tradable_shares_list.append(tradable_shares)
            avg_cost_list.append(avg_cost)
        
        data['Core_Position'] = core_shares_list
        data['Tradable_Position'] = tradable_shares_list
        data['Total_Shares'] = [core_shares_list[i] + tradable_shares_list[i] for i in range(len(core_shares_list))]
        data['Avg_Cost'] = avg_cost_list
        data['Position_Value'] = data['Total_Shares'] * data['Close']
        
        # 基准: 一次性投入 (Lump Sum)
        initial_price = data['Open'].iloc[0]
        data['Benchmark_Equity'] = (data['Close'] / initial_price) * self.initial_capital
        
        # 保存portfolio对象以便获取指标
        data.portfolio = portfolio
        
        return data

    def calculate_metrics(self, results: pd.DataFrame, is_dca=False, is_pyramid=False):
        """计算性能指标。"""
        if is_pyramid:
            # 金字塔网格策略 - 使用 Portfolio 对象的指标
            if hasattr(results, 'portfolio'):
                portfolio_metrics = results.portfolio.get_metrics()
                
                # 基准收益 (Lump Sum)
                benchmark_final = results['Benchmark_Equity'].iloc[-1]
                benchmark_return = (benchmark_final - self.initial_capital) / self.initial_capital
                
                return {
                    "Total Return": portfolio_metrics['total_return'],
                    "Benchmark Return": benchmark_return,
                    "Win Rate": portfolio_metrics['win_rate'],
                    "Max Drawdown": portfolio_metrics['max_drawdown'],
                    "Sharpe Ratio": portfolio_metrics['sharpe_ratio']
                }
            else:
                # 备用方案（如果没有portfolio对象）
                final_equity = results['Equity'].iloc[-1]
                total_return = (final_equity - self.initial_capital) / self.initial_capital
                
                benchmark_final = results['Benchmark_Equity'].iloc[-1]
                benchmark_return = (benchmark_final - self.initial_capital) / self.initial_capital
                
                # 最大回撤
                rolling_max = results['Equity'].cummax()
                drawdown = (results['Equity'] - rolling_max) / rolling_max
                max_drawdown = drawdown.min()
                
                # 胜率（简化计算：净值上涨的天数占比）
                equity_change = results['Equity'].diff()
                win_days = (equity_change > 0).sum()
                total_days = len(equity_change) - 1
                win_rate = win_days / total_days if total_days > 0 else 0
                
                return {
                    "Total Return": total_return,
                    "Benchmark Return": benchmark_return,
                    "Win Rate": win_rate,
                    "Max Drawdown": max_drawdown,
                    "Sharpe Ratio": 0
                }
        
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
