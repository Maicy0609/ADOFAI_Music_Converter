# -*- coding: utf-8 -*-
"""
lib.audio - 音频处理模块

包含:
- processor: 音频加载和预处理
- detector: 节拍检测（FFT+高斯+峰值检测）
- converter: 谱面转换器（纯angleData + 拉链模式）
"""

from .processor import AudioProcessor
from .detector import BeatDetector
from .converter import AudioAngleConverter, AudioZipperConverter

__all__ = [
    'AudioProcessor',
    'BeatDetector',
    'AudioAngleConverter',
    'AudioZipperConverter'
]
