# -*- coding: utf-8 -*-
"""
angleData模式转换器
使用纯角度控制实现节奏控制

核心原理（参考游戏源码 / SharpFAI 的 FloorTimingCalculator）：
- 游戏自带 floor 0 起始砖块（不在 angleData 中），angleData[i] 对应 floor i+1
- 第一段旋转（default → angleData[0]）= 180° - angleData[0]
- 之后第 j 段旋转（j >= 1）= angleData[j-1] + 180 - angleData[j]
- 节拍 = 旋转角度 / 180，时间 = 节拍 × 60 / BPM
- Pause 事件在“出发瓷砖”上增加额外时间（duration 拍）
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

        # 先算出每个延迟对应的“实际旋转角”和需要补的 Pause
        rotations: List[float] = []
        pauses: List[float] = []
        for us_delay in us_delay_list:
            total_rotate_angle = us_delay * base_bpm / 60.0 / 1000000.0 * 180.0

            if total_rotate_angle > 360:
                base_rotate_angle = total_rotate_angle % 360
                if base_rotate_angle < 0.001:
                    base_rotate_angle = 360
                pause_beats = (total_rotate_angle - base_rotate_angle) / 180.0
            else:
                pause_beats = 0
                base_rotate_angle = total_rotate_angle

            rotations.append(base_rotate_angle)
            pauses.append(pause_beats)

        # 游戏自带 floor 0 起始砖块（不在 angleData 中），事件放在这里作用于第一段
        tile_data_list.append(TileData(0, is_default=True))

        # floor i（i >= 1）对应 angleData[i-1]；一共 len(us_delay_list) 块显式瓷砖
        angles: List[float] = [self._normalize_angle(180.0 - rotations[0])]
        for i in range(1, len(us_delay_list)):
            angles.append(self._normalize_angle(angles[-1] + 180.0 - rotations[i]))

        for floor, angle in enumerate(angles, start=1):
            tile_data_list.append(TileData(floor, angle=angle))

        # Pause 在“出发瓷砖”上生效：floor i 控制第 i 段（i=0 为默认砖块）
        for i, pause_beats in enumerate(pauses):
            if pause_beats > 0:
                tile_data_list[i].get_action_list(EventType.PAUSE).append(
                    Pause(pause_beats)
                )

        return map_data

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """规范化到 [0, 360)。"""
        normalized = angle % 360.0
        return 0.0 if abs(normalized) < 1e-12 else normalized

    @staticmethod
    def get_rotate_angle(angle_data: List[float], index: int) -> float:
        """
        计算瓷砖 index 到下一块瓷砖的旋转角度

        Args:
            angle_data: angleData数组
            index: 出发瓷砖索引

        Returns:
            float: 旋转角度
        """
        if index < 0 or index >= len(angle_data):
            return 0.0

        if index == 0:
            return AngleDataConverter._normalize_angle(180.0 - angle_data[0])

        return AngleDataConverter._normalize_angle(
            angle_data[index - 1] + 180.0 - angle_data[index]
        )

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
