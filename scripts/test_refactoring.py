# 测试重构后的代码
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategies.vix_switch import VIXSwitchStrategy
from core.strategies.ma200_trend import MA200TrendStrategy
from core.strategies.daily_dca import DailyDCAStrategy
from core.strategies.pyramid_grid import PyramidGridStrategy
import pandas as pd
import numpy as np

def test_get_action_info():
    print("=" * 60)
    print("测试策略重构 - get_action_info 方法")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2022-01-01', periods=300)
    df = pd.DataFrame({
        'Close': np.random.randn(300).cumsum() + 100,
        'Open': np.random.randn(300).cumsum() + 100,
        'High': np.random.randn(300).cumsum() + 105,
        'Low': np.random.randn(300).cumsum() + 95,
        'Volume': np.random.randint(1000, 10000, 300),
        'RSI': np.random.randint(20, 80, 300)
    }, index=dates)
    
    # 测试1: DCA策略
    print("\n1. 测试 Daily DCA 策略")
    print("-" * 60)
    dca = DailyDCAStrategy()
    sigs = dca.generate_signals(df)
    action, reason = dca.get_action_info(sigs.iloc[-1], sigs.iloc[-2], df.iloc[-1])
    print(f"   操作: {action}")
    print(f"   原因: {reason}")
    
    # 测试2: MA200策略
    print("\n2. 测试 MA200 Trend 策略")
    print("-" * 60)
    ma200 = MA200TrendStrategy()
    sigs = ma200.generate_signals(df)
    action, reason = ma200.get_action_info(sigs.iloc[-1], sigs.iloc[-2], df.iloc[-1])
    print(f"   操作: {action}")
    print(f"   原因: {reason}")
    
    # 测试3: VIX Switch策略
    print("\n3. 测试 VIX Switch 策略")
    print("-" * 60)
    vix_df = pd.DataFrame({'Close': np.random.randint(15, 30, 300)}, index=dates)
    vix = VIXSwitchStrategy()
    sigs = vix.generate_signals(df, vix_df=vix_df)
    if not sigs.empty:
        action, reason = vix.get_action_info(sigs.iloc[-1], sigs.iloc[-2], df.iloc[-1])
        print(f"   操作: {action}")
        print(f"   原因: {reason}")
    else:
        print("   无信号生成")
    
    # 测试4: Pyramid Grid策略
    print("\n4. 测试 Pyramid Grid 策略")
    print("-" * 60)
    pyramid = PyramidGridStrategy()
    sigs = pyramid.generate_signals(df)
    action, reason = pyramid.get_action_info(sigs.iloc[-1], sigs.iloc[-2], df.iloc[-1])
    print(f"   操作: {action}")
    print(f"   原因: {reason}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！重构成功，各策略可以独立提供操作建议原因。")
    print("=" * 60)

if __name__ == "__main__":
    test_get_action_info()
