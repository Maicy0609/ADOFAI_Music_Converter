# -*- coding: utf-8 -*-
"""
ADOFAI Music Converter - Python版本
将MIDI文件转换为A Dance of Fire and Ice的谱面文件

支持三种模式：
1. RW模式 (pathData) - 使用 SetSpeed + Twirl，固定15°夹角
2. angleData模式 - 纯角度控制，固定基准BPM
3. 自定义夹角模式 - 使用 angleData + SetSpeed，可自定义夹角

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

# 导入MIDI转换模块
from lib.midi.common import MidiParser, MapData
from lib.midi.angleD import AngleDataConverter
from lib.midi.angleD_custom import AngleCustomConverter

try:
    from mido import MidiFile
except ImportError:
    print("Error: mido library is required")
    print("Run: pip install mido")
    sys.exit(1)


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


def get_file_path() -> str:
    """获取文件路径，支持拖入文件"""
    print(t('ui.separator'))
    print(t('ui.file_prompt'))
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
    print(t('ui.mode_rw'))
    print(t('ui.mode_rw_desc1'))
    print(t('ui.mode_rw_desc2'))
    print(t('ui.mode_rw_desc3'))
    print()
    print(t('ui.mode_angle'))
    print(t('ui.mode_angle_desc1'))
    print(t('ui.mode_angle_desc2'))
    print(t('ui.mode_angle_desc3'))
    print()
    print(t('ui.mode_custom'))
    print(t('ui.mode_custom_desc1'))
    print(t('ui.mode_custom_desc2'))
    print(t('ui.mode_custom_desc3'))
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
    """获取基准 BPM (仅 angleData 模式)"""
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
                return None  # 表示自动计算
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


def convert_midi_to_adofai(midi_path: str, disable: list, octave_offset: int,
                           mode: int, base_bpm: float = None,
                           custom_angle: float = 15.0) -> str:
    """转换MIDI文件到ADOFAI格式"""
    print()
    print(t('ui.separator'))
    print(t('convert.title'))
    print(t('ui.separator'))

    print(t('convert.loading', path=midi_path))
    midi_file = MidiFile(midi_path)

    parser = MidiParser()

    print(t('convert.step1'))
    melody_list = parser.parse_to_melody_list(midi_file, disable)
    print(t('convert.melody_found', count=len(melody_list)))

    print(t('convert.step2'))
    us_delay_list = parser.melody_to_us_delay_list(melody_list, octave_offset)
    print(t('convert.nodes_generated', count=len(us_delay_list)))

    print(t('convert.step3'))

    if mode == 1:
        # RW模式 - 使用AngleCustomConverter模拟pathData效果
        print(t('convert.using_rw_mode'))
        converter = AngleCustomConverter(base_angle=15.0)
        map_data = converter.convert(us_delay_list)
    elif mode == 2:
        # angleData模式 - 固定基准BPM
        print(t('convert.using_angle_mode'))
        converter = AngleDataConverter()
        map_data = converter.convert(us_delay_list, base_bpm)

        if base_bpm is None:
            base_bpm = map_data.map_setting.bpm
            print(t('convert.median_bpm', bpm=base_bpm))
    else:
        # 自定义夹角模式
        print(t('convert.using_custom_mode'))
        converter = AngleCustomConverter(base_angle=custom_angle)
        map_data = converter.convert(us_delay_list)

    print(t('convert.tiles_generated', count=len(map_data.tile_data_list)))

    # 生成输出路径
    if mode == 1:
        mode_suffix = "_rw"
    elif mode == 2:
        mode_suffix = "_angle"
    else:
        mode_suffix = f"_custom_{int(custom_angle) if custom_angle == int(custom_angle) else custom_angle}"

    idx = midi_path.rfind('.')
    if idx != -1:
        out_path = midi_path[:idx] + mode_suffix + ".adofai"
    else:
        out_path = midi_path + mode_suffix + ".adofai"

    map_data.save(out_path)

    return out_path


def main() -> None:
    """主函数"""
    # 选择语言
    print()
    select_language()

    print_banner()

    try:
        midi_path = get_file_path()

        if not midi_path:
            print(t('error.no_file_path'))
            input(t('exit.press_enter'))
            return

        if not os.path.exists(midi_path):
            print(t('error.file_not_found', path=midi_path))
            input(t('exit.press_enter'))
            return

        print()
        print(t('convert.analyzing', name=os.path.basename(midi_path)))
        midi_file = MidiFile(midi_path)

        print()
        print(t('ui.separator'))
        print(t('track_info.title'))
        print(t('ui.separator'))
        for i, track in enumerate(midi_file.tracks):
            print(t('track_info.track_size', id=i, size=len(track)))

        # 选择转换模式
        mode = select_mode()

        # 选择轨道
        disable = select_tracks(len(midi_file.tracks))

        # 获取八度偏移
        octave_offset = get_octave_offset()

        # 根据模式获取额外参数
        base_bpm = None
        custom_angle = 15.0

        if mode == 2:
            # angleData模式需要基准BPM
            base_bpm = get_base_bpm()
        elif mode == 3:
            # 自定义夹角模式需要夹角
            custom_angle = get_custom_angle()

        # 执行转换
        out_path = convert_midi_to_adofai(
            midi_path, disable, octave_offset, mode,
            base_bpm, custom_angle
        )

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
