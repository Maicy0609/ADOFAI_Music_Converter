# -*- coding: utf-8 -*-
"""
MIDI转换通用模块
包含共享的数据结构、枚举和基础类
"""

import sys
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from abc import ABC, abstractmethod
from statistics import median

try:
    from mido import MidiFile
except ImportError:
    print("Error: mido library is required")
    print("Run: pip install mido")
    sys.exit(1)


# ============================================================================
# EventType 枚举
# ============================================================================

class EventType(Enum):
    """ADOFAI事件类型枚举"""
    SET_SPEED = ("SetSpeed", True)
    TWIRL = ("Twirl", True)
    PAUSE = ("Pause", True)
    CHECKPOINT = ("Checkpoint", True)
    CUSTOM_BACKGROUND = ("CustomBackground", False)
    COLOR_TRACK = ("ColorTrack", True)
    ANIMATE_TRACK = ("AnimateTrack", True)
    ADD_DECORATION = ("AddDecoration", False)
    FLASH = ("Flash", False)
    MOVE_CAMERA = ("MoveCamera", False)
    SET_HITSOUND = ("SetHitsound", True)
    RECOLOR_TRACK = ("RecolorTrack", False)
    MOVE_TRACK = ("MoveTrack", False)
    SET_FILTER = ("SetFilter", False)
    HALL_OF_MIRRORS = ("HallOfMirrors", False)
    SHAKE_SCREEN = ("ShakeScreen", False)
    SET_PLANET_ROTATION = ("SetPlanetRotation", True)
    MOVE_DECORATIONS = ("MoveDecorations", False)
    POSITION_TRACK = ("PositionTrack", True)
    REPEAT_EVENTS = ("RepeatEvents", True)
    BLOOM = ("Bloom", False)
    SET_CONDITIONAL_EVENTS = ("SetConditionalEvents", True)
    CHANGE_TRACK = ("ChangeTrack", False)

    def __init__(self, type_str: str, single_only: bool):
        self._type_str = type_str
        self._single_only = single_only

    @property
    def type_str(self) -> str:
        return self._type_str

    def __str__(self) -> str:
        return self._type_str


STRING_TO_EVENT_TYPE = {et.type_str: et for et in EventType}


# ============================================================================
# TileAngle 枚举 (用于 pathData 模式)
# ============================================================================

class TileAngle(Enum):
    """ADOFAI瓷砖角度枚举 (pathData模式使用)"""
    _0 = ('R', 0, False)
    _15 = ('p', 15, False)
    _30 = ('J', 30, False)
    _45 = ('E', 45, False)
    _60 = ('T', 60, False)
    _75 = ('o', 75, False)
    _90 = ('U', 90, False)
    _105 = ('q', 105, False)
    _120 = ('G', 120, False)
    _135 = ('Q', 135, False)
    _150 = ('H', 150, False)
    _165 = ('W', 165, False)
    _180 = ('L', 180, False)
    _195 = ('x', 195, False)
    _210 = ('N', 210, False)
    _225 = ('Z', 225, False)
    _240 = ('F', 240, False)
    _255 = ('V', 255, False)
    _270 = ('D', 270, False)
    _285 = ('Y', 285, False)
    _300 = ('B', 300, False)
    _315 = ('C', 315, False)
    _330 = ('M', 330, False)
    _345 = ('A', 345, False)
    _5 = ('5', 108, True)
    _6 = ('6', 252, True)
    _7 = ('7', 900.0 / 7.0, True)
    _8 = ('8', 360 - 900.0 / 7.0, True)
    NONE = ('!', 0, True)

    def __init__(self, name_char: str, angle: float, dynamic: bool):
        self._name_char = name_char
        self._angle = angle
        self._dynamic = dynamic

    @property
    def name_char(self) -> str:
        return self._name_char

    @property
    def angle(self) -> float:
        return self._angle


CHAR_TO_TILE_ANGLE = {ta.name_char: ta for ta in TileAngle}


# ============================================================================
# Action 基类和具体动作
# ============================================================================

class Action(ABC):
    """动作基类"""

    def __init__(self, event_type: EventType):
        self.event_type = event_type

    @abstractmethod
    def save(self, sb: List[str], floor: int) -> None:
        pass

    def _save_before(self, sb: List[str], floor: int) -> None:
        sb.append(f'\t\t{{ "floor": {floor}, "eventType": "{self.event_type.type_str}"')

    def _save_string(self, sb: List[str], name: str, value: Optional[str]) -> None:
        if value is not None:
            sb.append(f', "{name}": "{value}"')

    def _save_long(self, sb: List[str], name: str, value: Optional[int]) -> None:
        if value is not None:
            sb.append(f', "{name}": {value}')

    def _save_double(self, sb: List[str], name: str, value: Optional[float]) -> None:
        if value is not None:
            sb.append(f', "{name}": ')
            self._append_double_string(sb, value)

    def _append_double_string(self, sb: List[str], value: float) -> None:
        long_value = int(value)
        if value == long_value:
            sb.append(str(long_value))
        else:
            sb.append(f'{value:.6f}')

    def _save_after(self, sb: List[str]) -> None:
        sb.append(' },\n')


class SetSpeed(Action):
    """设置速度动作"""

    def __init__(self, speed_type: Optional[str] = None,
                 beats_per_minute: Optional[float] = None,
                 bpm_multiplier: Optional[float] = None):
        super().__init__(EventType.SET_SPEED)
        self.speed_type = speed_type
        self.beats_per_minute = beats_per_minute
        self.bpm_multiplier = bpm_multiplier

    def save(self, sb: List[str], floor: int) -> None:
        self._save_before(sb, floor)
        self._save_string(sb, "speedType", self.speed_type)
        self._save_double(sb, "beatsPerMinute", self.beats_per_minute)
        self._save_double(sb, "bpmMultiplier", self.bpm_multiplier)
        self._save_after(sb)


class Twirl(Action):
    """旋转动作"""

    def __init__(self):
        super().__init__(EventType.TWIRL)

    def save(self, sb: List[str], floor: int) -> None:
        self._save_before(sb, floor)
        self._save_after(sb)


class Pause(Action):
    """暂停动作"""

    def __init__(self, duration: Optional[float] = None):
        super().__init__(EventType.PAUSE)
        self.duration = duration

    def save(self, sb: List[str], floor: int) -> None:
        self._save_before(sb, floor)
        self._save_double(sb, "duration", self.duration)
        self._save_after(sb)


class SetHitsound(Action):
    """设置打击音动作"""

    def __init__(self, game_sound: str = "Hitsound",
                 hitsound: str = "Kick",
                 hitsound_volume: float = 100):
        super().__init__(EventType.SET_HITSOUND)
        self.game_sound = game_sound
        self.hitsound = hitsound
        self.hitsound_volume = hitsound_volume

    def save(self, sb: List[str], floor: int) -> None:
        self._save_before(sb, floor)
        self._save_string(sb, "gameSound", self.game_sound)
        self._save_string(sb, "hitsound", self.hitsound)
        self._save_double(sb, "hitsoundVolume", self.hitsound_volume)
        self._save_after(sb)


# ============================================================================
# Melody - 旋律数据
# ============================================================================

class Melody:
    """旋律数据"""

    def __init__(self, us: int, tick: int, parent: Optional['Melody'] = None):
        self.us = us  # 微秒时间戳
        self.tick = tick  # MIDI tick
        self.keys: Set[int] = set()  # 当前按下的音符键值

        if parent is not None:
            self.keys = set(parent.keys)


# ============================================================================
# MidiParser - MIDI解析器
# ============================================================================

class MidiParser:
    """MIDI文件解析器"""

    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(self):
        self.tone_hz = [32.7032, 34.6478, 36.7081, 38.8909, 41.2304, 43.6535,
                        46.2493, 48.9994, 51.913, 55.0, 58.2705, 61.7354]
        self.tone_delay: Dict[int, float] = {}
        self.tone_max_octave = 10
        self.tone_min_octave = -10
        self.next_key_time: Dict[int, float] = {}

        self._init_tone_delay()

    def _init_tone_delay(self) -> None:
        """初始化音调延迟表"""
        for i in range(len(self.tone_hz)):
            self.tone_delay[i] = 1000000 / self.tone_hz[i]

        for i in range(1, self.tone_max_octave):
            offset = i * len(self.tone_hz)
            for j in range(len(self.tone_hz)):
                self.tone_delay[offset + j] = self.tone_delay[offset + j - len(self.tone_hz)] / 2

        for i in range(-1, self.tone_min_octave, -1):
            offset = i * len(self.tone_hz)
            for j in range(len(self.tone_hz)):
                self.tone_delay[offset + j] = self.tone_delay[offset + j + len(self.tone_hz)] * 2

    def parse_to_melody_list(self, midi_file: MidiFile, disable: List[bool]) -> List[Melody]:
        """将MIDI文件解析为旋律列表"""
        melody_list: List[Melody] = []
        curr_melody = Melody(0, 0)

        tracks = midi_file.tracks
        resolution = midi_file.ticks_per_beat
        tempo = 500000.0
        tick_multiply = tempo / resolution
        curr_time_us = 0
        last_tick = 0

        # 收集所有事件并按时间排序
        all_events = []
        for track_idx, track in enumerate(tracks):
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                all_events.append((abs_tick, track_idx, msg))

        all_events.sort(key=lambda x: x[0])

        for event_tick, track_idx, msg in all_events:
            if track_idx < len(disable) and disable[track_idx]:
                continue

            if msg.type == 'note_on' or msg.type == 'note_off':
                key = msg.note
                velocity = msg.velocity

                if event_tick != curr_melody.tick:
                    melody_list.append(curr_melody)
                    curr_time_us += (event_tick - last_tick) * tick_multiply
                    last_tick = event_tick
                    curr_melody = Melody(int(curr_time_us), event_tick, curr_melody)

                if msg.type == 'note_on' and velocity > 0:
                    curr_melody.keys.add(key)
                else:
                    curr_melody.keys.discard(key)

            elif msg.type == 'set_tempo':
                curr_time_us += (event_tick - last_tick) * tick_multiply
                last_tick = event_tick
                tempo = msg.tempo
                tick_multiply = tempo / resolution

        melody_list.append(curr_melody)
        return melody_list

    def melody_to_us_delay_list(self, melody_list: List[Melody], octave_offset: int) -> List[int]:
        """将旋律列表转换为微秒延迟列表"""
        curr_time = 0
        self.next_key_time.clear()
        us_delay_list: List[int] = []

        for i in range(1, len(melody_list)):
            curr = melody_list[i - 1]
            next_melody = melody_list[i]

            if len(curr.keys) == 0:
                diff_time = next_melody.us - curr_time
                if diff_time == 0:
                    continue
                us_delay_list.append(diff_time)
                curr_time = next_melody.us
            else:
                prev_time = curr_time
                min_time_keys: Set[int] = set()

                while True:
                    min_time = sys.maxsize
                    min_time_keys.clear()

                    for key in curr.keys:
                        adjusted_key = key + octave_offset * 12
                        next_time = self._get_next_time(curr_time, adjusted_key)

                        if next_time == min_time:
                            min_time_keys.add(adjusted_key)
                        elif next_time < min_time:
                            min_time_keys.clear()
                            min_time_keys.add(adjusted_key)
                            min_time = next_time

                    if min_time >= next_melody.us:
                        break

                    for key in min_time_keys:
                        self._add_next_time(key)

                    diff_time = min_time - prev_time
                    if diff_time == 0:
                        continue

                    us_delay_list.append(diff_time)
                    prev_time = min_time

                curr_time = prev_time

        return us_delay_list

    def _get_next_time(self, time_from: int, key: int) -> int:
        """获取下一个音符时间"""
        next_time = self.next_key_time.get(key, 0.0)

        if next_time <= time_from:
            delay_time = self.tone_delay.get(key)
            if delay_time is None:
                delay_time = 1000000 / 32.7032

            next_time = delay_time * int(time_from / delay_time)
            if next_time <= time_from:
                next_time += delay_time

        self.next_key_time[key] = next_time
        return int(next_time)

    def _add_next_time(self, key: int) -> None:
        """增加音符时间"""
        delay = self.tone_delay.get(key, 1000000 / 32.7032)
        self.next_key_time[key] = self.next_key_time.get(key, 0.0) + delay


# ============================================================================
# MapSetting - 地图设置
# ============================================================================

class MapSetting:
    """ADOFAI地图设置"""

    def __init__(self):
        self.version: int = 2
        self.artist: str = "Artist"
        self.special_artist_type: str = "None"
        self.artist_permission: str = ""
        self.song: str = "Song"
        self.author: str = "Author"
        self.separate_countdown_time: str = "Enabled"
        self.preview_image: str = ""
        self.preview_icon: str = ""
        self.preview_icon_color: str = "003f52"
        self.preview_song_start: int = 0
        self.preview_song_duration: int = 10
        self.seizure_warning: str = "Disabled"
        self.level_desc: str = "Describe your level!"
        self.level_tags: str = ""
        self.artist_links: str = ""
        self.difficulty: int = 1
        self.song_filename: str = ""
        self.bpm: float = 100.0
        self.volume: int = 100
        self.offset: int = 0
        self.pitch: int = 100
        self.hitsound: str = "Kick"
        self.hitsound_volume: int = 100
        self.countdown_ticks: int = 4
        self.track_color_type: str = "Single"
        self.track_color: str = "debb7b"
        self.secondary_track_color: str = "ffffff"
        self.track_color_anim_duration: float = 2.0
        self.track_color_pulse: str = "None"
        self.track_pulse_length: int = 10
        self.track_style: str = "Standard"
        self.track_animation: str = "None"
        self.beats_ahead: float = 3.0
        self.track_disappear_animation: str = "None"
        self.beats_behind: float = 4.0
        self.background_color: str = "000000"
        self.bg_image: str = ""
        self.bg_image_color: str = "ffffff"
        self.parallax: List[int] = [100, 100]
        self.bg_display_mode: str = "FitToScreen"
        self.lock_rot: str = "Disabled"
        self.loop_bg: str = "Disabled"
        self.unscaled_size: int = 100
        self.relative_to: str = "Player"
        self.position: List[int] = [0, 0]
        self.rotation: float = 0.0
        self.zoom: int = 100
        self.bg_video: str = ""
        self.loop_video: str = "Disabled"
        self.vid_offset: int = 0
        self.floor_icon_outlines: str = "Disabled"
        self.stick_to_floors: str = "Disabled"
        self.planet_ease: str = "Linear"
        self.planet_ease_parts: int = 1

    def save(self, sb: List[str]) -> None:
        """保存设置到字符串构建器"""
        self._save_variable(sb, "version", self.version)
        self._save_variable(sb, "artist", self.artist)
        self._save_variable(sb, "specialArtistType", self.special_artist_type)
        self._save_variable(sb, "artistPermission", self.artist_permission)
        self._save_variable(sb, "song", self.song)
        self._save_variable(sb, "author", self.author)
        self._save_variable(sb, "separateCountdownTime", self.separate_countdown_time)
        self._save_variable(sb, "previewImage", self.preview_image)
        self._save_variable(sb, "previewIcon", self.preview_icon)
        self._save_variable(sb, "previewIconColor", self.preview_icon_color)
        self._save_variable(sb, "previewSongStart", self.preview_song_start)
        self._save_variable(sb, "previewSongDuration", self.preview_song_duration)
        self._save_variable(sb, "seizureWarning", self.seizure_warning)
        self._save_variable(sb, "levelDesc", self.level_desc)
        self._save_variable(sb, "levelTags", self.level_tags)
        self._save_variable(sb, "artistLinks", self.artist_links)
        self._save_variable(sb, "difficulty", self.difficulty)
        self._save_variable(sb, "songFilename", self.song_filename)
        self._save_variable(sb, "bpm", self.bpm)
        self._save_variable(sb, "volume", self.volume)
        self._save_variable(sb, "offset", self.offset)
        self._save_variable(sb, "pitch", self.pitch)
        self._save_variable(sb, "hitsound", self.hitsound)
        self._save_variable(sb, "hitsoundVolume", self.hitsound_volume)
        self._save_variable(sb, "countdownTicks", self.countdown_ticks)
        self._save_variable(sb, "trackColorType", self.track_color_type)
        self._save_variable(sb, "trackColor", self.track_color)
        self._save_variable(sb, "secondaryTrackColor", self.secondary_track_color)
        self._save_variable(sb, "trackColorAnimDuration", self.track_color_anim_duration)
        self._save_variable(sb, "trackColorPulse", self.track_color_pulse)
        self._save_variable(sb, "trackPulseLength", self.track_pulse_length)
        self._save_variable(sb, "trackStyle", self.track_style)
        self._save_variable(sb, "trackAnimation", self.track_animation)
        self._save_variable(sb, "beatsAhead", self.beats_ahead)
        self._save_variable(sb, "trackDisappearAnimation", self.track_disappear_animation)
        self._save_variable(sb, "beatsBehind", self.beats_behind)
        self._save_variable(sb, "backgroundColor", self.background_color)
        self._save_variable(sb, "bgImage", self.bg_image)
        self._save_variable(sb, "bgImageColor", self.bg_image_color)
        self._save_variable(sb, "parallax", self.parallax)
        self._save_variable(sb, "bgDisplayMode", self.bg_display_mode)
        self._save_variable(sb, "lockRot", self.lock_rot)
        self._save_variable(sb, "loopBG", self.loop_bg)
        self._save_variable(sb, "unscaledSize", self.unscaled_size)
        self._save_variable(sb, "relativeTo", self.relative_to)
        self._save_variable(sb, "position", self.position)
        self._save_variable(sb, "rotation", self.rotation)
        self._save_variable(sb, "zoom", self.zoom)
        self._save_variable(sb, "bgVideo", self.bg_video)
        self._save_variable(sb, "loopVideo", self.loop_video)
        self._save_variable(sb, "vidOffset", self.vid_offset)
        self._save_variable(sb, "floorIconOutlines", self.floor_icon_outlines)
        self._save_variable(sb, "stickToFloors", self.stick_to_floors)
        self._save_variable(sb, "planetEase", self.planet_ease)
        self._save_variable(sb, "planetEaseParts", self.planet_ease_parts)

    def _save_variable(self, sb: List[str], name: str, value: Any) -> None:
        """保存变量到字符串构建器"""
        if value is None:
            return
        if isinstance(value, str):
            sb.append(f'\t\t"{name}": "{value}", \n')
        elif isinstance(value, int):
            sb.append(f'\t\t"{name}": {value}, \n')
        elif isinstance(value, float):
            long_value = int(value)
            if value == long_value:
                sb.append(f'\t\t"{name}": {long_value}, \n')
            else:
                sb.append(f'\t\t"{name}": {value:.6f}, \n')
        elif isinstance(value, list):
            sb.append(f'\t\t"{name}": [')
            for i, v in enumerate(value):
                sb.append(str(v))
                if i < len(value) - 1:
                    sb.append(', ')
            sb.append('], \n')


# ============================================================================
# TileData - 瓷砖数据
# ============================================================================

class TileData:
    """ADOFAI瓷砖数据"""

    def __init__(self, floor: int, tile_angle: TileAngle = None, angle: float = None):
        self.floor = floor
        self.tile_angle = tile_angle  # 用于 pathData 模式
        self.angle = angle  # 用于 angleData 模式
        self.action_list_map: Dict[EventType, List[Action]] = {}

    def save(self, sb: List[str]) -> None:
        """保存瓷砖数据到字符串构建器"""
        event_order = [
            EventType.SET_SPEED,
            EventType.TWIRL,
            EventType.PAUSE,
            EventType.CHECKPOINT,
            EventType.CUSTOM_BACKGROUND,
            EventType.COLOR_TRACK,
            EventType.ANIMATE_TRACK,
            EventType.ADD_DECORATION,
            EventType.FLASH,
            EventType.MOVE_CAMERA,
            EventType.SET_HITSOUND,
            EventType.RECOLOR_TRACK,
            EventType.MOVE_TRACK,
            EventType.SET_FILTER,
            EventType.HALL_OF_MIRRORS,
            EventType.SHAKE_SCREEN,
            EventType.SET_PLANET_ROTATION,
            EventType.MOVE_DECORATIONS,
            EventType.POSITION_TRACK,
            EventType.REPEAT_EVENTS,
            EventType.BLOOM,
            EventType.SET_CONDITIONAL_EVENTS
        ]

        for event_type in event_order:
            self._save(sb, event_type)

    def _save(self, sb: List[str], event_type: EventType) -> None:
        """保存特定类型的事件"""
        action_list = self.action_list_map.get(event_type)
        if action_list is None:
            return
        for action in action_list:
            action.save(sb, self.floor)

    def get_action_list(self, event_type: EventType) -> List[Action]:
        """获取指定类型的事件列表"""
        action_list = self.action_list_map.get(event_type)
        if action_list is None:
            action_list = []
            self.action_list_map[event_type] = action_list
        return action_list


# ============================================================================
# MapData - 地图数据
# ============================================================================

class MapData:
    """ADOFAI地图数据"""

    def __init__(self, use_angle_data: bool = False):
        self.map_setting = MapSetting()
        self.tile_data_list: List[TileData] = []
        self.use_angle_data = use_angle_data

    def save(self, path: str) -> None:
        """保存地图到文件"""
        sb: List[str] = []

        sb.append('{\n')

        if self.use_angle_data:
            sb.append('\t"angleData": [')
            for i, tile_data in enumerate(self.tile_data_list):
                if i > 0:
                    sb.append(', ')
                angle = tile_data.angle
                long_value = int(angle)
                if angle == long_value:
                    sb.append(str(long_value))
                else:
                    sb.append(f'{angle:.6f}')
            sb.append('], \n')
        else:
            sb.append('\t"pathData": "')
            for i, tile_data in enumerate(self.tile_data_list):
                if i > 0:
                    sb.append(tile_data.tile_angle.name_char)
            sb.append('", \n')

        sb.append('\t"settings":\n\t{\n')
        self.map_setting.save(sb)
        sb.append('\t},\n\t"actions":\n\t[\n')

        for tile_data in self.tile_data_list:
            tile_data.save(sb)

        sb.append('\t]\n}\n')

        content = ''.join(sb)
        with open(path, 'w', encoding='utf-8-sig') as f:
            f.write(content)
