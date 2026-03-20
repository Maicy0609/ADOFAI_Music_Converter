# -*- coding: utf-8 -*-
"""
自定义夹角模式转换器 (Custom Angle Mode Converter)
使用 angleData + SetSpeed + Pause 实现节奏控制

核心原理：
- 用户输入自定义夹角 θ（如15°）
- 使用 angleData 存储角度序列，确保每个瓷砖之间的旋转角度固定为 θ
- 角度计算公式：angle[i] = (angle[i-1] + 180 - θ) mod 360
- 魔法数字 = 180/θ（用于BPM补偿）
- 时间 = θ/180 × 60/BPM 秒

特殊处理：
- θ = 0°：不合法，拒绝（无法移动）
- θ = 180°：直线，不需要额外角度调整
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
    """自定义夹角模式转换器（使用angleData）"""

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

        # 计算魔法数字
        magic_number = self.get_magic_number(angle)

        # 添加起始瓷砖 (floor 0, 角度 = 0)
        tile_data_list.append(TileData(0, angle=0))

        # 当前绝对角度
        current_angle = 0.0

        for i, us_delay in enumerate(us_delay_list):
            # 计算需要的BPM
            # 时间 = angle/180 × 60/BPM
            # BPM = angle/180 × 60 × 1000000 / us_delay
            # 但因为魔法数字的关系，实际显示的BPM需要除以magic_number
            to_bpm = 60.0 * 1000 * 1000 / us_delay / magic_number

            # 计算总旋转角度
            # 总旋转角度 = 时间 × BPM / 60 × 180
            #           = us_delay / 1000000 × to_bpm × magic_number / 60 × 180
            #           = us_delay × to_bpm × magic_number / (60 × 1000000) × 180
            total_rotate_angle = us_delay * to_bpm * magic_number / 60.0 / 1000000.0 * 180.0

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
            # 根据pyadofai的解释：
            # rotation_angle = (prev_angle + 180 - curr_angle) mod 360
            # 我们想要 rotation_angle = base_rotate_angle
            # 所以：curr_angle = prev_angle + 180 - base_rotate_angle
            next_angle = current_angle + 180.0 - base_rotate_angle

            # 规范化到 (0, 360] 范围
            while next_angle <= 0:
                next_angle += 360
            while next_angle > 360:
                next_angle -= 360

            tile_data = TileData(i + 1, angle=next_angle)

            # 添加 SetSpeed 事件
            tile_data.get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", to_bpm, 1.0)
            )

            # 如果需要 Pause 事件
            if pause_beats > 0:
                tile_data.get_action_list(EventType.PAUSE).append(Pause(pause_beats))

            tile_data_list.append(tile_data)

            current_angle = next_angle

        return map_data

    @staticmethod
    def get_bpm_list(us_delay_list: List[int], angle: float = 15.0) -> List[float]:
        """
        计算每个延迟对应的BPM值

        Args:
            us_delay_list: 微秒延迟列表
            angle: 夹角度数

        Returns:
            List[float]: BPM列表
        """
        magic_number = AngleCustomConverter.get_magic_number(angle)
        return [60.0 * 1000 * 1000 / us_delay / magic_number for us_delay in us_delay_list]

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
# 注意：PathDataConverter 使用的是 pathData 格式，不是 angleData
# 这个别名仅用于兼容旧代码
PathDataConverter = AngleCustomConverter
