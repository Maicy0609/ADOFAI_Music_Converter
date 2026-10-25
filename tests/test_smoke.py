# -*- coding: utf-8 -*-
"""全量冒烟测试。

覆盖：
- 四种转换模式的谱面时间轴（angleData / 拉链 / 音频 / 大圈圈）
- MIDI 解析（含 tempo 变化）
- .adofai 文件结构、事件字段与范围
- 音频能量信号、峰值检测、全采音
- pathData / angleData 序列化
- i18n 键完整性与格式化
- 真实 CLI 端到端流程（subprocess）

运行：
    python -m unittest discover -s tests -v
"""

import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from mido import Message, MetaMessage, MidiFile, MidiTrack
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.audio.converter import (  # noqa: E402
    AudioAngleConverter,
    AudioZipperConverter,
    FullSampleConverter,
)
from lib.audio.detector import BeatDetector  # noqa: E402
from lib.audio.processor import AudioProcessor  # noqa: E402
from lib.midi.angleD import AngleDataConverter  # noqa: E402
from lib.midi.angleD_custom import AngleCustomConverter  # noqa: E402
from lib.midi.bigcircle import BigCircleConverter  # noqa: E402
from lib.midi.common import (  # noqa: E402
    EventType,
    MapData,
    MidiParser,
    Pause,
    SetHitsound,
    SetSpeed,
    TileAngle,
    TileData,
    Twirl,
)
from lib.utils import show_progress  # noqa: E402
from i18n import i18n  # noqa: E402


DEFAULT_DELAYS_US = [500_000, 250_000, 750_000, 1_000_000]


def chart_hit_times(map_data: MapData) -> List[float]:
    """按 ADOFAI 的游戏语义回放谱面，返回每块瓷砖的命中时间（秒）。

    游戏自带 floor 0 起始砖块，angleData[i] 对应 floor i+1。
    - SetSpeed / Twirl / Pause 都在“当前瓷砖”上生效，影响当前瓷砖 -> 下一块
    - 第一段旋转 = 180 - angleData[0]
    - 第 i 段旋转（i >= 1）= angleData[i-1] + 180 - angleData[i]
    """
    angles: List[float] = [0.0]  # 游戏自带 floor 0 起始砖块
    actions_by_floor: Dict[int, Dict[EventType, List[Any]]] = {}
    for tile in map_data.tile_data_list:
        actions_by_floor[tile.floor] = tile.action_list_map
        if tile.is_default:
            continue
        assert tile.angle is not None, f"tile {tile.floor} has no angle"
        angles.append(tile.angle)

    if len(angles) <= 1:
        return [0.0]

    bpm = map_data.map_setting.bpm
    direction = 1
    now = 0.0
    hit_times = [0.0]

    for i in range(len(angles) - 1):
        actions = actions_by_floor.get(i, {})
        for action in actions.get(EventType.SET_SPEED, []):
            assert isinstance(action, SetSpeed)
            assert action.beats_per_minute is not None
            bpm = action.beats_per_minute * (action.bpm_multiplier or 1.0)
        for _ in actions.get(EventType.TWIRL, []):
            direction *= -1
        for action in actions.get(EventType.PAUSE, []):
            assert isinstance(action, Pause)
            assert action.duration is not None
            now += action.duration * 60.0 / bpm

        if direction > 0:
            rotation = angles[i] + 180.0 - angles[i + 1]
        else:
            rotation = 180.0 + angles[i + 1] - angles[i]
        rotation %= 360.0
        if rotation <= 0:
            rotation += 360.0

        now += rotation / 180.0 * 60.0 / bpm
        hit_times.append(now)

    return hit_times


def read_adofai(path: Path) -> Dict[str, Any]:
    """读取 ADOFAI 文件（允许尾逗号）。"""
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    data: Dict[str, Any] = json.loads(text)
    return data


def write_mono_midi(path: Path) -> None:
    """写一个 120 BPM、每拍一个音符的 MIDI。"""
    midi = MidiFile(ticks_per_beat=480)
    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage("set_tempo", tempo=500_000, time=0))
    midi.tracks.append(tempo_track)

    note_track = MidiTrack()
    last_tick = 0
    for i, note in enumerate([60, 64, 67, 72]):
        on_tick = i * 480
        off_tick = on_tick + 240
        note_track.append(Message("note_on", note=note, velocity=100,
                                  time=on_tick - last_tick))
        note_track.append(Message("note_off", note=note, velocity=0,
                                  time=off_tick - on_tick))
        last_tick = off_tick
    midi.tracks.append(note_track)
    midi.save(str(path))


def write_click_wav(path: Path, sample_rate: int = 8000,
                    duration: float = 0.75) -> None:
    """写一个带明显瞬态的 WAV，便于峰值检测。"""
    samples = np.zeros(int(sample_rate * duration), dtype=np.float64)
    for second in (0.05, 0.30, 0.55):
        start = int(second * sample_rate)
        samples[start:start + 40] = np.linspace(0.9, 0.0, 40)
    wavfile.write(str(path), sample_rate, (samples * 32767).astype(np.int16))


class ChartTimingTests(unittest.TestCase):
    def assert_times(self, actual: List[float], expected: List[float],
                     delta: float = 1e-6) -> None:
        self.assertEqual(len(actual), len(expected))
        for got, want in zip(actual, expected):
            self.assertAlmostEqual(got, want, delta=delta)

    def test_angle_data_timing_and_long_interval(self) -> None:
        delays = [100_000, 100_000, 100_000, 5_000_000]
        map_data = AngleDataConverter().convert(delays)
        expected = [0.0]
        for delay in delays:
            expected.append(expected[-1] + delay / 1e6)
        self.assert_times(chart_hit_times(map_data), expected)

        # 长间隔应产生 Pause，且 Pause 必须落在出发瓷砖上
        pauses = [
            tile.floor
            for tile in map_data.tile_data_list
            if EventType.PAUSE in tile.action_list_map
        ]
        self.assertEqual(pauses, [3])

    def test_zipper_timing_all_angles(self) -> None:
        expected = [0.0]
        for delay in DEFAULT_DELAYS_US:
            expected.append(expected[-1] + delay / 1e6)

        for angle in (15.0, 90.0, 180.0):
            with self.subTest(angle=angle):
                map_data = AngleCustomConverter(angle).convert(DEFAULT_DELAYS_US)
                self.assert_times(chart_hit_times(map_data), expected)
                self.assertEqual(len(map_data.tile_data_list), 5)
                # 每个出发瓷砖一个 SetSpeed
                speeds = [
                    tile.floor
                    for tile in map_data.tile_data_list
                    if EventType.SET_SPEED in tile.action_list_map
                ]
                self.assertEqual(speeds, [0, 1, 2, 3])

    def test_audio_converters_timing(self) -> None:
        beat_times = [0.1, 0.6, 0.85, 1.6, 2.6]
        expected = [0.0, 0.5, 0.75, 1.5, 2.5]

        self.assert_times(
            chart_hit_times(AudioAngleConverter().convert(beat_times, 120.0)),
            expected,
        )
        for angle in (15.0, 180.0):
            with self.subTest(angle=angle):
                self.assert_times(
                    chart_hit_times(
                        AudioZipperConverter(angle).convert(beat_times, 120.0)
                    ),
                    expected,
                )

    def test_bigcircle_timing(self) -> None:
        notes = [(0.0, 69), (0.25, 72), (0.5, 76), (1.0, 60), (1.5, 81)]
        map_data, offset_ms, out_path = BigCircleConverter().convert_track(notes)
        self.assertIsNotNone(map_data)
        assert map_data is not None
        self.assertEqual(offset_ms, 0)
        self.assertIsNotNone(out_path)

        hit_times = chart_hit_times(map_data)
        for note_time, _pitch in notes:
            nearest = min(hit_times, key=lambda t: abs(t - note_time))
            self.assertAlmostEqual(nearest, note_time, delta=2e-3)


class MidiTests(unittest.TestCase):
    def test_parser_delays_are_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "song.mid"
            write_mono_midi(path)
            midi = MidiFile(str(path))
            melodies = MidiParser().parse_to_melody_list(
                midi, [False] * len(midi.tracks)
            )
            self.assertGreater(len(melodies), 1)
            delays = MidiParser().melody_to_us_delay_list(melodies, -4)
            self.assertTrue(delays)
            self.assertTrue(all(d > 0 for d in delays))

    def test_bigcircle_tempo_change_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tempo.mid"
            midi = MidiFile(ticks_per_beat=480)
            track = MidiTrack()
            midi.tracks.append(track)
            track.append(MetaMessage("set_tempo", tempo=500_000, time=0))
            track.append(Message("note_on", note=60, velocity=100, time=0))
            track.append(MetaMessage("set_tempo", tempo=250_000, time=480))
            track.append(Message("note_on", note=60, velocity=100, time=480))
            midi.save(str(path))

            parsed = MidiFile(str(path))
            notes = BigCircleConverter().parse_midi_track(parsed, 0)
            self.assertEqual(notes, [(0.0, 60), (0.75, 60)])


class SerializationTests(unittest.TestCase):
    def test_angle_data_file_structure(self) -> None:
        map_data = AngleCustomConverter(15.0).convert(DEFAULT_DELAYS_US)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "level.adofai"
            map_data.save(str(path))
            data = read_adofai(path)

            self.assertEqual(len(data["angleData"]), 4)
            self.assertEqual(len(data["actions"]), 6)
            self.assertEqual(data["angleData"][0], 0.0)
            self.assertEqual(data["settings"]["bpm"], 100)
            for angle in data["angleData"]:
                self.assertTrue(0.0 <= angle <= 360.0)
            for action in data["actions"]:
                self.assertIn(action["floor"], range(5))
                self.assertIn(
                    action["eventType"], {"SetSpeed", "Twirl", "Pause"}
                )
                if action["eventType"] == "SetSpeed":
                    self.assertGreater(action["beatsPerMinute"], 0)
                    self.assertTrue(math.isfinite(action["beatsPerMinute"]))

    def test_path_data_includes_first_tile(self) -> None:
        map_data = MapData(use_angle_data=False)
        map_data.tile_data_list = [
            TileData(0, TileAngle._0),
            TileData(1, TileAngle._15),
            TileData(2, TileAngle._180),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "path.adofai"
            map_data.save(str(path))
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn('"pathData": "RpL"', text)

    def test_missing_angle_or_tile_angle_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            angle_map = MapData(use_angle_data=True)
            angle_map.tile_data_list = [TileData(0)]
            with self.assertRaises(ValueError):
                angle_map.save(str(Path(tmp) / "bad-angle.adofai"))

            path_map = MapData(use_angle_data=False)
            path_map.tile_data_list = [TileData(0)]
            with self.assertRaises(ValueError):
                path_map.save(str(Path(tmp) / "bad-path.adofai"))


class AudioTests(unittest.TestCase):
    def test_energy_signal_handles_int16_float32_int32(self) -> None:
        sample_rate = 8000
        t = np.arange(sample_rate) / sample_rate
        wave = 0.8 * np.sin(2 * np.pi * 440 * t)
        variants: List[Tuple[str, np.ndarray]] = [
            ("int16", (wave * 32767).astype(np.int16)),
            ("float32", wave.astype(np.float32)),
            ("int32", (wave * 8_388_607).astype(np.int32)),
        ]
        for name, samples in variants:
            with self.subTest(dtype=name), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "tone.wav"
                wavfile.write(str(path), sample_rate, samples)
                processor = AudioProcessor()
                self.assertTrue(processor.load(str(path), verbose=False))
                energy = processor.get_energy_signal()
                self.assertEqual(energy.dtype, np.int16)
                self.assertEqual(int(energy.max()), 32767)
                self.assertGreater(int((energy > 0).sum()), 0)

                detector = BeatDetector()
                beats = detector.detect_peaks(energy, sample_rate)
                self.assertGreater(len(beats), 0)

    def test_fullsample_converter(self) -> None:
        sample_rate = 8000
        samples = np.zeros(800, dtype=np.float64)
        samples[100:140] = 0.5
        converter = FullSampleConverter(pseudo_sample_rate=4000.0)
        map_data = converter.convert(samples, sample_rate)

        self.assertEqual(map_data.map_setting.bpm, 240_000.0)
        self.assertEqual(len(map_data.tile_data_list), 401)
        hitsounds = [
            action
            for tile in map_data.tile_data_list
            for action in tile.action_list_map.get(EventType.SET_HITSOUND, [])
        ]
        self.assertEqual(len(hitsounds), 400)
        for action in hitsounds:
            assert isinstance(action, SetHitsound)
            self.assertGreaterEqual(action.hitsound_volume, 0)
            self.assertLessEqual(action.hitsound_volume, 100)

    def test_fullsample_empty_audio(self) -> None:
        converter = FullSampleConverter(pseudo_sample_rate=8000.0)
        map_data = converter.convert(np.zeros(0, dtype=np.float64), 8000)
        self.assertEqual(len(map_data.tile_data_list), 1)


class I18nAndProgressTests(unittest.TestCase):
    def test_translation_keys_are_complete(self) -> None:
        key_pattern = re.compile(r"""(?<![\w.])t\(\s*['"]([^'"]+)['"]""")
        used: set[str] = set()
        for path in list(ROOT.glob("*.py")) + list(ROOT.glob("lib/**/*.py")):
            used.update(key_pattern.findall(path.read_text(encoding="utf-8")))

        for lang in ("zh_CN", "en_US"):
            translations = json.loads(
                (ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8")
            )

            def has_key(key: str) -> bool:
                node: Any = translations
                for part in key.split("."):
                    if not isinstance(node, dict) or part not in node:
                        return False
                    node = node[part]
                return isinstance(node, str)

            missing = sorted(key for key in used if not has_key(key))
            self.assertEqual(missing, [], f"{lang} missing keys: {missing}")

    def test_translation_formatting(self) -> None:
        self.assertTrue(i18n.set_language("zh_CN"))
        self.assertEqual(i18n.t("ui.track_set", num=3, status="启用"),
                         "轨道 3 已设为: 启用")
        self.assertEqual(i18n.t("no.such.key"), "no.such.key")

    def test_show_progress(self) -> None:
        self.assertEqual(list(show_progress([1, 2, 3], prefix="test")), [1, 2, 3])


class CliSmokeTests(unittest.TestCase):
    """真实入口端到端测试。"""

    def run_cli(self, stdin: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            input=stdin,
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            timeout=120,
            check=False,
        )

    def test_midi_angle_and_zipper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            midi_path = Path(tmp) / "song.mid"
            write_mono_midi(midi_path)

            angle_out = Path(tmp) / "song_angle.adofai"
            result = self.run_cli(
                f"1\n1\n{midi_path}\n1\n-1\n\n\n\n"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(angle_out.exists(), result.stdout + result.stderr)
            self.assertGreater(len(read_adofai(angle_out)["angleData"]), 1)

            zipper_out = Path(tmp) / "song_zipper_15.adofai"
            result = self.run_cli(
                f"1\n1\n{midi_path}\n2\n-1\n\n\n\n"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(zipper_out.exists(), result.stdout + result.stderr)
            self.assertGreater(len(read_adofai(zipper_out)["actions"]), 0)

    def test_midi_bigcircle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            midi_path = Path(tmp) / "song.mid"
            write_mono_midi(midi_path)
            result = self.run_cli(f"1\n1\n{midi_path}\n4\n-1\n\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            out = Path(tmp) / "song_Track1.adofai"
            self.assertTrue(out.exists(), result.stdout + result.stderr)
            self.assertGreater(len(read_adofai(out)["angleData"]), 1)

    def test_audio_peak_and_fullsample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "click.wav"
            write_click_wav(wav_path)

            peak_out = Path(tmp) / "click_peak_angle.adofai"
            result = self.run_cli(
                f"1\n2\n{wav_path}\n1\n1\n\n\n\n\n"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(peak_out.exists(), result.stdout + result.stderr)
            self.assertEqual(
                read_adofai(peak_out)["settings"]["songFilename"], "click.wav"
            )

            full_out = Path(tmp) / "click_fullsample_8000.adofai"
            result = self.run_cli(
                f"1\n2\n{wav_path}\n3\n\n\n\n"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(full_out.exists(), result.stdout + result.stderr)
            self.assertGreater(len(read_adofai(full_out)["angleData"]), 1)

    def test_midi_fullsample_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            midi_path = Path(tmp) / "song.mid"
            write_mono_midi(midi_path)
            result = self.run_cli(f"1\n1\n{midi_path}\n3\n\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("全采音模式仅支持音频文件", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
