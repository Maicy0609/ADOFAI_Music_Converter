# -*- coding: utf-8 -*-
"""
节拍检测器
使用FFT卷积 + 高斯滤波 + 峰值检测

核心算法：
1. 计算音频能量信号（样本平方）
2. 使用高斯核进行FFT卷积平滑
3. 使用scipy.signal.find_peaks检测峰值
"""

from typing import List, Tuple, Optional
import numpy as np

try:
    from scipy.fft import fft, ifft
    from scipy.signal import find_peaks
except ImportError:
    print("Error: scipy library is required")
    print("Run: pip install scipy")
    exit(1)


class BeatDetector:
    """节拍检测器"""

    # 高斯核参数
    SIGMA_BASE = 1e-2  # 基础sigma值
    MU = 0.5           # 高斯中心位置（信号中部）

    def __init__(self):
        self.beat_times: List[float] = []
        self.smoothed_signal: Optional[np.ndarray] = None

    def detect(
        self,
        energy_signal: np.ndarray,
        sample_rate: int,
        smoothness: float = 0.0,
        threshold_min: float = 0.0,
        threshold_max: float = 32767.0
    ) -> List[float]:
        """
        检测节拍时间点

        Args:
            energy_signal: 能量信号
            sample_rate: 采样率
            smoothness: 平滑度参数 (-5 ~ 5)，值越小节拍越密集
            threshold_min: 阈值最小值
            threshold_max: 阈值最大值

        Returns:
            List[float]: 节拍时间点列表（秒）
        """
        # 计算高斯核
        sigma = self.SIGMA_BASE * np.exp(smoothness * 0.5)

        # 生成高斯核
        n = len(energy_signal)
        x = np.linspace(0, n / sample_rate, n, endpoint=False)
        gaussian_kernel = self._gaussian_kernel(x, sigma, n, sample_rate)

        # FFT卷积
        smoothed = self._convolve_fft(energy_signal.astype(np.float64), gaussian_kernel)

        # 归一化
        smoothed = smoothed / smoothed.max() * 32767
        self.smoothed_signal = smoothed.astype(np.int16)

        # 峰值检测
        peaks, _ = find_peaks(
            self.smoothed_signal,
            height=(threshold_min, threshold_max)
        )

        # 转换为时间（秒）
        self.beat_times = (peaks / sample_rate).tolist()

        return self.beat_times

    def _gaussian_kernel(
        self,
        x: np.ndarray,
        sigma: float,
        n: int,
        sample_rate: int
    ) -> np.ndarray:
        """
        生成高斯核

        Args:
            x: 时间轴
            sigma: 标准差
            n: 信号长度
            sample_rate: 采样率

        Returns:
            np.ndarray: 高斯核
        """
        mu = self.MU * n / sample_rate
        kernel = 1 / (np.sqrt(2 * np.pi) * sigma) * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))
        return kernel

    def _convolve_fft(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        使用FFT进行快速卷积

        Args:
            a: 信号
            b: 核

        Returns:
            np.ndarray: 卷积结果
        """
        n = len(a)
        m = len(b)

        # FFT长度（补零到2的幂次）
        fft_len = 2 ** (int(np.log2(n + m - 1)) + 1)

        # FFT卷积
        a_fft = fft(a, fft_len)
        b_fft = fft(b, fft_len)
        result = ifft(a_fft * b_fft)

        # 取实部并截断到正确长度
        start = int(np.floor(m / 2))
        end = int(np.floor(n + m / 2))
        return np.real(result[start:end])

    @staticmethod
    def estimate_bpm(beat_times: List[float]) -> float:
        """
        估计BPM

        Args:
            beat_times: 节拍时间点列表

        Returns:
            float: 估计的BPM
        """
        if len(beat_times) < 2:
            return 120.0  # 默认BPM

        # 计算节拍间隔
        intervals = np.diff(beat_times)

        # 使用中位数估计
        median_interval = np.median(intervals)

        # BPM = 60 / 间隔
        bpm = 60.0 / median_interval

        return bpm


def detect_beats(
    energy_signal: np.ndarray,
    sample_rate: int,
    smoothness: float = 0.0,
    threshold: float = 0.0
) -> Tuple[List[float], float]:
    """
    便捷函数：检测节拍

    Args:
        energy_signal: 能量信号
        sample_rate: 采样率
        smoothness: 平滑度
        threshold: 阈值

    Returns:
        Tuple[List[float], float]: (节拍时间列表, 估计BPM)
    """
    detector = BeatDetector()
    beat_times = detector.detect(
        energy_signal,
        sample_rate,
        smoothness,
        threshold,
        32767.0
    )
    bpm = BeatDetector.estimate_bpm(beat_times)
    return beat_times, bpm
