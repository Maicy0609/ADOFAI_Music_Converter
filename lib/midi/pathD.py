# -*- coding: utf-8 -*-
"""
pathData模式转换器
使用 SetSpeed + Twirl 实现节奏控制

核心原理：
- pathData 使用 RWRW... 模式（0°, 165°, 0°, 165°, ...）
- Twirl 事件使实际角度变为 180-165 = 15°
- 因此 BPM 被"加速"12倍（180/15 = 12）
- 时间 = 15/180 × 60/BPM 秒
"""

from typing import List

from .common import (
    MapData,
    TileData,
    TileAngle,
    EventType,
    SetSpeed,
    Twirl
)


class PathDataConverter:
    """pathData模式转换器"""

    def __init__(self):
        self.floor = 0

    def convert(self, us_delay_list: List[int]) -> MapData:
        """
        将微秒延迟列表转换为ADOFAI地图数据
        
        Args:
            us_delay_list: 微秒延迟列表，每个元素表示一个音符的时间间隔
        
        Returns:
            MapData: ADOFAI地图数据对象
        """
        map_data = MapData(use_angle_data=False)
        tile_data_list = map_data.tile_data_list
        self.floor = 0

        # 添加起始瓷砖
        tile_data_list.append(self._get_tile_data())

        for us_delay in us_delay_list:
            # BPM = 60 * 1000000 / us_delay / 12
            # 除以 12 是因为实际角度是 15° 而不是 180°
            to_bpm = 60.0 * 1000 * 1000 / us_delay / 12.0

            tile_data = self._get_tile_data()
            tile_data.get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", to_bpm, 1.0)
            )
            tile_data_list.append(tile_data)

        return map_data

    def _get_tile_data(self) -> TileData:
        """获取pathData模式的瓷砖数据"""
        if self.floor == 0:
            tile_angle = TileAngle.NONE
        elif self.floor % 2 == 0:
            tile_angle = TileAngle._165
        else:
            tile_angle = TileAngle._0

        tile_data = TileData(self.floor, tile_angle=tile_angle)

        if self.floor > 1:
            tile_data.get_action_list(EventType.TWIRL).append(Twirl())

        self.floor += 1
        return tile_data

    @staticmethod
    def get_bpm_list(us_delay_list: List[int]) -> List[float]:
        """
        计算每个延迟对应的BPM值
        
        Args:
            us_delay_list: 微秒延迟列表
        
        Returns:
            List[float]: BPM列表
        """
        return [60.0 * 1000 * 1000 / us_delay / 12.0 for us_delay in us_delay_list]
