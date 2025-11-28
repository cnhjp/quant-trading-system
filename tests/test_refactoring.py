"""
重构验证测试脚本
验证所有策略是否正确加载
"""

from core.strategy_loader import load_strategies, get_enabled_strategies
from core.strategies.base import BaseStrategy

def test_strategy_loading():
    """测试策略加载功能"""
    print("=" * 60)
    print("测试策略加载器")
    print("=" * 60)
    
    # 1. 加载策略
    try:
        strategies, strategy_display_names = load_strategies()
        print(f"✅ 成功加载 {len(strategies)} 个策略\n")
    except Exception as e:
        print(f"❌ 加载策略失败: {e}\n")
        return False
    
    # 2. 验证每个策略
    print("策略详情：")
    print("-" * 60)
    for name, strategy in strategies.items():
        display_name = strategy_display_names.get(name, "未知")
        
        # 检查是否继承自 BaseStrategy
        is_base = isinstance(strategy, BaseStrategy)
        
        # 检查是否实现了 generate_signals 方法
        has_method = hasattr(strategy, 'generate_signals')
        
        status = "✅" if (is_base and has_method) else "❌"
        
        print(f"{status} {name}")
        print(f"   显示名称: {display_name}")
        print(f"   类名: {strategy.__class__.__name__}")
        print(f"   继承 BaseStrategy: {is_base}")
        print(f"   实现 generate_signals: {has_method}")
        print()
    
    # 3. 获取启用的策略列表
    enabled = get_enabled_strategies()
    print("-" * 60)
    print(f"启用的策略数量: {len(enabled)}")
    print(f"启用的策略: {', '.join(enabled)}")
    print()
    
    # 4. 验证策略名称映射
    print("=" * 60)
    print("策略名称映射验证")
    print("=" * 60)
    for name in strategies.keys():
        display = strategy_display_names.get(name)
        if display:
            print(f"✅ {name} -> {display}")
        else:
            print(f"❌ {name} -> 缺少显示名称")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_strategy_loading()
    exit(0 if success else 1)
