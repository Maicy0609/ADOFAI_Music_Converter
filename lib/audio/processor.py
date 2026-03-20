# -*- coding: utf-8 -*-
"""
音频处理器
负责加载音频文件并预处理

支持格式：
- WAV (直接读取)
- 其他格式 (通过ffmpeg转码)
"""

import os
import subprocess
import tempfile
from typing import Tuple, Optional
import numpy as np

try:
    import scipy.io.wavfile as wav
except ImportError:
    print("Error: scipy library is required for audio processing")
    print("Run: pip install scipy")
    exit(1)


class AudioProcessor:
    """音频处理器"""

    def __init__(self):
        self.sample_rate: Optional[int] = None
        self.samples: Optional[np.ndarray] = None
        self.duration: float = 0.0
        self.file_path: Optional[str] = None
        self.file_name: str = ""

    def load(self, path: str, verbose: bool = True) -> bool:
        """
        加载音频文件

        Args:
            path: 音频文件路径
            verbose: 是否输出详细信息

        Returns:
            bool: 是否加载成功
        """
        if not os.path.isfile(path):
            if verbose:
                print(f"Error: File not found: {path}")
            return False

        # 检查是否需要转码
        ext = os.path.splitext(path)[1].lower()

        if ext == '.wav':
            wav_path = path
        else:
            # 使用ffmpeg转码
            wav_path = self._convert_to_wav(path, verbose)
            if wav_path is None:
                return False

        # 读取WAV文件
        try:
            self.sample_rate, data = wav.read(wav_path)
        except Exception as e:
            if verbose:
                print(f"Error: Failed to read audio file: {e}")
            return False

        # 转换为单声道
        if data.ndim == 2:
            # 立体声转单声道：取平均值
            data = np.mean(data, axis=1)

        # 转换为float64以便后续处理
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

    def _convert_to_wav(self, path: str, verbose: bool = True) -> Optional[str]:
        """
        使用ffmpeg将音频转换为WAV格式

        Args:
            path: 原始文件路径
            verbose: 是否输出详细信息

        Returns:
            Optional[str]: WAV文件路径，失败返回None
        """
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        wav_path = os.path.join(temp_dir, f"ado_convert_{os.getpid()}.wav")

        try:
            if verbose:
                print("Converting audio format...")

            # 使用ffmpeg转码
            cmd = ['ffmpeg', '-y', '-i', path, '-ar', '44100', '-ac', '1', wav_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if verbose:
                    print(f"Error: ffmpeg conversion failed")
                return None

            if not os.path.isfile(wav_path):
                if verbose:
                    print("Error: Conversion failed - no output file")
                return None

            return wav_path

        except FileNotFoundError:
            if verbose:
                print("Error: ffmpeg not found. Please install ffmpeg.")
            return None
        except Exception as e:
            if verbose:
                print(f"Error: Conversion failed: {e}")
            return None

    def get_energy_signal(self) -> np.ndarray:
        """
        获取能量信号（样本值的平方）

        Returns:
            np.ndarray: 能量信号
        """
        if self.samples is None:
            raise ValueError("No audio loaded")

        # 计算能量（平方）
        energy = self.samples ** 2

        # 归一化到int16范围
        energy = energy / energy.max() * 32767

        return energy.astype(np.int16)

    def get_time_axis(self) -> np.ndarray:
        """
        获取时间轴

        Returns:
            np.ndarray: 时间数组（秒）
        """
        if self.samples is None:
            raise ValueError("No audio loaded")

        return np.linspace(0, self.duration, len(self.samples), endpoint=False)
