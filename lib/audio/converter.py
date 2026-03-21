# -*- coding: utf-8 -*-
"""
音频转换器
将检测到的节拍时间转换为ADOFAI谱面

提供三种模式：
1. AudioAngleConverter - 纯angleData模式（固定BPM，动态角度）
2. AudioZipperConverter - 拉链模式（固定角度，动态BPM）
3. FullSampleConverter - 全采音模式（直线轨道，打击音播放音频）

核心原则：前两种模式生成的拍子绝对时间完全相同！
"""

from typing import List, Optional, Tuple
from statistics import median
import sys
import os
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from lib.midi.common import (
    MapData,
    TileData,
    MapSetting,
    EventType,
    SetSpeed,
    Pause,
    SetHitsound
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

    拉链模式原理：
    - 用户设置夹角 θ（如15°）
    - angleData 序列：[0, 180-θ, 0, 180-θ, ...]
    - 例如 θ=15° 时：angleData = [0, 165, 0, 165, 0, 165, ...]
    - 旋转角度固定为 θ，方向交替（左转、右转、左转...）
    - 形成锯齿/拉链形状

    时间公式：时间 = θ/180 × 60/BPM
    因此：BPM = θ/180 × 60/时间
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
        计算魔法数字（BPM倍增因子）

        Args:
            angle: 夹角度数

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

        map_data = MapData(use_angle_data=True)

        # 设置基础BPM（使用估计值）
        map_data.map_setting.bpm = estimated_bpm

        # 设置音频偏移
        if audio_offset != 0:
            map_data.map_setting.offset = int(audio_offset)

        tile_data_list = map_data.tile_data_list

        # 特殊情况：180° 夹角
        # angleData = [0, 0, 0, ...]，每个旋转都是 180°
        # 不需要 SetSpeed，直接用谱面 BPM
        if self.base_angle == 180.0:
            # 添加起始瓷砖
            tile_data_list.append(TileData(0, angle=0))
            
            for i in range(1, len(beat_times)):
                # 所有角度都是 0
                tile_data_list.append(TileData(i, angle=0))
            
            return map_data

        # 计算交替角度
        # 拉链序列：[0, 180-angle, 0, 180-angle, ...]
        # 例如 angle=15° 时：[0, 165, 0, 165, ...]
        alternate_angle = 180.0 - self.base_angle

        # 添加起始瓷砖
        tile_data_list.append(TileData(0, angle=0))

        # 计算节拍间隔
        intervals = []
        for i in range(1, len(beat_times)):
            intervals.append(beat_times[i] - beat_times[i - 1])

        for i, interval in enumerate(intervals):
            # 计算显示BPM
            # 时间 = angle/180 × 60/BPM
            # BPM = angle/180 × 60/时间
            display_bpm = self.base_angle / 180.0 * 60.0 / interval

            # 拉链模式：角度在 0 和 (180-angle) 之间交替
            # tile 1: 0 → alternate_angle (逆时针转 angle°)
            # tile 2: alternate_angle → 0 (顺时针转 angle°)
            # tile 3: 0 → alternate_angle
            # ...
            if (i + 1) % 2 == 1:  # 奇数位置：1, 3, 5, ...
                next_angle = alternate_angle
            else:  # 偶数位置：2, 4, 6, ...
                next_angle = 0.0

            tile_data = TileData(i + 1, angle=next_angle)

            # 添加SetSpeed事件
            tile_data.get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", display_bpm, 1.0)
            )

            tile_data_list.append(tile_data)

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


class FullSampleConverter:
    """
    全采音模式转换器
    基于零阶保持采样重构原理，将音频转换为打击音序列

    核心原理：
    - 将音频重采样到目标伪采样率（如8000Hz）
    - 每个采样点对应一个砖块
    - 砖块设置打击音(Kick)和音量(0-100)
    - 轨道为直线（角度0°）
    - BPM = 伪采样率 × 60

    时间公式：
    - 单帧时长 = 1 / 伪采样率
    - BPM = 伪采样率 × 60
    - 例如：8000Hz → BPM = 480,000
    """

    # 默认伪采样率
    DEFAULT_SAMPLE_RATE = 8000
    # 目标输出采样率（保持核长度）
    OUTPUT_SAMPLE_RATE = 48000
    # 默认打击音
    DEFAULT_HITSOUND = "Kick"
    # 默认游戏音效类型
    DEFAULT_GAME_SOUND = "Hitsound"

    def __init__(self, pseudo_sample_rate: float = 8000.0, use_float_volume: bool = False):
        """
        初始化

        Args:
            pseudo_sample_rate: 伪采样率（Hz），默认8000
            use_float_volume: 是否使用浮点数音量，False则使用整数
        """
        self._validate_sample_rate(pseudo_sample_rate)
        self.pseudo_sample_rate = pseudo_sample_rate
        self.use_float_volume = use_float_volume

    def _validate_sample_rate(self, sample_rate: float) -> None:
        """验证采样率合法性"""
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be greater than 0, got {sample_rate}")
        if sample_rate > self.OUTPUT_SAMPLE_RATE:
            raise ValueError(f"Sample rate cannot exceed {self.OUTPUT_SAMPLE_RATE}, got {sample_rate}")

    @property
    def bpm(self) -> float:
        """计算谱面BPM"""
        return self.pseudo_sample_rate * 60.0

    def convert(
        self,
        audio_data: np.ndarray,
        original_sample_rate: int,
        audio_offset: float = 0.0,
        song_filename: str = ""
    ) -> MapData:
        """
        将音频数据转换为全采音谱面

        Args:
            audio_data: 音频数据（numpy数组，单声道）
            original_sample_rate: 原始采样率
            audio_offset: 音频偏移（毫秒）
            song_filename: 歌曲文件名

        Returns:
            MapData: 谱面数据
        """
        map_data = MapData(use_angle_data=True)

        # 设置BPM
        map_data.map_setting.bpm = self.bpm

        # 设置打击音默认值
        map_data.map_setting.hitsound = self.DEFAULT_HITSOUND
        map_data.map_setting.hitsound_volume = 100

        # 设置音频偏移
        if audio_offset != 0:
            map_data.map_setting.offset = int(audio_offset)

        # 设置歌曲文件名
        if song_filename:
            map_data.map_setting.song_filename = song_filename

        tile_data_list = map_data.tile_data_list

        # 重采样到伪采样率
        resampled_data = self._resample_audio(audio_data, original_sample_rate)

        # 计算音量序列
        volumes = self._calculate_volumes(resampled_data)

        # 生成谱面
        # 添加起始瓷砖 (floor 0)
        tile_data_list.append(TileData(0, angle=0))

        # 为每个采样点添加瓷砖和SetHitsound事件
        for i, volume in enumerate(volumes):
            tile_data = TileData(i + 1, angle=0)  # 直线轨道，所有角度为0

            # 添加SetHitsound事件
            tile_data.get_action_list(EventType.SET_HITSOUND).append(
                SetHitsound(
                    game_sound=self.DEFAULT_GAME_SOUND,
                    hitsound=self.DEFAULT_HITSOUND,
                    hitsound_volume=volume
                )
            )

            tile_data_list.append(tile_data)

        return map_data

    def _resample_audio(self, audio_data: np.ndarray, original_sample_rate: int) -> np.ndarray:
        """
        使用scipy.signal.resample_poly重采样音频

        Args:
            audio_data: 原始音频数据
            original_sample_rate: 原始采样率

        Returns:
            np.ndarray: 重采样后的音频数据
        """
        from scipy.signal import resample_poly

        # 计算重采样比率
        # resample_poly 使用 up/down 参数
        # 新采样率 = 原采样率 * up / down
        # 因此 up/down = 新采样率 / 原采样率

        # 使用最大公约数简化分数
        from math import gcd

        target_rate = int(self.pseudo_sample_rate)
        orig_rate = int(original_sample_rate)

        # 计算 up 和 down
        common_divisor = gcd(target_rate, orig_rate)
        up = target_rate // common_divisor
        down = orig_rate // common_divisor

        # 重采样
        resampled = resample_poly(audio_data, up, down)

        return resampled

    def _calculate_volumes(self, audio_data: np.ndarray) -> List[float]:
        """
        计算每个采样点的音量

        Args:
            audio_data: 重采样后的音频数据

        Returns:
            List[float]: 音量列表（0-100）
        """
        # 取绝对值获取幅度
        amplitudes = np.abs(audio_data)

        # 归一化到 0-1
        max_amplitude = np.max(amplitudes)
        if max_amplitude > 0:
            normalized = amplitudes / max_amplitude
        else:
            normalized = amplitudes

        # 映射到 0-100
        volumes = normalized * 100.0

        # 根据设置决定是否转换为整数
        if not self.use_float_volume:
            volumes = np.round(volumes).astype(int)

        return volumes.tolist()

    @staticmethod
    def load_audio_file(file_path: str) -> Tuple[np.ndarray, int]:
        """
        加载 WAV 音频文件

        Args:
            file_path: 音频文件路径（仅支持 WAV 格式）

        Returns:
            Tuple[np.ndarray, int]: (音频数据, 采样率)
        """
        from scipy.io import wavfile

        # 读取 WAV 文件
        sample_rate, audio_data = wavfile.read(file_path)

        # 转换数据类型
        if audio_data.dtype == np.int16:
            # int16 范围 -32768 到 32767，归一化到 -1.0 到 1.0
            audio_data = audio_data.astype(np.float64) / 32768.0
        elif audio_data.dtype == np.int32:
            # int32 范围
            audio_data = audio_data.astype(np.float64) / 2147483648.0
        elif audio_data.dtype == np.uint8:
            # uint8 范围 0 到 255
            audio_data = (audio_data.astype(np.float64) - 128.0) / 128.0
        else:
            audio_data = audio_data.astype(np.float64)

        # 转换为单声道
        if len(audio_data.shape) > 1:
            # 多声道，取平均值
            audio_data = np.mean(audio_data, axis=1)

        return audio_data, sample_rate
