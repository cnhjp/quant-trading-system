import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from core.data_loader import DataLoader
from core.strategies import LiquidityGrabStrategy, TrendConfluenceStrategy, MeanReversionStrategy, DailyDCAStrategy, PyramidGridStrategy, MA200TrendStrategy, TurnOfTheMonthStrategy, VIXSwitchStrategy
from core.backtester import Backtester
from core.auth import check_password
from config.settings import TICKER_MAP

# 页面配置
st.set_page_config(page_title="量化交易回测系统", layout="wide")

# 登录校验
if not check_password():
    st.stop()

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

# 模式选择
app_mode = st.sidebar.radio("功能模式", ["策略回测", "交易信号看板"])

# 标的映射
# TICKER_MAP imported from config.py

ticker_source = st.sidebar.radio("标的来源", ["预设标的", "自定义标的"])

if ticker_source == "预设标的":
    selected_ticker_label = st.sidebar.selectbox("选择标的", list(TICKER_MAP.keys()))
    ticker = TICKER_MAP[selected_ticker_label]
    use_cache = True
else:
    custom_ticker = st.sidebar.text_input("输入标的代码 (例如 AAPL)", value="AAPL")
    ticker = custom_ticker.strip().upper() if custom_ticker.strip() else "SPY"
    use_cache = False

# 确定货币符号
if ticker.endswith(".HK"):
    currency_symbol = "HK$"
elif ticker.endswith(".SS") or ticker.endswith(".SZ"):
    currency_symbol = "¥"
else:
    currency_symbol = "$"

initial_capital = st.sidebar.number_input("初始资金", value=10000, step=1000)

# 初始化模块 (使用用户输入的初始资金)
backtester = Backtester(initial_capital=initial_capital)

# 定义原始数据列的配置和 Tooltip (全局复用)
raw_data_column_config = {
    "Open": st.column_config.NumberColumn("Open 🛈", help="开盘价: 交易日开始时的第一笔成交价格。"),
    "High": st.column_config.NumberColumn("High 🛈", help="最高价: 交易日内的最高成交价格。"),
    "Low": st.column_config.NumberColumn("Low 🛈", help="最低价: 交易日内的最低成交价格。"),
    "Close": st.column_config.NumberColumn("Close 🛈", help="收盘价: 交易日结束时的最后一笔成交价格。"),
    "Volume": st.column_config.NumberColumn("Volume 🛈", help="成交量: 交易日内的总成交股数或合约数。"),
    "PDH": st.column_config.NumberColumn("PDH 🛈", help="昨日高点: 上一个交易日的最高价。"),
    "PDL": st.column_config.NumberColumn("PDL 🛈", help="昨日低点: 上一个交易日的最低价。"),
    "VWAP": st.column_config.NumberColumn("VWAP 🛈", help="成交量加权平均价: 按成交量加权的平均成交价格。"),
    "MA200": st.column_config.NumberColumn("MA200 🛈", help="200日均线: 过去200个交易日的收盘价平均值，长期趋势参考。"),
    "RSI": st.column_config.NumberColumn("RSI 🛈", help="相对强弱指数: 衡量买卖力量对比(0-100)。"),
    "TP": st.column_config.NumberColumn("TP 🛈", help="典型价格: (High + Low + Close) / 3。"),
    "TPV": st.column_config.NumberColumn("TPV 🛈", help="典型价格成交量: TP * Volume。"),
    "CumTPV": st.column_config.NumberColumn("CumTPV 🛈", help="累积 TPV。"),
    "CumVol": st.column_config.NumberColumn("CumVol 🛈", help="累积成交量。"),
}

def load_strategy_doc(strategy_display_name):
    """加载策略文档"""
    try:
        file_path = os.path.join("docs", f"{strategy_display_name}.md")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        return f"无法加载文档: {e}"
    return None

def get_action_description(strategy_name, current_row, prev_row=None):
    """
    根据单行数据（以及前一行数据）解析操作描述。
    用于批量处理历史数据。
    """
    today_sig = current_row['Signal']
    if prev_row is not None:
        prev_sig = prev_row['Signal']
    else:
        prev_sig = 0 # 默认前一天空仓

    if strategy_name == "Daily DCA":
        return "买入 (定投)"
        
    elif strategy_name == "Pyramid Grid":
        if today_sig == 1:
            level = current_row.get('BuyLevel', -1)
            amt = current_row.get('BuyAmount', 0)
            return f"买入 (L{level}, {amt:.0%})"
        elif today_sig == -1:
            ratio = current_row.get('SellRatio', 0)
            return f"卖出 ({ratio:.0%})"
        else:
            # Grid 策略持有是常态，不一定每次都输出
            # 为了历史表格整洁，这里可以显示 "持仓" 或 空
            # 如果上一时刻持有底仓以上，则是持仓
            return "持仓" # 简化显示
            
    else:
        # Standard 0/1
        if today_sig == 1 and prev_sig == 0:
            return "买入 (100% 全仓)"
        elif today_sig == 1 and prev_sig == 1:
            return "持仓 (100%)"
        elif today_sig == 0 and prev_sig == 1:
            return "卖出 (100% 清仓)"
        elif today_sig == 0 and prev_sig == 0:
            return "空仓 (0%)"
            
    return "?"

def get_strategy_action(strategy_name, signals):
    """获取策略在最新日期的操作建议 (原有函数保留用于回测模式)"""
    if signals.empty:
        return "无数据", None
    
    last_date = signals.index[-1]
    today_sig = signals['Signal'].iloc[-1]
    
    # Check if we have previous data
    if len(signals) > 1:
        prev_sig = signals['Signal'].iloc[-2]
    else:
        prev_sig = 0
        
    if strategy_name == "Daily DCA":
        return "买入 (定投)", last_date
        
    elif strategy_name == "Pyramid Grid":
        if today_sig == 1:
            level = signals['BuyLevel'].iloc[-1]
            amt = signals['BuyAmount'].iloc[-1]
            return f"买入 (层级 {level}, 仓位 {amt:.0%})", last_date
        elif today_sig == -1:
            ratio = signals['SellRatio'].iloc[-1]
            return f"卖出 (比例 {ratio:.0%})", last_date
        else:
            return "无交易 (持仓/观望)", last_date
            
    else:
        # Standard 0/1 State Strategies
        if today_sig == 1 and prev_sig == 0:
            return "买入 (100% 全仓)", last_date
        elif today_sig == 1 and prev_sig == 1:
            return "持仓 (100%)", last_date
        elif today_sig == 0 and prev_sig == 1:
            return "卖出 (100% 清仓)", last_date
        elif today_sig == 0 and prev_sig == 0:
            return "空仓 / 观望", last_date
            
    return "未知", last_date

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


if app_mode == "交易信号看板":
    st.title(f"📈 交易信号看板 ({ticker})")
    
    # 1. 获取数据 (默认取最近 2 年数据以保证指标计算足够)
    with st.spinner("正在分析最新市场数据..."):
        df = data_loader.fetch_data(ticker, period="2y", interval="1d", cache_data=use_cache)
        vix_df = data_loader.get_vix(period="2y", interval="1d")
        
        if df.empty:
            st.error("无法获取数据，请稍后再试。")
        else:
            # 2. 计算所有策略的信号
            all_actions = pd.DataFrame(index=df.index)
            
            # 遍历策略生成信号
            for s_name, strategy in strategies.items():
                disp_name = strategy_display_names[s_name]
                
                if s_name == "Daily DCA":
                    # DCA 简单处理
                    all_actions[disp_name] = "🟢 买入 (定投)"
                else:
                    try:
                        if s_name == "Pyramid Grid":
                            sigs = strategy.generate_signals(df)
                        else:
                            sigs = strategy.generate_signals(df, vix_df=vix_df)
                        
                        # 转换信号为文字描述
                        # 为了效率，我们可以使用 apply，或者简单的循环
                        # 由于要用到 prev_row，这里简单遍历一遍或者使用 vectorized logic
                        
                        # 向量化处理 (Standard)
                        if s_name not in ["Pyramid Grid"]:
                            actions = []
                            sig_series = sigs['Signal']
                            prev_sig_series = sig_series.shift(1).fillna(0)
                            
                            for i in range(len(sig_series)):
                                curr = sig_series.iloc[i]
                                prev = prev_sig_series.iloc[i]
                                
                                if curr == 1 and prev == 0: actions.append("🟢 买入 (100% 全仓)")
                                elif curr == 1 and prev == 1: actions.append("🔵 持仓 (100%)")
                                elif curr == 0 and prev == 1: actions.append("🔴 卖出 (100% 清仓)")
                                else: actions.append("⚪ 空仓")
                            
                            all_actions[disp_name] = actions
                            
                        else:
                            # Pyramid Grid 复杂逻辑，逐行处理比较稳妥 (虽然慢一点，但数据量不大)
                            actions = []
                            for i in range(len(sigs)):
                                act = get_action_description(s_name, sigs.iloc[i], sigs.iloc[i-1] if i > 0 else None)
                                # 添加 emoji
                                if "买入" in act: act = "🟢 " + act
                                elif "卖出" in act: act = "🔴 " + act
                                elif "持仓" in act: act = "🔵 " + act
                                actions.append(act)
                            all_actions[disp_name] = actions
                            
                    except Exception as e:
                        all_actions[disp_name] = "Error"
                        print(f"Error processing {s_name}: {e}")

            # 3. 展示今日概览
            st.subheader("📅 今日操作建议")
            last_date = df.index[-1]
            st.info(f"数据日期: **{last_date.strftime('%Y-%m-%d')}**")
            
            # 取最后一行并转置
            today_actions = all_actions.iloc[[-1]].T
            today_actions.columns = ["操作建议"]
            
            # 样式优化
            def color_action(val):
                color = ''
                if '买入' in val: color = 'background-color: #d4edda; color: #155724' # Green
                elif '卖出' in val: color = 'background-color: #f8d7da; color: #721c24' # Red
                elif '持仓' in val: color = 'background-color: #cce5ff; color: #004085' # Blue
                return color

            st.table(today_actions.style.applymap(color_action))
            
            # 4. 历史信号全览
            st.subheader("📜 历史信号总览")
            
            # 倒序排列
            history_df = all_actions.sort_index(ascending=False)
            
            # 显示最近 N 天
            days_to_show = st.slider("显示最近天数", 10, 365, 30)
            st.dataframe(history_df.head(days_to_show).style.applymap(color_action), height=600)


elif app_mode == "策略回测":
    compare_mode = st.sidebar.checkbox("策略对比模式")

    selected_comparison_strategies = []

    if not compare_mode:
        # 默认选择每日定投 (index 3)
        selected_strategy_display = st.sidebar.selectbox("选择策略", list(strategy_display_names.values()), index=3)
        strategy_name = display_to_key[selected_strategy_display]
    else:
        strategy_name = None # In compare mode, we ignore single strategy selection
        selected_comparison_strategies = st.sidebar.multiselect(
            "选择要对比的策略",
            options=list(strategy_display_names.values()),
            default=list(strategy_display_names.values())
        )

    # 默认回测周期 1y (index 0)
    period = st.sidebar.selectbox("回测周期", ["3mo", "6mo", "1y", "2y", "5y", "10y"], index=2)

    # 双模式逻辑
    interval = "1d"

    # run_backtest = st.sidebar.button("开始回测") # Removed for auto-run
    update_data = st.sidebar.button("强制更新数据")

    if update_data:
        with st.spinner(f"正在更新 {ticker} 的数据..."):
            data_loader.fetch_data(ticker, period=period, interval=interval, force_update=True, cache_data=use_cache)
            st.sidebar.success(f"{ticker} 数据已更新！")

    # 主区域
    st.title(f"{ticker} - 策略回测")

    # 即时显示策略文档 (不需要点击开始回测)
    if not compare_mode and strategy_name:
        doc_content = load_strategy_doc(selected_strategy_display)
        if doc_content:
            with st.expander(f"📖 策略说明: {selected_strategy_display}"):
                st.markdown(doc_content)

    # 自动运行回测
    with st.spinner("正在获取数据并执行回测..."):
        # 1. 获取数据
        df = data_loader.fetch_data(ticker, period=period, interval=interval, cache_data=use_cache)
        vix_df = data_loader.get_vix(period=period, interval=interval)
        
        if df.empty:
            st.error("未找到数据！请检查标的是否正确或网络连接。")
        else:
            if compare_mode:
                    # 对比模式逻辑
                    st.subheader("策略对比分析")
                    
                    comparison_results = []
                    equity_curves = {}
                    
                    # 确定要运行的策略
                    strategies_to_run = {}
                    if selected_comparison_strategies:
                        for disp in selected_comparison_strategies:
                            k = display_to_key[disp]
                            strategies_to_run[k] = strategies[k]
                    
                    if not strategies_to_run:
                        st.warning("请至少选择一个策略进行对比。")
                        st.stop()

                    # 遍历选中的策略
                    for s_name, strategy in strategies_to_run.items():
                        # 生成信号
                        if s_name == "Daily DCA":
                            sig = strategy.generate_signals(df)
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
                        
                        # 获取今日操作建议
                        action, action_date = get_strategy_action(s_name, sig)
                        met['今日操作'] = action
                        met['数据日期'] = action_date.strftime('%Y-%m-%d')
                        
                        comparison_results.append(met)
                        
                        # 收集净值曲线
                        equity_curves[strategy_display_names[s_name]] = res['Equity']
                        
                        # 保存基准 (只需要一次)
                        if 'Benchmark_Equity' not in equity_curves:
                            equity_curves[f'基准 ({ticker} 买入持有)'] = res['Benchmark_Equity']

                    # 添加基准表现到表格
                    if comparison_results and not df.empty:
                        # 使用最后一次计算的 res (包含 Benchmark_Equity)
                        bench_res = res.copy()
                        bench_res['Equity'] = res['Benchmark_Equity']
                        # 计算基准指标
                        bench_met = backtester.calculate_metrics(bench_res)
                        
                        bench_met['Strategy'] = f'📊 基准 ({ticker})'
                        bench_met['今日操作'] = '-'
                        bench_met['数据日期'] = action_date.strftime('%Y-%m-%d') if action_date else "-"
                        # 基准的基准收益就是它自己，或者设为 0 表示无超额
                        bench_met['Benchmark Return'] = bench_met['Total Return'] 
                        
                        comparison_results.append(bench_met)

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
                    
                    # 调整列顺序，把操作建议放在前面
                    cols = ['今日操作', '数据日期', '总收益率', '基准收益', '夏普比率', '胜率', '最大回撤']
                    # 确保列存在 (防止某些指标计算失败缺失)
                    cols = [c for c in cols if c in comp_df.columns]
                    comp_df = comp_df[cols]

                    # 转换百分比数值，以便 st.dataframe 正确显示 (它不会自动乘以100)
                    # 注意：这里我们创建一个副本用于显示，以免影响后续逻辑（虽然这里是最后一步）
                    display_df = comp_df.copy()
                    pct_cols = ['总收益率', '基准收益', '胜率', '最大回撤']
                    for col in pct_cols:
                        if col in display_df.columns:
                            display_df[col] = display_df[col] * 100

                    st.dataframe(
                        display_df,
                        column_config={
                            "总收益率": st.column_config.NumberColumn("总收益率 🛈", format="%.2f%%", help="策略在回测期间的累积收益百分比。"),
                            "基准收益": st.column_config.NumberColumn("基准收益 🛈", format="%.2f%%", help="同期买入并持有标的（如 SPY）的收益率。"),
                            "胜率": st.column_config.NumberColumn("胜率 🛈", format="%.2f%%", help="盈利交易次数占总交易次数的比例。"),
                            "最大回撤": st.column_config.NumberColumn("最大回撤 🛈", format="%.2f%%", help="资金曲线从峰值回落的最大跌幅。"),
                            "夏普比率": st.column_config.NumberColumn("夏普比率 🛈", format="%.2f", help="衡量风险调整后的收益。数值越高越好。"),
                        },
                        use_container_width=True
                    )
                    
                    # 2. 净值曲线对比图
                    fig_comp = go.Figure()
                    for name, curve in equity_curves.items():
                        line_props = dict()
                        if "Benchmark" in name or "基准" in name:
                            line_props = dict(dash='dash', color='gray', width=2)
                        
                        fig_comp.add_trace(go.Scatter(x=curve.index, y=curve, mode='lines', name=name, line=line_props))
                    
                    fig_comp.update_layout(title="全策略资金曲线对比", xaxis_title="日期", yaxis_title=f"净值 ({currency_symbol})")
                    st.plotly_chart(fig_comp, use_container_width=True)
                    
                    # 3. 原始数据查看
                    with st.expander("查看原始数据"):
                        st.dataframe(df.sort_index(ascending=False), column_config=raw_data_column_config, use_container_width=True)

            else:
                # 单一策略模式 (原有逻辑)
                
                # 获取通用信号（对于DCA和Grid，虽然逻辑不同，但为了获取操作建议，我们需要信号对象）
                    # 注意：下面的 if/else 块里已经有了各自的逻辑，这里主要为了提取“今日操作”
                    
                    current_action = "未知"
                    action_date = None
                    
                    if strategy_name == "Daily DCA":
                        # DCA 特殊处理
                        # DCA 信号总是 1，我们需要构造一个 dummy 信号 df 或者直接调用 get_strategy_action
                        # 但 get_strategy_action 需要 dataframe。
                        # 重新生成信号
                        dca_strategy = strategies[strategy_name]
                        dca_signals = dca_strategy.generate_signals(df)
                        current_action, action_date = get_strategy_action(strategy_name, dca_signals)
                        
                        results = backtester.run_dca_backtest(df)
                        metrics = backtester.calculate_metrics(results, is_dca=True)
                        
                        # 显示操作建议
                        st.success(f"📅 **{action_date.strftime('%Y-%m-%d')} 操作建议:** {current_action}")

                        # 显示 DCA 结果
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("总收益率", f"{metrics['Total Return']:.2%}", help="定投结束时的累积收益百分比。")
                        col2.metric("总投入", f"{currency_symbol}{results['Total_Invested'].iloc[-1]:,.0f}", help="定投期间累计投入的本金总额。")
                        col3.metric("最终净值", f"{currency_symbol}{results['Equity'].iloc[-1]:,.0f}", help="回测结束时的账户总资产（持仓市值 + 现金）。")
                        col4.metric("最大回撤", f"{metrics['Max Drawdown']:.2%}", help="资金曲线从峰值回落的最大跌幅。")
                        col5.metric("夏普比率", f"{metrics.get('Sharpe Ratio', 0):.2f}", help="衡量风险调整后的收益。数值越高越好。")
                        
                        tab1, tab2, tab3 = st.tabs(["回测结果", "交易分析", "历史数据"])
                        with tab1:
                            fig_equity = go.Figure()
                            fig_equity.add_trace(go.Scatter(x=results.index, y=results['Equity'], mode='lines', name='定投净值'))
                            fig_equity.add_trace(go.Scatter(x=results.index, y=results['Total_Invested'], mode='lines', name='总投入成本', line=dict(dash='dash', color='gray')))
                            fig_equity.update_layout(title="定投资金曲线 vs 成本", xaxis_title="日期", yaxis_title=f"金额 ({currency_symbol})")
                            st.plotly_chart(fig_equity, use_container_width=True)
                        
                        with tab2:
                            st.info("定投策略每日买入，无特定交易信号图表。")
                        
                        with tab3:
                            st.dataframe(df.sort_index(ascending=False), column_config=raw_data_column_config, use_container_width=True)
                    
                    elif strategy_name == "Pyramid Grid":
                        # Pyramid Grid 特殊处理
                        strategy = strategies[strategy_name]
                        signals = strategy.generate_signals(df)
                        
                        current_action, action_date = get_strategy_action(strategy_name, signals)
                        st.success(f"📅 **{action_date.strftime('%Y-%m-%d')} 操作建议:** {current_action}")

                        results = backtester.run_pyramid_backtest(df, signals)
                        metrics = backtester.calculate_metrics(results, is_pyramid=True)
                        
                        # 显示 Pyramid Grid 结果
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("总收益率", f"{metrics['Total Return']:.2%}", help="策略在回测期间的累积收益百分比。")
                        col2.metric("基准收益", f"{metrics['Benchmark Return']:.2%}", help="同期买入并持有标的（如 SPY）的收益率。")
                        col3.metric("夏普比率", f"{metrics.get('Sharpe Ratio', 0):.2f}", help="衡量风险调整后的收益。数值越高越好。")
                        col4.metric("胜率", f"{metrics['Win Rate']:.2%}", help="盈利交易次数占总交易次数的比例。")
                        col5.metric("最大回撤", f"{metrics['Max Drawdown']:.2%}", help="资金曲线从峰值回落的最大跌幅。")
                        
                        tab1, tab2, tab3 = st.tabs(["回测结果", "仓位分析", "历史数据"])
                        with tab1:
                            # 资金曲线
                            fig_equity = go.Figure()
                            fig_equity.add_trace(go.Scatter(x=results.index, y=results['Equity'], mode='lines', name='策略净值'))
                            fig_equity.add_trace(go.Scatter(x=results.index, y=results['Benchmark_Equity'], mode='lines', name='基准净值 (一次性买入)', line=dict(dash='dash', color='gray')))
                            fig_equity.update_layout(title="金字塔网格 vs 一次性投入", xaxis_title="日期", yaxis_title=f"净值 ({currency_symbol})")
                            st.plotly_chart(fig_equity, use_container_width=True)
                        
                        with tab2:
                            # 仓位分析
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("底仓股数", f"{results['Core_Position'].iloc[-1]:.2f}")
                                st.metric("可交易股数", f"{results['Tradable_Position'].iloc[-1]:.2f}")
                            with col_b:
                                st.metric("总持仓股数", f"{results['Total_Shares'].iloc[-1]:.2f}")
                                st.metric("持仓均价", f"{currency_symbol}{results['Avg_Cost'].iloc[-1]:.2f}")
                            
                            # 持仓演变图
                            fig_position = go.Figure()
                            fig_position.add_trace(go.Scatter(x=results.index, y=results['Core_Position'], mode='lines', name='底仓 (永久)', stackgroup='one'))
                            fig_position.add_trace(go.Scatter(x=results.index, y=results['Tradable_Position'], mode='lines', name='可交易仓位', stackgroup='one'))
                            fig_position.update_layout(title="仓位演变", xaxis_title="日期", yaxis_title="持仓股数")
                            st.plotly_chart(fig_position, use_container_width=True)
                        
                        with tab3:
                            st.dataframe(df.sort_index(ascending=False), column_config=raw_data_column_config, use_container_width=True)
                            
                    else:
                        # 标准策略处理
                        strategy = strategies[strategy_name]
                        signals = strategy.generate_signals(df, vix_df=vix_df)
                        
                        current_action, action_date = get_strategy_action(strategy_name, signals)
                        st.success(f"📅 **{action_date.strftime('%Y-%m-%d')} 操作建议:** {current_action}")
                        
                        # 3. 运行回测
                        results = backtester.run_backtest(df, signals)
                        metrics = backtester.calculate_metrics(results)
                        
                        # 4. 显示结果
                        
                        # 指标行
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("总收益率", f"{metrics['Total Return']:.2%}", help="策略在回测期间的累积收益百分比。")
                        col2.metric("基准收益", f"{metrics['Benchmark Return']:.2%}", help="同期买入并持有标的（如 SPY）的收益率，用于对比策略表现。")
                        col3.metric("胜率", f"{metrics['Win Rate']:.2%}", help="盈利交易次数占总交易次数的比例。")
                        col4.metric("最大回撤", f"{metrics['Max Drawdown']:.2%}", help="资金曲线从峰值回落的最大跌幅，衡量策略可能面临的最大风险。")
                        col5.metric("夏普比率", f"{metrics.get('Sharpe Ratio', 0):.2f}", help="衡量风险调整后的收益。数值越高，代表在承担单位风险下获得的超额回报越高（通常 >1 为良好）。")
                        
                        # 标签页视图
                        tab1, tab2, tab3 = st.tabs(["回测结果", "交易分析", "历史数据"])
                        
                        with tab1:
                            # 资金曲线
                            fig_equity = go.Figure()
                            fig_equity.add_trace(go.Scatter(x=results.index, y=results['Equity'], mode='lines', name='策略净值'))
                            fig_equity.add_trace(go.Scatter(x=results.index, y=results['Benchmark_Equity'], mode='lines', name=f'基准净值 ({ticker}持有)', line=dict(dash='dash', color='gray')))
                            fig_equity.update_layout(title="资金曲线 vs 基准", xaxis_title="日期", yaxis_title=f"净值 ({currency_symbol})")
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

                            with st.expander("🛈 图表指标说明"):
                                st.markdown("""
                                - **PDH (Previous Day High):** 昨日最高价，常作为阻力位参考。
                                - **PDL (Previous Day Low):** 昨日最低价，常作为支撑位参考。
                                - **VWAP (Volume Weighted Average Price):** 成交量加权平均价，反映市场平均持仓成本，是机构交易的重要参考线。
                                - **🔺/🔻:** 策略产生的买入/卖出信号点。
                                """)
                        
                        with tab3:
                            st.dataframe(df.sort_index(ascending=False), column_config=raw_data_column_config, use_container_width=True)