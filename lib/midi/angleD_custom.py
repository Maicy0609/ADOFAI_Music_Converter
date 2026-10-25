# -*- coding: utf-8 -*-
"""
拉链夹角模式转换器 (Zipper Angle Mode Converter)
使用 angleData + SetSpeed 实现节奏控制

核心原理：
- 用户输入夹角 θ（如15°）
- 旋转角度固定为 θ，方向交替
- 游戏自带 floor 0 起始砖块；angleData 从 0° 开始：
  [0, 180-θ, 0, 180-θ, ...]（例如 θ=15° → [0, 165, 0, 165, ...]）
- 第一段固定旋转 180°；之后每段旋转 θ，方向逐块交替（Twirl）
- 时间：第一段 = 60/BPM，其余 = θ/180 × 60/BPM
- 因此 floor 0 的 BPM = 60/时间，其余显示BPM = θ/180 × 60/时间

特殊处理：
- θ = 0°：不合法，拒绝（无法移动）
- θ = 180°：直线，角度序列 [0, 0, 0, ...]
"""

from typing import List, Optional, Tuple

from .common import (
    MapData,
    TileData,
    EventType,
    SetSpeed,
    Twirl
)


class AngleCustomConverter:
    """拉链夹角模式转换器（使用angleData）"""

    # 最小有效夹角（度）
    MIN_ANGLE = 0.001
    # 最大有效夹角（度）
    MAX_ANGLE = 180.0

    def __init__(self, base_angle: float = 15.0):
        """
        初始化转换器

        Args:
            base_angle: 基准夹角（度），默认15°
        """
        self.base_angle = base_angle
        self._validate_angle(base_angle)

    def _validate_angle(self, angle: float) -> None:
        """
        验证夹角是否合法

        Args:
            angle: 夹角度数

        Raises:
            ValueError: 当夹角不合法时
        """
        if angle <= 0:
            raise ValueError(f"Invalid angle: {angle}°. Angle must be greater than 0°.")
        if angle > 180:
            raise ValueError(f"Invalid angle: {angle}°. Angle must not exceed 180°.")

    @staticmethod
    def is_valid_angle(angle: float) -> Tuple[bool, str]:
        """
        检查夹角是否合法

        Args:
            angle: 夹角度数

        Returns:
            Tuple[bool, str]: (是否合法, 错误信息)
        """
        if angle <= 0:
            return False, "Angle must be greater than 0°"
        if angle > 180:
            return False, "Angle must not exceed 180°"
        return True, ""

    @staticmethod
    def get_magic_number(angle: float) -> float:
        """
        计算魔法数字（BPM倍增因子）

        Args:
            angle: 夹角度数

        Returns:
            float: 魔法数字 = 180 / angle
        """
        return 180.0 / angle

    def convert(self, us_delay_list: List[int], base_angle: Optional[float] = None) -> MapData:
        """
        将微秒延迟列表转换为ADOFAI地图数据

        Args:
            us_delay_list: 微秒延迟列表，每个元素表示一个音符的时间间隔
            base_angle: 基准夹角（度），如果为None则使用实例的base_angle

        Returns:
            MapData: ADOFAI地图数据对象
        """
        if not us_delay_list:
            return MapData(use_angle_data=True)

        # 使用传入的夹角或实例夹角
        angle = base_angle if base_angle is not None else self.base_angle
        self._validate_angle(angle)

        map_data = MapData(use_angle_data=True)
        tile_data_list = map_data.tile_data_list

        # 游戏自带 floor 0 起始砖块（不在 angleData 中）。
        # angleData 从 0 开始、按 [0, 180-angle, 0, 180-angle, ...] 排列。
        alternate_angle = 180.0 - angle
        count = len(us_delay_list)

        tile_data_list.append(TileData(0, is_default=True))

        for i in range(count):
            tile_data_list.append(
                TileData(i + 1, angle=0.0 if i % 2 == 0 else alternate_angle)
            )

        # 第一段：默认砖块 0° → angleData[0]=0°，固定 180°
        tile_data_list[0].get_action_list(EventType.SET_SPEED).append(
            SetSpeed("Bpm", 60.0 / (us_delay_list[0] / 1000000.0), 1.0)
        )

        # 之后每段：floor i → floor i+1 由 floor i 的 SetSpeed + Twirl 控制
        # 第二段（0° → 165°）本身就走 15° 近路，从 floor 2 开始才需要 Twirl
        for i in range(1, count):
            time_seconds = us_delay_list[i] / 1000000.0
            display_bpm = angle / 180.0 * 60.0 / time_seconds
            tile_data_list[i].get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", display_bpm, 1.0)
            )
            if i >= 2:
                tile_data_list[i].get_action_list(EventType.TWIRL).append(Twirl())

        return map_data

    @staticmethod
    def get_bpm_list(us_delay_list: List[int], angle: float = 15.0) -> List[float]:
        """
        计算每个延迟对应的显示BPM值

        Args:
            us_delay_list: 微秒延迟列表
            angle: 夹角度数

        Returns:
            List[float]: 显示BPM列表
        """
        return [angle / 180.0 * 60.0 * 1000000.0 / us_delay for us_delay in us_delay_list]

    @staticmethod
    def calculate_base_bpm(us_delay_list: List[int], angle: float = 15.0) -> float:
        """
        计算最优基准BPM（用于固定BPM模式）

        Args:
            us_delay_list: 微秒延迟列表
            angle: 夹角度数

        Returns:
            float: 基准BPM
        """
        from statistics import median
        bpm_list = AngleCustomConverter.get_bpm_list(us_delay_list, angle)
        return median(bpm_list)


# 为了向后兼容，保留 PathDataConverter 别名
PathDataConverter = AngleCustomConverter
