import os
import requests
import pandas as pd
import json
from datetime import datetime
from config import TICKER_MAP
from data_loader import DataLoader
from strategies import (
    LiquidityGrabStrategy, 
    TrendConfluenceStrategy, 
    MeanReversionStrategy, 
    DailyDCAStrategy, 
    PyramidGridStrategy, 
    MA200TrendStrategy, 
    TurnOfTheMonthStrategy, 
    VIXSwitchStrategy
)

# 钉钉 Webhook Base URL
# 用户需要在 GitHub Secrets 中配置 DINGTALK_ACCESS_TOKEN 和 (可选) DINGTALK_SECRET
DINGTALK_TOKEN = os.environ.get("DINGTALK_ACCESS_TOKEN")
DINGTALK_SECRET = os.environ.get("DINGTALK_SECRET") # 如果开启了加签

def get_strategies():
    return {
        "流动性掠夺": LiquidityGrabStrategy(),
        "趋势共振": TrendConfluenceStrategy(),
        "均值回归": MeanReversionStrategy(),
        "金字塔网格": PyramidGridStrategy(),
        "均线趋势": MA200TrendStrategy(),
        "月底效应": TurnOfTheMonthStrategy(),
        "波动率控制": VIXSwitchStrategy()
    }

def send_dingtalk_markdown(title, text):
    if not DINGTALK_TOKEN:
        print("Error: DINGTALK_ACCESS_TOKEN not found in environment variables.")
        return

    url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}"
    
    # 如果需要加签逻辑 (Timestamp + Sign)，这里可以扩展，但通常 Access Token 足够
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        result = response.json()
        if result.get("errcode") == 0:
            print("DingTalk notification sent successfully.")
        else:
            print(f"DingTalk error: {result}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

def generate_report():
    loader = DataLoader()
    strategies = get_strategies()
    
    report_lines = []
    report_lines.append(f"# 📊 量化交易早报 ({datetime.now().strftime('%Y-%m-%d')})")
    
    # 获取 VIX 数据 (用于部分策略)
    vix_df = loader.get_vix(period="1y", interval="1d")
    
    for name, ticker in TICKER_MAP.items():
        print(f"Analyzing {ticker}...")
        df = loader.fetch_data(ticker, period="1y", interval="1d", cache_data=True)
        
        if df.empty:
            continue
            
        last_date = df.index[-1]
        date_str = last_date.strftime('%m-%d')
        
        # 检查数据是否“新鲜” (例如 3 天内)
        days_diff = (datetime.now() - last_date).days
        freshness_icon = "🟢" if days_diff <= 1 else "🟠" if days_diff <= 3 else "🔴"
        
        ticker_section = [f"## {name} ({date_str} {freshness_icon})"]
        has_action = False
        
        for strat_name, strategy in strategies.items():
            try:
                # 生成信号
                if strat_name == "金字塔网格":
                    sigs = strategy.generate_signals(df)
                else:
                    sigs = strategy.generate_signals(df, vix_df=vix_df)
                
                if sigs.empty:
                    continue
                    
                # 获取最新信号
                curr_sig = sigs['Signal'].iloc[-1]
                
                # 获取前一日信号 (用于判断是否是新动作)
                prev_sig = sigs['Signal'].iloc[-2] if len(sigs) > 1 else 0
                
                action = None
                # 解析动作为人类可读文本
                if strat_name == "金字塔网格":
                    if curr_sig == 1:
                         action = f"**买入** (层级 {sigs['BuyLevel'].iloc[-1]})"
                    elif curr_sig == -1:
                         action = f"**卖出** (比例 {sigs['SellRatio'].iloc[-1]:.0%})"
                else:
                    if curr_sig == 1 and prev_sig == 0:
                        action = "**买入 (Open)** 🚀"
                    elif curr_sig == 0 and prev_sig == 1:
                        action = "**卖出 (Close)** 📉"
                    # 仅报告变动或持仓?
                    # 策略日报通常希望能看到持仓状态。
                    elif curr_sig == 1:
                        action = "持仓 (Hold)"
                
                # 只有当有特定动作(买/卖)或者处于持仓状态时才报告?
                # 为了简洁，我们只报告 "买入"、"卖出" 的变化，或者如果用户特别关心持仓也可以加上。
                # 考虑到手机屏幕，只报告 变化 (Change) 可能是最好的，或者做成精简列表。
                
                if action:
                    has_action = True
                    # 如果是开仓/平仓，加粗显示
                    prefix = "- "
                    if "Open" in action or "Close" in action or "买入" in action or "卖出" in action:
                         prefix = "- 🔥 "
                    
                    ticker_section.append(f"{prefix}{strat_name}: {action}")
                    
            except Exception as e:
                print(f"Error {strat_name} on {ticker}: {e}")
        
        if has_action:
            report_lines.extend(ticker_section)
            report_lines.append("---")
    
    # 如果没有任何信号
    if len(report_lines) == 1:
        report_lines.append("今日无特定交易信号建议。")
        
    # 添加页脚以匹配常见的钉钉自定义关键词 (防止 310000 错误)
    report_lines.append("\n> 系统自动推送 | 关键词: 量化 交易 测试 通知")
        
    full_text = "\n\n".join(report_lines)
    send_dingtalk_markdown("量化交易早报", full_text)

if __name__ == "__main__":
    generate_report()
