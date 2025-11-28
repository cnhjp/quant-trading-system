"""
标的加载器
从配置文件动态加载启用的标的
"""
import json
import os
from typing import Dict

def load_tickers(config_path: str = "config/tickers.json") -> Dict[str, str]:
    """
    从配置文件加载启用的标的
    
    Args:
        config_path: 标的配置文件路径
        
    Returns:
        Dict: {display_name: symbol} 映射字典
    """
    # 如果配置文件不存在，返回默认标的
    if not os.path.exists(config_path):
        print(f"警告: 标的配置文件不存在: {config_path}，使用默认配置")
        return {
            "SPY (标普500)": "SPY",
            "QQQ (纳指100)": "QQQ",
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取标的配置文件: {e}")
        return {
            "SPY (标普500)": "SPY",
        }
    
    ticker_map = {}
    
    for ticker_config in config.get('tickers', []):
        # 只加载启用的标的
        if not ticker_config.get('enabled', True):
            continue
        
        display_name = ticker_config.get('display_name', '')
        symbol = ticker_config.get('symbol', '')
        
        if display_name and symbol:
            ticker_map[display_name] = symbol
    
    # 确保至少有一个标的
    if not ticker_map:
        print("警告: 没有启用的标的，使用默认 SPY")
        ticker_map = {"SPY (标普500)": "SPY"}
    
    return ticker_map


def get_enabled_tickers(config_path: str = "config/tickers.json") -> list:
    """
    获取所有启用的标的符号列表
    
    Args:
        config_path: 标的配置文件路径
        
    Returns:
        list: 启用的标的符号列表
    """
    if not os.path.exists(config_path):
        return ["SPY", "QQQ"]
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        return ["SPY"]
    
    enabled = [
        t['symbol'] 
        for t in config.get('tickers', []) 
        if t.get('enabled', True)
    ]
    
    return enabled if enabled else ["SPY"]
