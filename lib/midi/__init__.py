# -*- coding: utf-8 -*-
"""
lib.midi - MIDI转换核心模块

包含:
- angleD_custom: 自定义夹角模式实现 (原pathD)
- angleD: angleData模式实现
- common: 共享数据结构和工具
"""

from .common import (
    MidiParser,
    Melody,
    MapSetting,
    TileData,
    MapData,
    EventType,
    Action,
    SetSpeed,
    Twirl,
    Pause,
    TileAngle,
    CHAR_TO_TILE_ANGLE
)

from .angleD_custom import AngleCustomConverter, PathDataConverter
from .angleD import AngleDataConverter

__all__ = [
    # 转换器
    'AngleCustomConverter',
    'PathDataConverter',  # 向后兼容别名
    'AngleDataConverter',
    # 解析器
    'MidiParser',
    # 数据结构
    'Melody',
    'MapSetting',
    'TileData',
    'MapData',
    # 枚举
    'EventType',
    'TileAngle',
    'CHAR_TO_TILE_ANGLE',
    # 动作
    'Action',
    'SetSpeed',
    'Twirl',
    'Pause'
]
