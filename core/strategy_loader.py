"""
策略加载器
从配置文件动态加载启用的策略
"""
import json
import importlib
import os
from typing import Dict

def load_strategies(config_path: str = "config/strategies.json") -> Dict:
    """
    从配置文件加载启用的策略
    
    Args:
        config_path: 策略配置文件路径
        
    Returns:
        Dict: {strategy_name: strategy_instance}
    """
    # 读取配置文件
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"策略配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    strategies = {}
    strategy_display_names = {}
    
    for strategy_config in config['strategies']:
        # 只加载启用的策略
        if not strategy_config.get('enabled', True):
            continue
        
        strategy_name = strategy_config['name']
        display_name = strategy_config['display_name']
        module_path = strategy_config['module']
        class_name = strategy_config['class_name']
        
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 获取策略类
            strategy_class = getattr(module, class_name)
            
            # 实例化策略
            strategy_instance = strategy_class()
            
            # 存储策略实例
            strategies[strategy_name] = strategy_instance
            strategy_display_names[strategy_name] = display_name
            
        except Exception as e:
            print(f"加载策略失败 {strategy_name}: {e}")
            continue
    
    return strategies, strategy_display_names


def get_enabled_strategies(config_path: str = "config/strategies.json") -> list:
    """
    获取所有启用的策略名称列表
    
    Args:
        config_path: 策略配置文件路径
        
    Returns:
        list: 启用的策略名称列表
    """
    if not os.path.exists(config_path):
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    enabled = [s['name'] for s in config['strategies'] if s.get('enabled', True)]
    return enabled
