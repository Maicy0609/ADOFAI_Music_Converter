# -*- coding: utf-8 -*-
"""
节拍检测器
支持两种模式：
1. 峰值采样 - 只采集峰值点，可调阈值
2. 采样点全采样 - 采集每个采样点
"""

from typing import List, Optional, Tuple
import numpy as np

try:
    from scipy.signal import find_peaks
except ImportError:
    print("Error: scipy library is required")
    print("Run: pip install scipy")
    exit(1)


class BeatDetector:
    """节拍检测器"""

    def __init__(self):
        self.beat_times: List[float] = []
        self.smoothed_signal: Optional[np.ndarray] = None

    def detect_peaks(
        self,
        energy_signal: np.ndarray,
        sample_rate: int,
        height_min: float = 0.0,
        height_max: float = 32767.0
    ) -> List[float]:
        """
        峰值采样模式：检测峰值点

        Args:
            energy_signal: 能量信号（int16 范围）
            sample_rate: 采样率
            height_min: 阈值最小值（默认 0）
            height_max: 阈值最大值（默认 32767）

        Returns:
            List[float]: 节拍时间点列表（秒）
        """
        self.smoothed_signal = energy_signal

        # 峰值检测
        peaks = find_peaks(energy_signal, [height_min, height_max])[0]

        print(f"  峰值采样: 阈值=[{height_min}, {height_max}], 找到 {len(peaks)} 个峰值")

        # 转换为时间（秒）
        self.beat_times = (peaks / sample_rate).tolist()

        return self.beat_times

    def detect_all_samples(
        self,
        sample_rate: int,
        total_samples: int
    ) -> List[float]:
        """
        采样点全采样模式：采集每个采样点

        Args:
            sample_rate: 采样率
            total_samples: 总采样点数

        Returns:
            List[float]: 节拍时间点列表（秒）
        """
        # 每个采样点的时间
        self.beat_times = [i / sample_rate for i in range(total_samples)]

        print(f"  采样点全采样: {total_samples:,} 个采样点")
        print(f"  警告: 这将生成 {total_samples:,} 个瓷砖！")

        return self.beat_times

    @staticmethod
    def estimate_bpm(beat_times: List[float]) -> float:
        """
        估计 BPM

        Args:
            beat_times: 节拍时间点列表

        Returns:
            float: 估计的 BPM
        """
        if len(beat_times) < 2:
            return 120.0  # 默认 BPM

        # 计算节拍间隔
        intervals = np.diff(beat_times)

        # 使用中位数估计
        median_interval = np.median(intervals)

        # BPM = 60 / 间隔
        bpm = 60.0 / median_interval

        return bpm
