# -*- coding: utf-8 -*-
"""
音频处理器
负责加载音频文件并预处理

支持格式：
- WAV, MP3, FLAC, VORBIS (通过 miniaudio 解码)
- WAV 也支持通过 scipy 直接读取
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

try:
    import miniaudio
except ImportError:
    miniaudio = None  # type: ignore


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

        # 检查文件扩展名
        ext = os.path.splitext(path)[1].lower()

        # 优先使用 miniaudio 解码（支持 WAV, MP3, FLAC, VORBIS）
        if miniaudio is not None:
            return self._load_with_miniaudio(path, ext, verbose)
        
        # 回退方案：WAV 文件使用 scipy 读取
        if ext == '.wav':
            return self._load_wav_with_scipy(path, verbose)
        
        # 无法处理
        if verbose:
            print(f"Error: Unsupported audio format '{ext}'")
            print("Install miniaudio for MP3/FLAC/VORBIS support: pip install miniaudio")
        return False

    def _load_with_miniaudio(self, path: str, ext: str, verbose: bool = True) -> bool:
        """
        使用 miniaudio 加载音频文件（支持 WAV, MP3, FLAC, VORBIS）

        Args:
            path: 音频文件路径
            ext: 文件扩展名
            verbose: 是否输出详细信息

        Returns:
            bool: 是否加载成功
        """
        supported_formats = ('.wav', '.mp3', '.flac', '.ogg', '.vorbis')
        
        if ext not in supported_formats:
            if verbose:
                print(f"Error: Unsupported audio format '{ext}'")
                print(f"Supported formats: {', '.join(supported_formats)}")
            return False

        try:
            if verbose:
                print(f"Loading audio with miniaudio...")

            # 使用 miniaudio 解码音频文件
            # 强制转换为单声道、44100Hz 采样率
            decoded = miniaudio.decode_file(
                path,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=44100
            )

            # 设置采样率
            self.sample_rate = decoded.sample_rate

            # 转换为 numpy 数组，再转为 float64
            self.samples = np.array(decoded.samples, dtype=np.float64)

            # 计算时长
            self.duration = decoded.duration

            # 保存文件信息
            self.file_path = path
            self.file_name = os.path.basename(path)

            if verbose:
                print(f"Sample rate: {self.sample_rate} Hz")
                print(f"Total samples: {len(self.samples)}")
                print(f"Duration: {self.duration:.2f} seconds")

            return True

        except miniaudio.DecodeError as e:
            if verbose:
                print(f"Error: Failed to decode audio file: {e}")
            return False
        except Exception as e:
            if verbose:
                print(f"Error: Failed to load audio: {e}")
            return False

    def _load_wav_with_scipy(self, path: str, verbose: bool = True) -> bool:
        """
        使用 scipy 读取 WAV 文件（回退方案）

        Args:
            path: WAV 文件路径
            verbose: 是否输出详细信息

        Returns:
            bool: 是否加载成功
        """
        try:
            self.sample_rate, data = wav.read(path)
        except Exception as e:
            if verbose:
                print(f"Error: Failed to read WAV file: {e}")
            return False

        # 转换为单声道
        if data.ndim == 2:
            data = np.mean(data, axis=1)

        # 转换为 float64
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
