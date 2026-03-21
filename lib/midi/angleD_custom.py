# -*- coding: utf-8 -*-
"""
拉链夹角模式转换器 (Zipper Angle Mode Converter)
使用 angleData + SetSpeed 实现节奏控制

核心原理：
- 用户输入夹角 θ（如15°）
- 旋转角度固定为 θ，方向交替
- angleData 序列：[0, 180-θ, 0, 180-θ, ...]
- 例如 θ=15° 时：angleData = [0, 165, 0, 165, 0, 165, ...]
- 时间公式：时间 = θ/180 × 60/BPM
- 显示BPM = θ/180 × 60/时间

旋转方向：
- 从 0 到 (180-θ)：逆时针旋转 θ°
- 从 (180-θ) 到 0：顺时针旋转 θ°
- 形成锯齿/拉链形状

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
    Pause
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

        # 计算交替角度
        # 拉链序列：[0, 180-angle, 0, 180-angle, ...]
        # 例如 angle=15° 时：[0, 165, 0, 165, ...]
        alternate_angle = 180.0 - angle

        # 添加起始瓷砖 (floor 0, 角度 = 0)
        tile_data_list.append(TileData(0, angle=0))

        for i, us_delay in enumerate(us_delay_list):
            # 计算时间（秒）
            time_seconds = us_delay / 1000000.0
            
            # 计算显示BPM
            # 时间 = angle/180 × 60/BPM
            # BPM = angle/180 × 60/时间
            display_bpm = angle / 180.0 * 60.0 / time_seconds

            # 拉链模式：角度在 0 和 (180-angle) 之间交替
            # angleData = [0, 165, 0, 165, ...]
            # - floor 1: 165°
            # - floor 2: 0°
            # - floor 3: 165°
            # - floor 4: 0°
            if (i + 1) % 2 == 1:  # 奇数位置：1, 3, 5, ...
                next_angle = alternate_angle
            else:  # 偶数位置：2, 4, 6, ...
                next_angle = 0.0

            tile_data = TileData(i + 1, angle=next_angle)

            # 添加 SetSpeed 事件（从 floor 1 开始）
            tile_data.get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", display_bpm, 1.0)
            )

            # 添加 Twirl 事件（从 floor 2 开始）
            if i + 1 >= 2:
                from .common import Twirl
                tile_data.get_action_list(EventType.TWIRL).append(Twirl())

            tile_data_list.append(tile_data)

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
