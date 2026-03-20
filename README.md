# ADOFAI Music Converter

**[中文文档 (Chinese README)](./README_CN.md)**

A converter tool from MIDI music files to ADOFAI level files.

## Overview

This tool converts MIDI files into level files for [A Dance of Fire and Ice (ADOFAI)](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/). It supports two conversion modes.

## Features

- **Two Conversion Modes**:
  - **angleData Mode**: Pure angle control with fixed base BPM
  - **Zipper Angle Mode**: Uses angleData + SetSpeed + Pause with customizable angle
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
│       ├── angleD_custom.py   # Zipper angle mode implementation
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
3. Select conversion mode (1=angleData, 2=Zipper Angle)
4. Select tracks to enable/disable
5. Set octave offset (recommended: -4 to -2)
6. Set additional parameters based on mode (BPM/Angle)

### Output Files

After conversion, output files are generated in the same directory as the MIDI file:
- angleData mode: `filename_angle.adofai`
- Zipper Angle mode: `filename_zipper_angle.adofai`

## Conversion Modes Comparison

| Feature | angleData Mode | Zipper Angle Mode |
|---------|----------------|-------------------|
| Mechanism | Pure angleData | angleData + SetSpeed + Pause |
| Angle | Dynamic calculation | User-defined |
| BPM | Fixed base | Dynamic adjustment |
| Precision | Highest | High |
| Long Delays | Pause events | Pause events |

## Technical Details

### Magic Numbers Explained

This project uses several important constants. Here's what they mean:

| Constant | Value | Explanation |
|----------|-------|-------------|
| `Magic Number` | 180/angle | BPM multiplier factor. Smaller angle = larger magic number. Formula: `displayed_bpm = actual_bpm / magic_number` |
| `180°` | 180 | One full beat = 180° rotation in ADOFAI. 180° angle = straight line |
| `500000 μs` | 500000 | Default MIDI tempo (120 BPM = 500000 microseconds per beat) |

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

4. **Long Delays (>360° rotation)**: Pause events are used when rotation exceeds 360°

### Zipper Angle Mode Algorithm

The Zipper Angle mode allows users to set a fixed angle between tiles:

1. **Angle Definition**: User inputs angle θ (0° < θ ≤ 180°)

2. **Angle Sequence Calculation**:
   ```
   angle[0] = 0°
   angle[i] = (angle[i-1] + 180 - θ) mod 360
   ```

3. **Magic Number Calculation**:
   ```
   magic_number = 180 / θ
   ```

4. **BPM Calculation**:
   ```
   Time = θ/180 × 60/BPM seconds
   BPM = 60 × 1000000 / us_delay / magic_number
   ```

5. **Special Handling**:
   - Angle = 0°: Rejected (invalid, no movement possible)
   - Angle = 180°: Generates straight line level

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `MidiParser` | `lib/midi/common.py` | Parses MIDI files into melody data |
| `AngleCustomConverter` | `lib/midi/angleD_custom.py` | Zipper angle mode converter |
| `AngleDataConverter` | `lib/midi/angleD.py` | angleData mode converter |
| `MapData` | `lib/midi/common.py` | Represents ADOFAI level data |
| `TileData` | `lib/midi/common.py` | Represents a single tile |

## Version History

### v2.2.0
- Simplified to two conversion modes
- Added Zipper Angle mode
- Angle validation: reject 0°, special handling for 180°
- Dynamic magic number calculation

### v2.1.0
- Modular project structure
- Internationalization support (i18n)

### v2.0.0
- Added angleData mode
- Fixed angleData timing calculation
- Added Pause event support for long delays

### v1.0.0
- Initial Python rewrite based on Java version

## Acknowledgments

- Original Java developer: [Luxus io](https://github.com/Luxusio/ADOFAI-Midi-Converter)
- [pyadofai library](https://github.com/TonyLimps/pyadofai) - Reference for angleData calculations

## License

This project is open source. Please refer to the original Java project for licensing terms.
