# -*- coding: utf-8 -*-
"""
节拍检测器
完全参考 apofai_main_console 的实现

核心算法（来自 apofai）：
1. 计算音频能量信号（样本平方）
2. 使用高斯核进行 FFT 卷积平滑
3. scipy.signal.find_peaks 峰值检测
4. 使用绝对阈值过滤峰值
"""

from typing import List, Optional, Tuple
import numpy as np

try:
    from scipy.fft import fft, ifft
    from scipy.signal import find_peaks
except ImportError:
    print("Error: scipy library is required")
    print("Run: pip install scipy")
    exit(1)


class BeatDetector:
    """节拍检测器（完全参考 apofai 实现）"""

    # apofai 的原始参数
    SIGMA_BASE = 1e-2  # 0.01，基础 sigma 值
    MU = 0.5  # 高斯中心位置（音频中间）

    def __init__(self):
        self.beat_times: List[float] = []
        self.smoothed_signal: Optional[np.ndarray] = None

    def detect(
        self,
        energy_signal: np.ndarray,
        sample_rate: int,
        smoothness: float = 0.0,
        height_min: float = 0.0,
        height_max: float = 32767.0
    ) -> List[float]:
        """
        检测节拍时间点（完全参考 apofai 的实现）

        Args:
            energy_signal: 能量信号（int16 范围）
            sample_rate: 采样率
            smoothness: 平滑度参数（无范围限制！apofai 原版允许任意值）
                - 越小，采音强度越高，按键越密集
                - 越大，采音强度越低，按键越稀疏
                - 默认 0
                - 建议范围: -21 到 5，但可以设置 -100 等极端值
            height_min: 阈值最小值（默认 0）
            height_max: 阈值最大值（默认 32767）

        Returns:
            List[float]: 节拍时间点列表（秒）
        """
        # 时间轴（参考 apofai）
        n = len(energy_signal)
        x = np.linspace(0, n / sample_rate, n, endpoint=False)

        # 计算高斯核（完全参考 apofai）
        # sigma = SIGMA * exp(smoothness * 0.5)
        sigma = self.SIGMA_BASE * np.exp(smoothness * 0.5)
        mu = self.MU * n / sample_rate  # 高斯中心在音频中间

        # 高斯核公式：1/(sqrt(2π)*σ) * exp(-((x-μ)²)/(2σ²))
        gaussian_kernel = 1 / (np.sqrt(2 * np.pi) * sigma) * np.exp(
            -((x - mu) ** 2) / (2 * sigma ** 2)
        )

        # FFT 卷积（参考 apofai 使用 int32）
        y2 = self._convolve_fft(np.int32(energy_signal), gaussian_kernel)

        # 归一化到 int16 范围
        y2 = np.int16((y2 / y2.max()) * 32767)
        self.smoothed_signal = y2

        # 峰值检测（完全参考 apofai）
        peaks = find_peaks(y2, [height_min, height_max])[0]

        # 转换为时间（秒）
        self.beat_times = (peaks / sample_rate).tolist()

        return self.beat_times

    def _convolve_fft(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        使用 FFT 进行快速卷积（完全参考 apofai 的 convfft 函数）

        Args:
            a: 信号（apofai 使用 int32）
            b: 核

        Returns:
            np.ndarray: 卷积结果
        """
        n = len(a)
        m = len(b)

        # FFT 长度：大于等于 n+m-1 的最小 2 的幂
        yn = n + m - 1
        fft_len = 2 ** (int(np.log2(yn)) + 1)

        # FFT 卷积
        a_fft = fft(a, fft_len)
        b_fft = fft(b, fft_len)
        ab_fft = a_fft * b_fft
        y = ifft(ab_fft)

        # 取实部并截断（完全参考 apofai）
        result = np.real(y[int(np.floor(m / 2)):int(np.floor(n + m / 2))])

        return result

    @staticmethod
    def estimate_bpm(beat_times: List[float]) -> float:
        """
        估计 BPM（参考 apofai 的计算方式）

        Args:
            beat_times: 节拍时间点列表

        Returns:
            float: 估计的 BPM
        """
        if len(beat_times) < 2:
            return 120.0  # 默认 BPM

        # 计算节拍间隔
        intervals = np.diff(beat_times)

        # 使用中位数估计（完全参考 apofai）
        median_interval = np.median(intervals)

        # BPM = 60 / 间隔
        bpm = 60.0 / median_interval

        return bpm


def detect_beats(
    energy_signal: np.ndarray,
    sample_rate: int,
    smoothness: float = 0.0,
    height_min: float = 0.0,
    height_max: float = 32767.0
) -> Tuple[List[float], float]:
    """
    便捷函数：检测节拍

    Args:
        energy_signal: 能量信号
        sample_rate: 采样率
        smoothness: 平滑度参数（-5 到 5）
        height_min: 阈值最小值
        height_max: 阈值最大值

    Returns:
        Tuple[List[float], float]: (节拍时间列表, 估计BPM)
    """
    detector = BeatDetector()
    beat_times = detector.detect(
        energy_signal,
        sample_rate,
        smoothness,
        height_min,
        height_max
    )
    bpm = BeatDetector.estimate_bpm(beat_times)
    return beat_times, bpm
