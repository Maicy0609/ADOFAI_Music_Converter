# -*- coding: utf-8 -*-
"""
angleData模式转换器
使用纯角度控制实现节奏控制

核心原理（参考 pyadofai 库）：
- angleData 存储的是瓷砖的绝对朝向角度，范围 (0, 360]
- 旋转角度（决定节拍）= (angleData[i-1] + 180 - angleData[i]) mod 360
- 如果旋转角度 <= 0，则加 360
- 节拍 = 旋转角度 / 180
- 时间 = 节拍 × 60 / BPM
- Pause 事件可以增加额外的旋转角度（duration * 180°）
"""

from typing import List, Optional
from statistics import median

from .common import (
    MapData,
    TileData,
    EventType,
    Pause
)


class AngleDataConverter:
    """angleData模式转换器"""

    def convert(self, us_delay_list: List[int], base_bpm: Optional[float] = None) -> MapData:
        """
        将微秒延迟列表转换为ADOFAI地图数据
        
        Args:
            us_delay_list: 微秒延迟列表，每个元素表示一个音符的时间间隔
            base_bpm: 基准BPM，如果为None则自动计算
        
        Returns:
            MapData: ADOFAI地图数据对象
        """
        if not us_delay_list:
            return MapData(use_angle_data=True)

        # 计算 RW 模式的 SetSpeed BPM 列表 (实际BPM / 12)
        rw_bpm_list = [60.0 * 1000 * 1000 / us_delay / 12.0 for us_delay in us_delay_list]

        # 确定基准 BPM
        if base_bpm is None:
            base_bpm = median(rw_bpm_list)

        map_data = MapData(use_angle_data=True)
        map_data.map_setting.bpm = base_bpm

        tile_data_list = map_data.tile_data_list

        # 添加起始瓷砖 (floor 0, 角度 = 0)
        tile_data_list.append(TileData(0, angle=0))

        # 当前绝对角度
        current_angle = 0.0

        for i, us_delay in enumerate(us_delay_list):
            # 计算总旋转角度
            total_rotate_angle = us_delay * base_bpm / 60.0 / 1000000.0 * 180.0

            # 计算需要的 Pause duration 和基础旋转角度
            # 基础旋转角度必须在 (0, 360] 范围内
            if total_rotate_angle > 360:
                base_rotate_angle = total_rotate_angle % 360
                if base_rotate_angle < 0.001:
                    base_rotate_angle = 360
                pause_beats = (total_rotate_angle - base_rotate_angle) / 180.0
            else:
                pause_beats = 0
                base_rotate_angle = total_rotate_angle

            # 计算下一个瓷砖的绝对角度
            next_angle = current_angle + 180.0 - base_rotate_angle

            # 规范化到 (0, 360] 范围
            while next_angle <= 0:
                next_angle += 360
            while next_angle > 360:
                next_angle -= 360

            tile_data = TileData(i + 1, angle=next_angle)

            # 如果需要 Pause 事件
            if pause_beats > 0:
                tile_data.get_action_list(EventType.PAUSE).append(Pause(pause_beats))

            tile_data_list.append(tile_data)

            current_angle = next_angle

        return map_data

    @staticmethod
    def get_rotate_angle(angle_data: List[float], index: int) -> float:
        """
        计算从瓷砖 index-1 到瓷砖 index 的旋转角度
        
        Args:
            angle_data: angleData数组
            index: 目标瓷砖索引
        
        Returns:
            float: 旋转角度
        """
        if index <= 0 or index >= len(angle_data):
            return 0.0

        prev_angle = angle_data[index - 1]
        curr_angle = angle_data[index]

        # 规范化角度到 (0, 360]
        if prev_angle <= 0:
            prev_angle += 360
        if curr_angle <= 0:
            curr_angle += 360

        absolute_angle1 = prev_angle + 180
        if absolute_angle1 > 360:
            absolute_angle1 -= 360

        rotate_angle = absolute_angle1 - curr_angle
        if rotate_angle <= 0:
            rotate_angle += 360

        return rotate_angle

    @staticmethod
    def calculate_base_bpm(us_delay_list: List[int]) -> float:
        """
        计算最优基准BPM
        
        Args:
            us_delay_list: 微秒延迟列表
        
        Returns:
            float: 基准BPM
        """
        rw_bpm_list = [60.0 * 1000 * 1000 / us_delay / 12.0 for us_delay in us_delay_list]
        return median(rw_bpm_list)
