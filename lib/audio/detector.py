# -*- coding: utf-8 -*-
"""
节拍检测器
参考 apofai 的实现：使用 FFT 卷积 + 高斯平滑 + 峰值检测

核心算法（来自 apofai）：
1. 计算音频能量信号（样本平方）
2. 使用高斯核进行 FFT 卷积平滑
3. 峰值检测
4. 根据采样百分比保留最强峰值
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
    """节拍检测器（参考 apofai 实现）"""

    # apofai 的原始参数
    SIGMA_BASE = 1e-2  # 0.01
    MU = 0.5  # 高斯中心位置

    def __init__(self):
        self.beat_times: List[float] = []
        self.smoothed_signal: Optional[np.ndarray] = None

    def detect(
        self,
        energy_signal: np.ndarray,
        sample_rate: int,
        sample_percent: float = 100.0,
        threshold_min: float = 0.0,
        threshold_max: float = 32767.0
    ) -> List[float]:
        """
        检测节拍时间点

        Args:
            energy_signal: 能量信号（已归一化到 int16 范围）
            sample_rate: 采样率
            sample_percent: 采样百分比 (1-100)
                - 100: 检测所有峰值（最密集）
                - 50: 只保留最强的50%峰值
                - 10: 只保留最强的10%峰值
            threshold_min: 阈值最小值（默认 0）
            threshold_max: 阈值最大值（默认 32767）

        Returns:
            List[float]: 节拍时间点列表（秒）
        """
        # 限制采样百分比范围
        sample_percent = max(1.0, min(100.0, sample_percent))

        # 时间轴
        n = len(energy_signal)
        x = np.linspace(0, n / sample_rate, n, endpoint=False)

        # 计算高斯核（参考 apofai）
        # sigma = SIGMA_BASE * exp(smoothness * 0.5)
        # 这里 smoothness 固定为 0，所以 sigma = SIGMA_BASE = 0.01
        sigma = self.SIGMA_BASE
        mu = self.MU * n / sample_rate

        # 高斯核公式：1/(sqrt(2π)*σ) * exp(-((x-μ)²)/(2σ²))
        gaussian_kernel = 1 / (np.sqrt(2 * np.pi) * sigma) * np.exp(
            -((x - mu) ** 2) / (2 * sigma ** 2)
        )

        # FFT 卷积
        smoothed = self._convolve_fft(energy_signal.astype(np.float64), gaussian_kernel)

        # 归一化到 int16 范围
        if smoothed.max() > 0:
            smoothed = smoothed / smoothed.max() * 32767
        self.smoothed_signal = smoothed.astype(np.int16)

        # 峰值检测
        peaks, properties = find_peaks(
            self.smoothed_signal,
            height=(threshold_min, threshold_max)
        )

        # 如果没有检测到峰值，返回空列表
        if len(peaks) == 0:
            self.beat_times = []
            return self.beat_times

        # 根据采样百分比筛选峰值
        if sample_percent < 100.0:
            # 获取峰值高度
            peak_heights = properties['peak_heights']

            # 计算要保留的峰值数量
            num_to_keep = max(1, int(len(peaks) * sample_percent / 100.0))

            # 按高度排序，只保留最高的 N 个
            sorted_indices = np.argsort(peak_heights)[::-1]  # 降序
            peaks = peaks[sorted_indices[:num_to_keep]]

            # 按时间排序
            peaks = np.sort(peaks)

        # 转换为时间（秒）
        self.beat_times = (peaks / sample_rate).tolist()

        return self.beat_times

    def _convolve_fft(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        使用 FFT 进行快速卷积（参考 apofai 的 convfft 函数）

        Args:
            a: 信号
            b: 核

        Returns:
            np.ndarray: 卷积结果
        """
        n = len(a)
        m = len(b)

        # FFT 长度
        yn = n + m - 1
        fft_len = 2 ** (int(np.log2(yn)) + 1)

        # FFT 卷积
        a_fft = fft(a, fft_len)
        b_fft = fft(b, fft_len)
        result = ifft(a_fft * b_fft)

        # 取实部并截断到正确长度（参考 apofai）
        start = int(np.floor(m / 2))
        end = int(np.floor(n + m / 2))
        return np.real(result[start:end])

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

        # 过滤异常值（间隔太小的可能是噪声）
        intervals = intervals[intervals > 0.05]  # 至少 50ms 间隔

        if len(intervals) == 0:
            return 120.0

        # 使用中位数估计（参考 apofai）
        median_interval = np.median(intervals)

        # BPM = 60 / 间隔
        bpm = 60.0 / median_interval

        return bpm


def detect_beats(
    energy_signal: np.ndarray,
    sample_rate: int,
    sample_percent: float = 100.0,
    threshold_min: float = 0.0,
    threshold_max: float = 32767.0
) -> Tuple[List[float], float]:
    """
    便捷函数：检测节拍

    Args:
        energy_signal: 能量信号
        sample_rate: 采样率
        sample_percent: 采样百分比 (1-100)
        threshold_min: 阈值最小值
        threshold_max: 阈值最大值

    Returns:
        Tuple[List[float], float]: (节拍时间列表, 估计BPM)
    """
    detector = BeatDetector()
    beat_times = detector.detect(
        energy_signal,
        sample_rate,
        sample_percent,
        threshold_min,
        threshold_max
    )
    bpm = BeatDetector.estimate_bpm(beat_times)
    return beat_times, bpm
