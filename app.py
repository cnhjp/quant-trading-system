import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_loader import DataLoader
from strategies import LiquidityGrabStrategy, TrendConfluenceStrategy, MeanReversionStrategy, DailyDCAStrategy, PyramidGridStrategy, MA200TrendStrategy, TurnOfTheMonthStrategy, VIXSwitchStrategy
from backtester import Backtester

# 页面配置
st.set_page_config(page_title="量化交易回测系统", layout="wide")

# 初始化模块
data_loader = DataLoader()
# backtester moved to sidebar config

strategies = {
    "Liquidity Grab (SFP)": LiquidityGrabStrategy(),
    "Trend Confluence": TrendConfluenceStrategy(),
    "Mean Reversion (RSI)": MeanReversionStrategy(),
    "Daily DCA": DailyDCAStrategy(),
    "Pyramid Grid": PyramidGridStrategy(),
    "MA200 Trend": MA200TrendStrategy(),
    "Turn of the Month": TurnOfTheMonthStrategy(),
    "VIX Switch": VIXSwitchStrategy()
}

# 侧边栏
st.sidebar.title("配置面板")
ticker = st.sidebar.selectbox("选择标的", ["SPY", "QQQ"])
initial_capital = st.sidebar.number_input("初始资金", value=10000, step=1000)

# 初始化模块 (使用用户输入的初始资金)
# data_loader = DataLoader() # 已经在上面初始化了，不需要重新初始化
backtester = Backtester(initial_capital=initial_capital)

# 策略名称映射
strategy_display_names = {
    "Liquidity Grab (SFP)": "流动性掠夺策略",
    "Trend Confluence": "趋势共振策略",
    "Mean Reversion (RSI)": "均值回归策略",
    "Daily DCA": "每日定投策略",
    "Pyramid Grid": "金字塔网格策略",
    "MA200 Trend": "均线趋势策略",
    "Turn of the Month": "月底效应策略",
    "VIX Switch": "波动率控制策略"
}
# 反向映射以获取策略字典的键
display_to_key = {v: k for k, v in strategy_display_names.items()}

compare_mode = st.sidebar.checkbox("对比所有策略")

if not compare_mode:
    # 默认选择每日定投 (index 3)
    selected_strategy_display = st.sidebar.selectbox("选择策略", list(strategy_display_names.values()), index=3)
    strategy_name = display_to_key[selected_strategy_display]
else:
    strategy_name = None # In compare mode, we ignore single strategy selection

# 默认回测周期 1y (index 0)
period = st.sidebar.selectbox("回测周期", ["1y", "2y", "5y", "10y"], index=0)

# 双模式逻辑
interval = "1d"
if period in ["1mo", "3mo"]: 
    pass

run_backtest = st.sidebar.button("开始回测")
update_data = st.sidebar.button("更新数据")

if update_data:
    with st.spinner(f"正在更新 {ticker} 的数据..."):
        data_loader.fetch_data(ticker, period=period, interval=interval, force_update=True)
        st.sidebar.success(f"{ticker} 数据已更新！")

# 主区域
st.title(f"{ticker}")

if run_backtest:
    with st.spinner("正在获取数据并执行回测..."):
        # 1. 获取数据
        df = data_loader.fetch_data(ticker, period=period, interval=interval)
        vix_df = data_loader.get_vix(period=period, interval=interval)
        
        if df.empty:
            st.error("未找到数据！")
        else:
            if compare_mode:
                # 对比模式逻辑
                st.subheader("策略对比分析")
                
                comparison_results = []
                equity_curves = {}
                
                # 遍历所有策略
                for s_name, strategy in strategies.items():
                    # 生成信号
                    if s_name == "Daily DCA":
                        res = backtester.run_dca_backtest(df)
                        met = backtester.calculate_metrics(res, is_dca=True)
                    elif s_name == "Pyramid Grid":
                        sig = strategy.generate_signals(df)
                        res = backtester.run_pyramid_backtest(df, sig)
                        met = backtester.calculate_metrics(res, is_pyramid=True)
                    else:
                        sig = strategy.generate_signals(df, vix_df=vix_df)
                        res = backtester.run_backtest(df, sig)
                        met = backtester.calculate_metrics(res)
                    
                    # 收集指标
                    met['Strategy'] = strategy_display_names[s_name]
                    comparison_results.append(met)
                    
                    # 收集净值曲线
                    equity_curves[strategy_display_names[s_name]] = res['Equity']
                    
                    # 保存基准 (只需要一次)
                    if 'Benchmark_Equity' not in equity_curves:
                        equity_curves['基准 (SPY 买入持有)'] = res['Benchmark_Equity']

                # 1. 指标对比表
                comp_df = pd.DataFrame(comparison_results).set_index('Strategy')
                # 重命名列为中文
                comp_df = comp_df.rename(columns={
                    'Total Return': '总收益率',
                    'Benchmark Return': '基准收益',
                    'Win Rate': '胜率',
                    'Max Drawdown': '最大回撤',
                    'Sharpe Ratio': '夏普比率'
                })
                # 格式化列
                format_dict = {
                    "总收益率": "{:.2%}",
                    "基准收益": "{:.2%}",
                    "胜率": "{:.2%}",
                    "最大回撤": "{:.2%}",
                    "夏普比率": "{:.2f}"
                }
                st.table(comp_df.style.format(format_dict))
                
                # 2. 净值曲线对比图
                fig_comp = go.Figure()
                for name, curve in equity_curves.items():
                    line_props = dict()
                    if "Benchmark" in name or "基准" in name:
                        line_props = dict(dash='dash', color='gray', width=2)
                    
                    fig_comp.add_trace(go.Scatter(x=curve.index, y=curve, mode='lines', name=name, line=line_props))
                
                fig_comp.update_layout(title="全策略资金曲线对比", xaxis_title="日期", yaxis_title="净值 ($)")
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # 3. 原始数据查看
                with st.expander("查看原始数据"):
                    st.dataframe(df)

            else:
                # 单一策略模式 (原有逻辑)
                if strategy_name == "Daily DCA":
                    # DCA 特殊处理
                    results = backtester.run_dca_backtest(df)
                    metrics = backtester.calculate_metrics(results, is_dca=True)
                    
                    # 显示 DCA 结果
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("总收益率", f"{metrics['Total Return']:.2%}")
                    col2.metric("总投入", f"${results['Total_Invested'].iloc[-1]:,.0f}")
                    col3.metric("最终净值", f"${results['Equity'].iloc[-1]:,.0f}")
                    col4.metric("最大回撤", f"{metrics['Max Drawdown']:.2%}")
                    
                    tab1, tab2, tab3 = st.tabs(["回测结果", "交易分析", "历史数据"])
                    with tab1:
                        fig_equity = go.Figure()
                        fig_equity.add_trace(go.Scatter(x=results.index, y=results['Equity'], mode='lines', name='定投净值'))
                        fig_equity.add_trace(go.Scatter(x=results.index, y=results['Total_Invested'], mode='lines', name='总投入成本', line=dict(dash='dash', color='gray')))
                        fig_equity.update_layout(title="定投资金曲线 vs 成本", xaxis_title="日期", yaxis_title="金额 ($)")
                        st.plotly_chart(fig_equity, use_container_width=True)
                    
                    with tab2:
                        st.info("定投策略每日买入，无特定交易信号图表。")
                    
                    with tab3:
                        st.dataframe(df)
                
                elif strategy_name == "Pyramid Grid":
                    # Pyramid Grid 特殊处理
                    strategy = strategies[strategy_name]
                    signals = strategy.generate_signals(df)
                    results = backtester.run_pyramid_backtest(df, signals)
                    metrics = backtester.calculate_metrics(results, is_pyramid=True)
                    
                    # 显示 Pyramid Grid 结果
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("总收益率", f"{metrics['Total Return']:.2%}")
                    col2.metric("基准收益", f"{metrics['Benchmark Return']:.2%}")
                    col3.metric("夏普比率", f"{metrics.get('Sharpe Ratio', 0):.2f}")
                    col4.metric("胜率", f"{metrics['Win Rate']:.2%}")
                    col5.metric("最大回撤", f"{metrics['Max Drawdown']:.2%}")
                    
                    tab1, tab2, tab3 = st.tabs(["回测结果", "仓位分析", "历史数据"])
                    with tab1:
                        # 资金曲线
                        fig_equity = go.Figure()
                        fig_equity.add_trace(go.Scatter(x=results.index, y=results['Equity'], mode='lines', name='策略净值'))
                        fig_equity.add_trace(go.Scatter(x=results.index, y=results['Benchmark_Equity'], mode='lines', name='基准净值 (一次性买入)', line=dict(dash='dash', color='gray')))
                        fig_equity.update_layout(title="金字塔网格 vs 一次性投入", xaxis_title="日期", yaxis_title="净值 ($)")
                        st.plotly_chart(fig_equity, use_container_width=True)
                    
                    with tab2:
                        # 仓位分析
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("底仓股数", f"{results['Core_Position'].iloc[-1]:.2f}")
                            st.metric("可交易股数", f"{results['Tradable_Position'].iloc[-1]:.2f}")
                        with col_b:
                            st.metric("总持仓股数", f"{results['Total_Shares'].iloc[-1]:.2f}")
                            st.metric("持仓均价", f"${results['Avg_Cost'].iloc[-1]:.2f}")
                        
                        # 持仓演变图
                        fig_position = go.Figure()
                        fig_position.add_trace(go.Scatter(x=results.index, y=results['Core_Position'], mode='lines', name='底仓 (永久)', stackgroup='one'))
                        fig_position.add_trace(go.Scatter(x=results.index, y=results['Tradable_Position'], mode='lines', name='可交易仓位', stackgroup='one'))
                        fig_position.update_layout(title="仓位演变", xaxis_title="日期", yaxis_title="持仓股数")
                        st.plotly_chart(fig_position, use_container_width=True)
                    
                    with tab3:
                        st.dataframe(df)
                        
                else:
                    # 标准策略处理
                    strategy = strategies[strategy_name]
                    signals = strategy.generate_signals(df, vix_df=vix_df)
                    
                    # 3. 运行回测
                    results = backtester.run_backtest(df, signals)
                    metrics = backtester.calculate_metrics(results)
                    
                    # 4. 显示结果
                    
                    # 指标行
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("总收益率", f"{metrics['Total Return']:.2%}")
                    col2.metric("基准收益", f"{metrics['Benchmark Return']:.2%}")
                    col3.metric("胜率", f"{metrics['Win Rate']:.2%}")
                    col4.metric("最大回撤", f"{metrics['Max Drawdown']:.2%}")
                    
                    # 标签页视图
                    tab1, tab2, tab3 = st.tabs(["回测结果", "交易分析", "历史数据"])
                    
                    with tab1:
                        # 资金曲线
                        fig_equity = go.Figure()
                        fig_equity.add_trace(go.Scatter(x=results.index, y=results['Equity'], mode='lines', name='策略净值'))
                        fig_equity.add_trace(go.Scatter(x=results.index, y=results['Benchmark_Equity'], mode='lines', name='基准净值 (SPY持有)', line=dict(dash='dash', color='gray')))
                        fig_equity.update_layout(title="资金曲线 vs 基准", xaxis_title="日期", yaxis_title="净值 ($)")
                        st.plotly_chart(fig_equity, use_container_width=True)
                        
                    with tab2:
                        # 带指标的 K 线图
                        # 创建子图: 第 1 行价格，第 2 行成交量/信号
                        fig_candle = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                        
                        # K 线
                        fig_candle.add_trace(go.Candlestick(
                            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'
                        ), row=1, col=1)
                        
                        # 如果可用，添加 PDH / PDL (用于 SFP 策略)
                        if 'PDH' in df.columns:
                            fig_candle.add_trace(go.Scatter(x=df.index, y=df['PDH'], mode='lines', name='昨日高点 (PDH)', line=dict(color='green', shape='hv')), row=1, col=1)
                        if 'PDL' in df.columns:
                            fig_candle.add_trace(go.Scatter(x=df.index, y=df['PDL'], mode='lines', name='昨日低点 (PDL)', line=dict(color='red', shape='hv')), row=1, col=1)
                            
                        # 如果可用，添加 VWAP
                        if 'VWAP' in df.columns:
                            fig_candle.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', name='锚定 VWAP', line=dict(color='orange')), row=1, col=1)

                        # 绘制买入/卖出标记
                        # 买入信号
                        buys = results[results['Signal'] == 1]
                        if not buys.empty:
                            fig_candle.add_trace(go.Scatter(
                                x=buys.index, y=buys['Low']*0.99, mode='markers', marker=dict(symbol='triangle-up', size=10, color='green'), name='买入信号'
                            ), row=1, col=1)
                            
                        # 卖出信号
                        sells = results[results['Signal'] == -1]
                        if not sells.empty:
                            fig_candle.add_trace(go.Scatter(
                                x=sells.index, y=sells['High']*1.01, mode='markers', marker=dict(symbol='triangle-down', size=10, color='red'), name='卖出信号'
                            ), row=1, col=1)

                        fig_candle.update_layout(title="价格行为与信号", xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig_candle, use_container_width=True)
                    
                    with tab3:
                        st.dataframe(df)

else:
    st.info("请在左侧选择参数并点击 '开始回测' 按钮。")
