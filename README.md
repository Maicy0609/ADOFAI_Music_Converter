# ADOFAI Music Converter

**[中文文档 (Chinese README)](./README_CN.md)**

A converter tool from MIDI music files to ADOFAI level files.

## Overview

This tool converts MIDI files into playable level files for [A Dance of Fire and Ice (ADOFAI)](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/). It supports two conversion modes to accommodate different use cases and precision requirements.

## Features

- **Two Conversion Modes**:
  - **pathData Mode (RW Mode)**: Uses SetSpeed + Twirl events for timing control
  - **angleData Mode**: Pure angle control with arbitrary floating-point precision
- **Multi-language Support**: English and Simplified Chinese
- **Interactive CLI**: User-friendly command-line interface
- **Auto BPM Calculation**: Automatically calculates optimal base BPM for angleData mode

## Project Structure

```
ADOFAI_Music_Converter/
├── main.py                    # Main entry point
├── lib/
│   └── midi/
│       ├── __init__.py        # Module initialization
│       ├── common.py          # Shared data structures and MIDI parser
│       ├── pathD.py           # pathData mode implementation
│       └── angleD.py          # angleData mode implementation
├── i18n/
│   ├── i18n.py               # Internationalization controller
│   ├── zh_CN.json            # Simplified Chinese translations
│   └── en_US.json            # English translations
├── README.md                  # English documentation (this file)
├── README_CN.md              # Chinese documentation
└── requirements.txt          # Python dependencies
```

## Installation

```bash
pip install mido
```

## Usage

### Interactive CLI

```bash
python main.py
```

Follow the prompts:
1. Select language (English/Chinese)
2. Enter or drag-and-drop MIDI file path
3. Select conversion mode (1=pathData, 2=angleData)
4. Select tracks to enable/disable
5. Set octave offset (recommended: -4 to -2)
6. For angleData mode: set base BPM (leave empty for auto-calculation)

### Output Files

After conversion, output files are generated in the same directory as the MIDI file:
- pathData mode: `filename_rw.adofai`
- angleData mode: `filename_angle.adofai`

## Conversion Modes Comparison

| Feature | pathData Mode | angleData Mode |
|---------|---------------|----------------|
| Mechanism | pathData + SetSpeed + Twirl | Pure angleData |
| Compatibility | Best | Good |
| Precision | High | Highest |
| BPM Changes | Dynamic adjustment | Fixed base BPM |
| Long Delays | SetSpeed events | Pause events |

## Technical Details

### Magic Numbers Explained

This project uses several important constants. Here's what they mean:

| Constant | Value | Explanation |
|----------|-------|-------------|
| `12` | 12 | The BPM multiplier factor in pathData mode. Since RW pattern gives 15° effective angle per beat (180°/15° = 12), the actual BPM appears 12x faster. Formula: `displayed_bpm = actual_bpm / 12` |
| `15°` | 15 | Effective rotation angle in pathData mode. R=0°, W=165°, Twirl makes: 180°-165°=15° |
| `180°` | 180 | One full beat = 180° rotation in ADOFAI |
| `500000 μs` | 500000 | Default MIDI tempo (120 BPM = 500000 microseconds per beat) |

### pathData Mode (RW Mode) Algorithm

The pathData mode uses a clever trick to achieve variable timing:

1. **Path Pattern**: Uses RWRW... pattern where:
   - R = 0° (right)
   - W = 165° (slightly less than 180°)

2. **Twirl Effect**: Twirl events flip the rotation direction, making the effective angle:
   - Without Twirl: 180° - 0° = 180° OR 180° - 165° = 15°
   - With Twirl: The 165° becomes effectively 15° (180° - 165° = 15°)

3. **BPM Calculation**:
   ```
   Time = 15°/180° × 60/BPM seconds
   BPM = 60 × 1000000 / us_delay / 12
   ```

4. **Why 12?**: Since each beat is only 15° instead of 180°, the music plays 12x faster. We divide by 12 to compensate.

### angleData Mode Algorithm

The angleData mode uses direct angle control:

1. **Angle Representation**: Each tile stores an absolute angle in range (0, 360]

2. **Rotation Calculation**:
   ```
   rotation_angle = (prev_angle + 180 - curr_angle) mod 360
   if rotation_angle <= 0:
       rotation_angle += 360
   ```

3. **Time Formula**:
   ```
   beats = rotation_angle / 180
   time = beats × 60 / BPM
   ```

4. **Long Delays (>360° rotation)**: When the required rotation exceeds 360°, Pause events are used:
   ```
   base_rotate_angle = total_rotate_angle % 360
   pause_beats = (total_rotate_angle - base_rotate_angle) / 180
   ```

5. **Base BPM Selection**: Uses median of all pathData BPM values for stability.

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `MidiParser` | `lib/midi/common.py` | Parses MIDI files into melody data |
| `PathDataConverter` | `lib/midi/pathD.py` | Converts to pathData format |
| `AngleDataConverter` | `lib/midi/angleD.py` | Converts to angleData format |
| `MapData` | `lib/midi/common.py` | Represents ADOFAI level data |
| `TileData` | `lib/midi/common.py` | Represents a single tile |

## Naming Conventions

This project strictly follows these naming conventions:

- **ADOFAI** - Always uppercase (abbreviation for "A Dance of Fire and Ice")
- **pathData** - CamelCase, first letter lowercase
- **angleData** - CamelCase, first letter lowercase

## Version History

### v2.1.0
- Modular project structure
- Internationalization support (i18n)
- Separated pathData and angleData implementations

### v2.0.0
- Added angleData mode
- Fixed angleData timing calculation
- Added Pause event support for long delays
- Optimized base BPM selection algorithm

### v1.0.0
- Initial Python rewrite based on Java version
- pathData mode support

## Acknowledgments

- Original Java developer: [Luxus io](https://github.com/Luxusio/ADOFAI-Midi-Converter)
- [pyadofai library](https://github.com/TonyLimps/pyadofai) - Reference for angleData calculations

## License

This project is open source. Please refer to the original Java project for licensing terms.
