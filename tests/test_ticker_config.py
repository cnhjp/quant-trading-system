"""
标的配置测试脚本
"""

from config.ticker_loader import load_tickers, get_enabled_tickers

def test_ticker_loading():
    """测试标的加载功能"""
    print("=" * 60)
    print("测试标的加载器")
    print("=" * 60)
    
    # 1. 加载标的
    try:
        ticker_map = load_tickers()
        print(f"✅ 成功加载 {len(ticker_map)} 个标的\n")
    except Exception as e:
        print(f"❌ 加载标的失败: {e}\n")
        return False
    
    # 2. 显示标的详情
    print("标的详情：")
    print("-" * 60)
    for display_name, symbol in ticker_map.items():
        print(f"✅ {display_name}")
        print(f"   代码: {symbol}")
        print()
    
    # 3. 获取启用的标的列表
    enabled = get_enabled_tickers()
    print("-" * 60)
    print(f"启用的标的数量: {len(enabled)}")
    print(f"标的代码: {', '.join(enabled)}")
    print()
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_ticker_loading()
    exit(0 if success else 1)
