# -*- coding: utf-8 -*-
"""
音频转换器
将检测到的节拍时间转换为ADOFAI谱面

提供两种模式：
1. AudioAngleConverter - 纯angleData模式（固定BPM，动态角度）
2. AudioZipperConverter - 拉链模式（固定角度，动态BPM）

核心原则：两种模式生成的拍子绝对时间完全相同！
"""

from typing import List, Optional
from statistics import median
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from lib.midi.common import (
    MapData,
    TileData,
    MapSetting,
    EventType,
    SetSpeed,
    Pause
)


class AudioAngleConverter:
    """
    纯angleData模式转换器
    固定BPM，通过角度变化控制时间

    时间公式：时间 = 旋转角度/180 × 60/BPM
    因此：旋转角度 = 时间 × BPM × 180 / 60
    """

    def __init__(self, base_bpm: Optional[float] = None):
        """
        初始化

        Args:
            base_bpm: 基准BPM，None则自动计算
        """
        self.base_bpm = base_bpm

    def convert(
        self,
        beat_times: List[float],
        estimated_bpm: float,
        audio_offset: float = 0.0
    ) -> MapData:
        """
        将节拍时间转换为谱面

        Args:
            beat_times: 节拍时间点列表（秒）
            estimated_bpm: 估计的BPM（用于自动计算base_bpm）
            audio_offset: 音频偏移（毫秒）

        Returns:
            MapData: 谱面数据
        """
        if not beat_times:
            return MapData(use_angle_data=True)

        # 确定BPM
        bpm = self.base_bpm if self.base_bpm else estimated_bpm

        map_data = MapData(use_angle_data=True)
        map_data.map_setting.bpm = bpm

        # 设置音频偏移
        if audio_offset != 0:
            map_data.map_setting.offset = int(audio_offset)

        tile_data_list = map_data.tile_data_list

        # 添加起始瓷砖
        tile_data_list.append(TileData(0, angle=0))

        # 计算节拍间隔
        intervals = []
        for i in range(1, len(beat_times)):
            intervals.append(beat_times[i] - beat_times[i - 1])

        # 当前绝对角度
        current_angle = 0.0

        for i, interval in enumerate(intervals):
            # 计算总旋转角度
            # 时间 = 旋转角度/180 × 60/BPM
            # 旋转角度 = 时间 × BPM × 180 / 60
            total_rotate_angle = interval * bpm * 180.0 / 60.0

            # 处理大于360度的情况
            if total_rotate_angle > 360:
                base_rotate_angle = total_rotate_angle % 360
                if base_rotate_angle < 0.001:
                    base_rotate_angle = 360
                pause_beats = (total_rotate_angle - base_rotate_angle) / 180.0
            else:
                pause_beats = 0
                base_rotate_angle = total_rotate_angle

            # 计算下一个角度
            next_angle = current_angle + 180.0 - base_rotate_angle

            # 规范化到 (0, 360]
            while next_angle <= 0:
                next_angle += 360
            while next_angle > 360:
                next_angle -= 360

            tile_data = TileData(i + 1, angle=next_angle)

            # 添加Pause事件
            if pause_beats > 0:
                tile_data.get_action_list(EventType.PAUSE).append(Pause(pause_beats))

            tile_data_list.append(tile_data)
            current_angle = next_angle

        return map_data


class AudioZipperConverter:
    """
    拉链模式转换器
    固定角度，通过BPM变化控制时间

    时间公式：时间 = 固定角度/180 × 60/BPM
    因此：BPM = 固定角度/180 × 60/时间
    """

    def __init__(self, base_angle: float = 15.0):
        """
        初始化

        Args:
            base_angle: 固定夹角（度），默认15°
        """
        self._validate_angle(base_angle)
        self.base_angle = base_angle

    def _validate_angle(self, angle: float) -> None:
        """验证角度合法性"""
        if angle <= 0:
            raise ValueError(f"Angle must be greater than 0°, got {angle}°")
        if angle > 180:
            raise ValueError(f"Angle must not exceed 180°, got {angle}°")

    @staticmethod
    def get_magic_number(angle: float) -> float:
        """
        计算魔法数字

        Args:
            angle: 夹角

        Returns:
            float: 魔法数字 = 180 / angle
        """
        return 180.0 / angle

    def convert(
        self,
        beat_times: List[float],
        estimated_bpm: float,
        audio_offset: float = 0.0
    ) -> MapData:
        """
        将节拍时间转换为谱面

        Args:
            beat_times: 节拍时间点列表（秒）
            estimated_bpm: 估计的BPM（用于设置谱面基础BPM）
            audio_offset: 音频偏移（毫秒）

        Returns:
            MapData: 谱面数据
        """
        if not beat_times:
            return MapData(use_angle_data=True)

        # 计算魔法数字
        magic_number = self.get_magic_number(self.base_angle)

        map_data = MapData(use_angle_data=True)

        # 设置基础BPM（使用估计值）
        map_data.map_setting.bpm = estimated_bpm

        # 设置音频偏移
        if audio_offset != 0:
            map_data.map_setting.offset = int(audio_offset)

        tile_data_list = map_data.tile_data_list

        # 添加起始瓷砖
        tile_data_list.append(TileData(0, angle=0))

        # 计算节拍间隔
        intervals = []
        for i in range(1, len(beat_times)):
            intervals.append(beat_times[i] - beat_times[i - 1])

        # 当前绝对角度
        current_angle = 0.0

        for i, interval in enumerate(intervals):
            # 计算需要的BPM
            # 时间 = 固定角度/180 × 60/BPM
            # BPM = 固定角度/180 × 60/时间
            # 但实际显示BPM需要除以魔法数字
            # 实际BPM = 60 / 时间间隔（秒）
            # 显示BPM = 实际BPM / 魔法数字
            actual_bpm = 60.0 / interval
            display_bpm = actual_bpm / magic_number * magic_number  # 保持一致性

            # 简化：直接计算需要的显示BPM
            # 时间 = angle/180 × 60/display_bpm
            # display_bpm = angle/180 × 60/时间
            to_bpm = self.base_angle / 180.0 * 60.0 / interval

            # 计算总旋转角度
            total_rotate_angle = self.base_angle

            # 计算下一个角度
            next_angle = current_angle + 180.0 - total_rotate_angle

            # 规范化到 (0, 360]
            while next_angle <= 0:
                next_angle += 360
            while next_angle > 360:
                next_angle -= 360

            tile_data = TileData(i + 1, angle=next_angle)

            # 添加SetSpeed事件
            tile_data.get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", to_bpm, 1.0)
            )

            # 注意：拉链模式下，如果时间间隔很大，仍然需要Pause
            # 但因为角度固定为base_angle，所以需要在计算中处理
            # 实际上，如果interval很大，to_bpm会很小，这是允许的
            # ADOFAI的BPM下限是有限制的，如果太低需要Pause

            # 检查是否需要Pause（当时间间隔超过一拍时）
            # 一拍时间 = 60/estimated_bpm
            # 如果interval > 60/estimated_bpm，需要额外处理
            # 但这里我们保持简化，让BPM自由变化

            tile_data_list.append(tile_data)
            current_angle = next_angle

        return map_data

    @staticmethod
    def calculate_display_bpm(interval: float, angle: float) -> float:
        """
        计算显示BPM

        Args:
            interval: 时间间隔（秒）
            angle: 固定角度

        Returns:
            float: 显示BPM
        """
        return angle / 180.0 * 60.0 / interval
