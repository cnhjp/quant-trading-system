"""
策略模块
从配置文件动态加载策略
"""
from .base import BaseStrategy
from .liquidity_grab import LiquidityGrabStrategy
from .trend_confluence import TrendConfluenceStrategy
from .mean_reversion import MeanReversionStrategy
from .daily_dca import DailyDCAStrategy
from .pyramid_grid import PyramidGridStrategy
from .ma200_trend import MA200TrendStrategy
from .turn_of_month import TurnOfTheMonthStrategy
from .vix_switch import VIXSwitchStrategy

__all__ = [
    'BaseStrategy',
    'LiquidityGrabStrategy',
    'TrendConfluenceStrategy',
    'MeanReversionStrategy',
    'DailyDCAStrategy',
    'PyramidGridStrategy',
    'MA200TrendStrategy',
    'TurnOfTheMonthStrategy',
    'VIXSwitchStrategy',
]
