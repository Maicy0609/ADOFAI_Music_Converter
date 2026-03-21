# -*- coding: utf-8 -*-
"""
ADOFAI Music Converter - Python版本
将MIDI或音频文件转换为A Dance of Fire and Ice的谱面文件

输入源：
- MIDI文件：从音符事件提取节拍
- 音频文件：从波形自动检测节拍

转换模式：
1. angleData模式 - 纯角度控制，固定基准BPM
2. 拉链夹角模式 - 固定角度，动态BPM调整
3. 全采音模式 - 直线轨道，打击音播放音频

核心原则：前两种模式生成的拍子绝对时间完全相同！

作者: 基于 Luxus io 的Java版本重写
GitHub: https://github.com/Luxusio/ADOFAI-Midi-Converter
"""

import os
import sys

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 导入i18n模块
from i18n.i18n import t, set_language, select_language

# ============================================================================
# 依赖检查
# ============================================================================

# 检查numpy
try:
    import numpy as np
except ImportError:
    print("Error: numpy library is required")
    print("Run: pip install numpy")
    sys.exit(1)

# 检查scipy（音频处理需要）
try:
    import scipy
except ImportError:
    print("Error: scipy library is required for audio processing")
    print("Run: pip install scipy")
    sys.exit(1)

# 检查mido（MIDI处理需要）
try:
    from mido import MidiFile
except ImportError:
    print("Error: mido library is required for MIDI processing")
    print("Run: pip install mido")
    sys.exit(1)

# 导入MIDI转换模块
from lib.midi.common import MidiParser
from lib.midi.angleD import AngleDataConverter
from lib.midi.angleD_custom import AngleCustomConverter

# 导入音频处理模块
from lib.audio.processor import AudioProcessor
from lib.audio.detector import BeatDetector
from lib.audio.converter import AudioAngleConverter, AudioZipperConverter, FullSampleConverter


# ============================================================================
# CLI 辅助函数
# ============================================================================

def print_banner() -> None:
    """打印程序横幅"""
    print()
    print(t('ui.separator'))
    print(f"    {t('app.title')}")
    print(f"    {t('app.version')}")
    print(t('ui.separator'))
    print()
    print(t('app.original_author'))
    print(t('app.python_rewrite'))
    print(t('app.youtube'))
    print(t('app.github'))
    print()


def select_input_source() -> int:
    """选择输入源"""
    print()
    print(t('ui.separator'))
    print(t('ui.source_title'))
    print(t('ui.separator'))
    print(t('ui.source_midi'))
    print(t('ui.source_midi_desc'))
    print()
    print(t('ui.source_audio'))
    print(t('ui.source_audio_desc'))
    print(t('ui.separator'))

    while True:
        try:
            choice = input(t('ui.source_prompt')).strip()
            if choice == "" or choice == "1":
                return 1
            elif choice == "2":
                return 2
            else:
                print(t('error.invalid_source'))
        except ValueError:
            print(t('error.invalid_number'))


def get_file_path(source: int) -> str:
    """获取文件路径"""
    print()
    print(t('ui.separator'))
    if source == 1:
        print(t('ui.file_prompt_midi'))
    else:
        print(t('ui.file_prompt_audio'))
    print(t('ui.file_hint'))
    print(t('ui.separator'))

    path = input(t('ui.file_input')).strip()
    path = path.strip('"').strip("'")

    return path


def select_mode() -> int:
    """选择转换模式"""
    print()
    print(t('ui.separator'))
    print(t('ui.mode_title'))
    print(t('ui.separator'))
    print(t('ui.mode_angle'))
    print(t('ui.mode_angle_desc1'))
    print()
    print(t('ui.mode_zipper'))
    print(t('ui.mode_zipper_desc1'))
    print(t('ui.mode_zipper_desc2'))
    print()
    print(t('ui.mode_fullsample'))
    print(t('ui.mode_fullsample_desc1'))
    print(t('ui.mode_fullsample_desc2'))
    print(t('ui.separator'))

    while True:
        try:
            choice = input(t('ui.mode_prompt')).strip()
            if choice == "" or choice == "1":
                return 1
            elif choice == "2":
                return 2
            elif choice == "3":
                return 3
            else:
                print(t('error.invalid_mode'))
        except ValueError:
            print(t('error.invalid_number'))


def select_tracks(track_count: int) -> list:
    """选择要禁用的轨道"""
    disable = [False] * track_count

    print()
    print(t('ui.separator'))
    print(t('ui.track_title'))
    print(t('ui.track_status', count=track_count))

    for i in range(track_count):
        status = t('ui.track_disabled') if disable[i] else t('ui.track_enabled')
        print(f"  {i}: {status}")

    print()
    print(t('ui.track_toggle'))
    print(t('ui.track_continue'))
    print(t('ui.separator'))

    while True:
        try:
            choice = input(t('ui.track_input')).strip()
            track_num = int(choice)

            if track_num == -1:
                break
            elif 0 <= track_num < track_count:
                disable[track_num] = not disable[track_num]
                status = t('ui.track_disabled') if disable[track_num] else t('ui.track_enabled')
                print(t('ui.track_set', num=track_num, status=status))
            else:
                print(t('ui.track_range_error', max=track_count - 1))
        except ValueError:
            print(t('error.invalid_integer'))

    return disable


def get_octave_offset() -> int:
    """获取八度偏移"""
    print()
    print(t('ui.separator'))
    print(t('ui.octave_title'))
    print(t('ui.separator'))
    print(t('ui.octave_desc'))
    print(t('ui.octave_recommend'))
    print(t('ui.separator'))

    while True:
        try:
            offset = input(t('ui.octave_prompt')).strip()
            if offset == "":
                return -4
            return int(offset)
        except ValueError:
            print(t('error.invalid_integer'))


def get_base_bpm() -> float:
    """获取基准 BPM"""
    print()
    print(t('ui.separator'))
    print(t('ui.bpm_title'))
    print(t('ui.separator'))
    print(t('ui.bpm_desc'))
    print(t('ui.bpm_auto'))
    print(t('ui.separator'))

    while True:
        try:
            bpm = input(t('ui.bpm_prompt')).strip()
            if bpm == "":
                return None
            bpm_val = float(bpm)
            if bpm_val <= 0:
                print(t('error.bpm_positive'))
                continue
            return bpm_val
        except ValueError:
            print(t('error.invalid_number'))


def get_custom_angle() -> float:
    """获取自定义夹角"""
    print()
    print(t('ui.separator'))
    print(t('ui.angle_title'))
    print(t('ui.separator'))
    print(t('ui.angle_desc'))
    print(t('ui.angle_example'))
    print(t('ui.angle_range'))
    print(t('ui.separator'))

    while True:
        try:
            angle_str = input(t('ui.angle_prompt')).strip()

            if angle_str == "":
                angle = 15.0
            else:
                angle = float(angle_str)

            # 验证夹角
            if angle <= 0:
                print(t('error.angle_zero'))
                continue
            if angle > 180:
                print(t('error.angle_exceed'))
                continue

            # 计算魔法数字
            magic_number = 180.0 / angle
            print()
            print(t('ui.angle_set', angle=angle))
            print(t('ui.angle_magic', angle=angle, magic=magic_number))

            if angle == 180:
                print(t('ui.angle_180_note'))

            return angle

        except ValueError:
            print(t('error.invalid_number'))


def select_audio_mode() -> int:
    """选择音频采样模式"""
    print()
    print(t('ui.separator'))
    print(t('ui.audio_mode_title'))
    print(t('ui.separator'))
    print(t('ui.audio_mode_peak'))
    print(t('ui.audio_mode_peak_desc'))
    print()
    print(t('ui.audio_mode_full'))
    print(t('ui.audio_mode_full_desc'))
    print(t('ui.separator'))

    while True:
        try:
            choice = input(t('ui.audio_mode_prompt')).strip()
            if choice == "" or choice == "1":
                return 1
            elif choice == "2":
                return 2
            else:
                print(t('error.invalid_mode'))
        except ValueError:
            print(t('error.invalid_number'))


def get_audio_params_peak() -> dict:
    """
    峰值采样模式参数

    参数说明：
    - height_min: 阈值最小值（0-32767），低于此值的峰值不采集
    - height_max: 阈值最大值（0-32767），高于此值的峰值不采集
    """
    print()
    print(t('ui.separator'))
    print(t('ui.peak_params_title'))
    print(t('ui.separator'))
    print()

    # 获取阈值最小值
    height_min = 0.0
    print(t('ui.height_min_prompt'), end='')
    height_min_str = input().strip()
    if height_min_str:
        try:
            height_min = float(height_min_str)
            height_min = max(0.0, min(32767.0, height_min))
        except ValueError:
            pass

    # 获取阈值最大值
    height_max = 32767.0
    print(t('ui.height_max_prompt'), end='')
    height_max_str = input().strip()
    if height_max_str:
        try:
            height_max = float(height_max_str)
            height_max = max(0.0, min(32767.0, height_max))
        except ValueError:
            pass

    print(t('ui.separator'))

    return {
        'height_min': height_min,
        'height_max': height_max
    }


def get_fullsample_params() -> dict:
    """
    全采音模式参数

    参数说明：
    - pseudo_sample_rate: 伪采样率（Hz），决定音频还原质量和谱面密度
    - use_float_volume: 是否使用浮点数音量
    """
    print()
    print(t('ui.separator'))
    print(t('ui.fullsample_title'))
    print(t('ui.separator'))
    print(t('ui.fullsample_rate_desc'))
    print(t('ui.fullsample_rate_example'))
    print(t('ui.fullsample_rate_range'))
    print(t('ui.separator'))

    # 获取伪采样率
    while True:
        try:
            rate_str = input(t('ui.fullsample_rate_prompt')).strip()
            if rate_str == "":
                pseudo_sample_rate = 8000.0
            else:
                pseudo_sample_rate = float(rate_str)

            # 验证采样率
            if pseudo_sample_rate <= 0 or pseudo_sample_rate > 48000:
                print(t('error.sample_rate_invalid'))
                continue

            break
        except ValueError:
            print(t('error.invalid_number'))

    print(t('ui.fullsample_rate_set', rate=pseudo_sample_rate))
    print(t('ui.fullsample_bpm_info', bpm=pseudo_sample_rate * 60))

    # 选择音量精度
    print()
    print(t('ui.separator'))
    print(t('ui.fullsample_volume_title'))
    print(t('ui.separator'))
    print(t('ui.fullsample_volume_int'))
    print(t('ui.fullsample_volume_int_desc'))
    print()
    print(t('ui.fullsample_volume_float'))
    print(t('ui.fullsample_volume_float_desc'))
    print(t('ui.separator'))

    while True:
        try:
            choice = input(t('ui.fullsample_volume_prompt')).strip()
            if choice == "" or choice == "1":
                use_float_volume = False
            elif choice == "2":
                use_float_volume = True
            else:
                print(t('error.invalid_mode'))
                continue
            break
        except ValueError:
            print(t('error.invalid_number'))

    print(t('ui.separator'))

    return {
        'pseudo_sample_rate': pseudo_sample_rate,
        'use_float_volume': use_float_volume
    }


# ============================================================================
# 转换函数
# ============================================================================

def convert_midi(midi_path: str, mode: int) -> str:
    """转换MIDI文件"""
    print()
    print(t('ui.separator'))
    print(t('convert.title'))
    print(t('ui.separator'))

    print(t('convert.loading', path=midi_path))
    midi_file = MidiFile(midi_path)

    # 显示轨道信息
    print()
    print(t('ui.separator'))
    print(t('track_info.title'))
    print(t('ui.separator'))
    for i, track in enumerate(midi_file.tracks):
        print(t('track_info.track_size', id=i, size=len(track)))

    # 选择轨道
    disable = select_tracks(len(midi_file.tracks))

    # 获取八度偏移
    octave_offset = get_octave_offset()

    # 解析MIDI
    parser = MidiParser()
    print()
    print(t('convert.step1'))
    melody_list = parser.parse_to_melody_list(midi_file, disable)
    print(t('convert.melody_found', count=len(melody_list)))

    print(t('convert.step2'))
    us_delay_list = parser.melody_to_us_delay_list(melody_list, octave_offset)
    print(t('convert.nodes_generated', count=len(us_delay_list)))

    print(t('convert.step3'))

    # 根据模式获取额外参数
    base_bpm = None
    custom_angle = 15.0

    if mode == 1:
        base_bpm = get_base_bpm()
        print()
        print(t('convert.using_angle_mode'))
        converter = AngleDataConverter()
        map_data = converter.convert(us_delay_list, base_bpm)

        if base_bpm is None:
            base_bpm = map_data.map_setting.bpm
            print(t('convert.median_bpm', bpm=base_bpm))

        mode_suffix = "_angle"
    else:
        custom_angle = get_custom_angle()
        print()
        print(t('convert.using_zipper_mode'))
        converter = AngleCustomConverter(base_angle=custom_angle)
        map_data = converter.convert(us_delay_list)
        mode_suffix = f"_zipper_{int(custom_angle) if custom_angle == int(custom_angle) else custom_angle}"

    print(t('convert.tiles_generated', count=len(map_data.tile_data_list)))

    # 生成输出路径
    idx = midi_path.rfind('.')
    if idx != -1:
        out_path = midi_path[:idx] + mode_suffix + ".adofai"
    else:
        out_path = midi_path + mode_suffix + ".adofai"

    map_data.save(out_path)

    return out_path


def convert_audio(audio_path: str, mode: int) -> str:
    """转换音频文件"""
    print()
    print(t('ui.separator'))
    print(t('convert.title'))
    print(t('ui.separator'))

    # 全采音模式特殊处理
    if mode == 3:
        return convert_audio_fullsample(audio_path)

    # 加载音频
    print(t('convert.loading', path=audio_path))
    processor = AudioProcessor()
    if not processor.load(audio_path):
        print(t('error.file_load_failed'))
        return None

    print()
    print(t('convert.sample_info', rate=processor.sample_rate, duration=processor.duration))

    # 选择音频采样模式
    audio_mode = select_audio_mode()

    # 检测节拍
    print()
    print(t('convert.step1_audio'))
    detector = BeatDetector()

    if audio_mode == 1:
        # 峰值采样模式
        params = get_audio_params_peak()
        energy_signal = processor.get_energy_signal()
        beat_times = detector.detect_peaks(
            energy_signal,
            processor.sample_rate,
            height_min=params['height_min'],
            height_max=params['height_max']
        )
        mode_suffix_audio = "_peak"
    else:
        # 采样点全采样模式
        beat_times = detector.detect_all_samples(
            processor.sample_rate,
            len(processor.samples)
        )
        mode_suffix_audio = "_full"

    if not beat_times:
        print(t('error.no_beats_detected'))
        return None

    print(t('convert.beats_found', count=len(beat_times)))

    # 估计BPM
    estimated_bpm = BeatDetector.estimate_bpm(beat_times)
    print(t('ui.bpm_estimated', bpm=estimated_bpm))

    print(t('convert.step3'))

    # 根据模式转换
    if mode == 1:
        # 获取或确认BPM
        print()
        base_bpm = get_base_bpm()
        if base_bpm is None:
            base_bpm = estimated_bpm

        print()
        print(t('convert.using_angle_mode'))
        converter = AudioAngleConverter(base_bpm=base_bpm)
        map_data = converter.convert(beat_times, estimated_bpm)
        mode_suffix = "_angle"
    else:
        custom_angle = get_custom_angle()
        print()
        print(t('convert.using_zipper_mode'))
        converter = AudioZipperConverter(base_angle=custom_angle)
        map_data = converter.convert(beat_times, estimated_bpm)
        mode_suffix = f"_zipper_{int(custom_angle) if custom_angle == int(custom_angle) else custom_angle}"

    print(t('convert.tiles_generated', count=len(map_data.tile_data_list)))

    # 生成输出路径
    idx = audio_path.rfind('.')
    if idx != -1:
        out_path = audio_path[:idx] + mode_suffix_audio + mode_suffix + ".adofai"
    else:
        out_path = audio_path + mode_suffix_audio + mode_suffix + ".adofai"

    map_data.save(out_path)

    return out_path


def convert_audio_fullsample(audio_path: str) -> str:
    """全采音模式转换音频文件"""
    print(t('convert.loading', path=audio_path))

    # 获取全采音参数
    params = get_fullsample_params()
    pseudo_sample_rate = params['pseudo_sample_rate']
    use_float_volume = params['use_float_volume']

    print()
    print(t('convert.step1_fullsample'))

    # 加载音频
    try:
        audio_data, sample_rate = FullSampleConverter.load_audio_file(audio_path)
    except Exception as e:
        print(t('error.audio_load_failed'))
        print(f"  {e}")
        return None

    duration = len(audio_data) / sample_rate
    estimated_tiles = int(duration * pseudo_sample_rate)

    print(t('convert.sample_info', rate=sample_rate, duration=duration))
    print(t('ui.fullsample_tiles_info', count=estimated_tiles))

    # 创建转换器
    converter = FullSampleConverter(
        pseudo_sample_rate=pseudo_sample_rate,
        use_float_volume=use_float_volume
    )

    print()
    print(t('convert.step2_fullsample'))

    # 转换
    import os
    song_filename = os.path.basename(audio_path)
    map_data = converter.convert(
        audio_data=audio_data,
        original_sample_rate=sample_rate,
        song_filename=song_filename
    )

    print()
    print(t('convert.step3'))
    print(t('convert.using_fullsample_mode'))
    print(t('convert.tiles_generated', count=len(map_data.tile_data_list)))

    # 生成输出路径
    idx = audio_path.rfind('.')
    if idx != -1:
        out_path = audio_path[:idx] + f"_fullsample_{int(pseudo_sample_rate)}.adofai"
    else:
        out_path = audio_path + f"_fullsample_{int(pseudo_sample_rate)}.adofai"

    map_data.save(out_path)

    return out_path


# ============================================================================
# 主函数
# ============================================================================

def main() -> None:
    """主函数"""
    # 选择语言
    print()
    select_language()

    print_banner()

    try:
        # 选择输入源
        source = select_input_source()

        # 获取文件路径
        file_path = get_file_path(source)

        if not file_path:
            print(t('error.no_file_path'))
            input(t('exit.press_enter'))
            return

        if not os.path.exists(file_path):
            print(t('error.file_not_found', path=file_path))
            input(t('exit.press_enter'))
            return

        # 选择转换模式
        mode = select_mode()

        # 根据输入源执行转换
        if source == 1:
            out_path = convert_midi(file_path, mode)
        else:
            out_path = convert_audio(file_path, mode)

        if out_path:
            print()
            print(t('ui.separator'))
            print(t('convert.complete'))
            print(t('ui.separator'))
            print(t('convert.output_file', path=out_path))
            print()

    except KeyboardInterrupt:
        print()
        print(t('exit.user_cancel'))
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    input(t('exit.press_enter'))


if __name__ == "__main__":
    main()
