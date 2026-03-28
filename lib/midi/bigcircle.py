# -*- coding: utf-8 -*-
"""
大圈圈模式转换器 (Big Circle Mode Converter)
为每个音符生成圆弧形状的轨道

核心原理：
- 每个音符根据其频率和持续时间生成N块瓷砖形成一个圆弧
- 使用 Twirl 在 floor 0 使全局逆时针旋转
- 使用 PositionTrack 调整轨道位置，形成大圈圈效果
- BPM公式: BPM = f × 60 × (1 + 2/N)，实现逆时针锁外轨

作者: 基于 apofai_musicbox.py 融合
版本: v0.7-BigCircle-FixedTwirl
"""

import math
from typing import List, Optional, Tuple

from .common import (
    MapData,
    TileData,
    EventType,
    SetSpeed,
    Twirl,
    Pause,
    PositionTrack
)

# A4 标准音频率
A4_FREQUENCY = 440.0


class BigCircleConverter:
    """大圈圈模式转换器"""

    def __init__(self):
        self.version = "v0.7-BigCircle"

    def convert_track(
        self,
        notes: List[Tuple[float, int]],
        track_name: str = "",
        base_path: str = ""
    ) -> Tuple[MapData, int, str]:
        """
        将音符列表转换为大圈圈模式的ADOFAI地图数据
        
        Args:
            notes: 音符列表，每个元素为 (时间秒, MIDI音高)
            track_name: 轨道名称（用于作者信息和文件名）
            base_path: 输出文件基础路径
        
        Returns:
            Tuple[MapData, int, str]: (地图数据, 偏移毫秒, 输出文件路径)
        """
        if not notes:
            return None, 0, None

        # 单音过滤：同一时刻只保留最高音
        unique_notes = self._filter_unique_notes(notes)
        
        if len(unique_notes) == 0:
            return None, 0, None

        map_data = MapData(use_angle_data=True)
        map_data.map_setting.author = f"apofaiautomaker (Big Circle Mode)"
        map_data.map_setting.level_desc = "Big Circle Mode"
        
        tile_data_list = map_data.tile_data_list
        
        # 添加起始瓷砖 (floor 0, 角度 = 0)
        tile_data_list.append(TileData(0, angle=0))
        
        # ====== 核心修改：在第0块地板放置唯一的Twirl，让全局变为逆时针旋转 ======
        twirl_tile = tile_data_list[0]
        twirl_tile.get_action_list(EventType.TWIRL).append(Twirl())

        floor = 0
        offset_ms = int(unique_notes[0][0] * 1000)
        actual_time = unique_notes[0][0]
        prev_R = 1.0
        
        angle_data = [0]
        actions = []
        
        for idx in range(len(unique_notes)):
            start_time, pitch = unique_notes[idx]
            
            if idx < len(unique_notes) - 1:
                target_next_time = unique_notes[idx+1][0]
            else:
                target_next_time = actual_time + 1.0 
                
            # 计算频率
            f = A4_FREQUENCY * (2 ** ((pitch - 69) / 12))
            
            wait_time = start_time - actual_time
            if wait_time < 0: 
                wait_time = 0
            
            D_avail = target_next_time - (actual_time + wait_time)
            if D_avail <= 0: 
                D_avail = 0.001
                
            N = max(1, int(math.floor(D_avail * f + 1e-6)))
            
            if N > 1:
                current_R = 1.0 / (2.0 * math.sin(math.pi / N))
            else:
                current_R = 1.0
                
            # 逆时针锁外轨公式：BPM = f * 60 * (1 + 2/N)
            BPM = f * 60.0 * (1.0 + 2.0 / N)
            
            # 添加 SetSpeed 事件
            speed_tile = tile_data_list[floor]
            speed_tile.get_action_list(EventType.SET_SPEED).append(
                SetSpeed("Bpm", round(BPM, 10), 1.0)
            )
            
            if wait_time > 1e-5:
                pause_beats = wait_time * (BPM / 60.0)
                pause_tile = tile_data_list[floor]
                pause_tile.get_action_list(EventType.PAUSE).append(
                    Pause(round(pause_beats, 10), countdown_ticks=0, angle_correction_dir=-1)
                )
                
            if idx > 0:
                pos_tile = None
                if floor + 1 < len(tile_data_list):
                    pos_tile = tile_data_list[floor + 1]
                else:
                    pos_tile = TileData(floor + 1, angle=0)
                    tile_data_list.append(pos_tile)
                pos_tile.get_action_list(EventType.POSITION_TRACK).append(
                    PositionTrack(
                        position_offset=[round(prev_R, 3), 0],
                        relative_to=[0, "ThisTile"],
                        just_this_tile=False,
                        editor_only=False
                    )
                )
                
            prev_R = current_R
            delta_angle = 360.0 / N
            
            for j in range(N):
                prev_angle = angle_data[-1]
                new_angle = (prev_angle + delta_angle) % 360  # 向上递增
                angle_data.append(round(new_angle, 10))
                floor += 1
                
                # 添加新瓷砖
                new_tile = TileData(floor, angle=round(new_angle, 10))
                tile_data_list.append(new_tile)
                
            actual_time = actual_time + wait_time + (N / f)

        # 生成输出文件路径
        if track_name:
            out_path = f"{base_path}_Track{track_name}.adofai"
        else:
            out_path = f"{base_path}_bigcircle.adofai"

        return map_data, offset_ms, out_path

    def _filter_unique_notes(self, notes: List[Tuple[float, int]]) -> List[Tuple[float, int]]:
        """
        过滤同一时刻的音符，只保留最高音
        
        Args:
            notes: 原始音符列表
        
        Returns:
            List[Tuple[float, int]]: 过滤后的音符列表
        """
        unique_notes = []
        for t, p in notes:
            if not unique_notes:
                unique_notes.append((t, p))
            else:
                if t - unique_notes[-1][0] < 0.001:
                    if p > unique_notes[-1][1]:
                        unique_notes[-1] = (t, p)
                else:
                    unique_notes.append((t, p))
        return unique_notes

    def parse_midi_track(self, midi_file, track_idx: int) -> List[Tuple[float, int]]:
        """
        解析MIDI文件的指定轨道，提取音符列表
        
        Args:
            midi_file: MidiFile对象
            track_idx: 轨道索引
        
        Returns:
            List[Tuple[float, int]]: 音符列表 [(时间秒, MIDI音高), ...]
        """
        if track_idx >= len(midi_file.tracks):
            return []
            
        track = midi_file.tracks[track_idx]
        timebound = 0
        tempo = 500000  # 默认tempo (微秒/拍)
        notes = []
        
        for msg in track:
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.time > 0:
                timebound += msg.time / midi_file.ticks_per_beat * tempo * 1e-6
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append((timebound, msg.note))
                
        return notes
