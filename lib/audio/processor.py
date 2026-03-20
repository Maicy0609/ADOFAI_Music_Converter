# -*- coding: utf-8 -*-
"""
音频处理器
负责加载 WAV 音频文件并预处理

只支持 WAV 格式（参考 apofai 使用 scipy.io.wavfile）
"""

import os
from typing import Optional
import numpy as np

try:
    import scipy.io.wavfile as wav
except ImportError:
    print("Error: scipy library is required for audio processing")
    print("Run: pip install scipy")
    exit(1)


class AudioProcessor:
    """音频处理器（只支持 WAV）"""

    def __init__(self):
        self.sample_rate: Optional[int] = None
        self.samples: Optional[np.ndarray] = None
        self.duration: float = 0.0
        self.file_path: Optional[str] = None
        self.file_name: str = ""

    def load(self, path: str, verbose: bool = True) -> bool:
        """
        加载 WAV 音频文件

        Args:
            path: WAV 文件路径
            verbose: 是否输出详细信息

        Returns:
            bool: 是否加载成功
        """
        if not os.path.isfile(path):
            if verbose:
                print(f"Error: File not found: {path}")
            return False

        # 检查文件扩展名
        ext = os.path.splitext(path)[1].lower()

        if ext != '.wav':
            if verbose:
                print(f"Error: Unsupported audio format '{ext}'")
                print("Only WAV format is supported")
            return False

        try:
            self.sample_rate, data = wav.read(path)
        except Exception as e:
            if verbose:
                print(f"Error: Failed to read WAV file: {e}")
            return False

        # 转换为单声道（参考 apofai）
        if data.ndim == 2:
            data = np.mean(data, axis=1)

        # 保存原始样本数据
        self.samples = data.astype(np.float64)

        # 计算时长
        self.duration = len(self.samples) / self.sample_rate

        # 保存文件信息
        self.file_path = path
        self.file_name = os.path.basename(path)

        if verbose:
            print(f"Sample rate: {self.sample_rate} Hz")
            print(f"Total samples: {len(self.samples)}")
            print(f"Duration: {self.duration:.2f} seconds")

        return True

    def get_energy_signal(self) -> np.ndarray:
        """
        获取能量信号（完全参考 apofai 的实现）

        apofai 原始逻辑：
        y0 = np.array(all_samples)  # 原始样本
        if y0.ndim == 2:
            y0 = (y0[:,0]+y0[:,1])/2  # 立体声取平均
        y1 = np.int32(y0)**2  # 平方，使用 int32 防止溢出
        y1 = np.int16((y1/y1.max())*32767)  # 归一化到 int16

        Returns:
            np.ndarray: 能量信号（int16）
        """
        if self.samples is None:
            raise ValueError("No audio loaded")

        # 参考 apofai：使用 int32 计算平方，防止溢出
        y0 = self.samples
        y1 = np.int32(y0) ** 2

        # 归一化到 int16 范围
        y1 = np.int16((y1 / y1.max()) * 32767)

        return y1

    def get_time_axis(self) -> np.ndarray:
        """
        获取时间轴

        Returns:
            np.ndarray: 时间数组（秒）
        """
        if self.samples is None:
            raise ValueError("No audio loaded")

        return np.linspace(0, self.duration, len(self.samples), endpoint=False)
