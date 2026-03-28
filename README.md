# ADOFAI Music Converter

**[中文文档 (Chinese README)](./README_CN.md)**

A converter tool from MIDI or audio files to ADOFAI level files.

## Overview

This tool converts MIDI files or audio files into level files for [A Dance of Fire and Ice (ADOFAI)](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/).

### Input Sources
- **MIDI File**: Extract beats from MIDI note events
- **Audio File**: Auto-detect beats from audio waveform (WAV, MP3, FLAC, VORBIS)

### Conversion Modes

| Mode | Description | BPM | Angle |
|------|-------------|-----|-------|
| angleData | Pure angle control | Fixed | Dynamic |
| Zipper Angle | Fixed angle + SetSpeed | Dynamic | Fixed |
| Full Sample | Straight track + hitsounds | Fixed | Fixed (straight) |
| Big Circle | Arc-shaped track | Dynamic | Dynamic |

## Features

- **Dual Input Support**: MIDI files and audio files
- **Four Conversion Modes**: angleData, Zipper Angle, Full Sample, Big Circle
- **Multi-language**: English and Simplified Chinese
- **Auto BPM Detection**: Automatically calculates optimal BPM
- **Customizable Parameters**: Angle, smoothness, threshold, etc.
- **Big Circle Mode**: Each MIDI track outputs a separate file, with track disable option

## Project Structure

```
ADOFAI_Music_Converter/
├── main.py                    # Main entry point
├── lib/
│   ├── midi/
│   │   ├── common.py          # MIDI parser and data structures
│   │   ├── angleD.py          # angleData mode for MIDI
│   │   ├── angleD_custom.py   # Zipper mode for MIDI
│   │   └── bigcircle.py       # Big Circle mode for MIDI
│   └── audio/
│       ├── processor.py       # Audio loader
│       ├── detector.py        # Beat detection (FFT + Gaussian)
│       └── converter.py       # angleData + Zipper mode for audio
├── i18n/
│   ├── i18n.py               # Internationalization
│   ├── zh_CN.json            # Simplified Chinese
│   └── en_US.json            # English
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install mido numpy scipy miniaudio
```

**Note**: Audio processing uses [miniaudio](https://github.com/irmen/pyminiaudio) library, no ffmpeg installation required.

## Usage

### Interactive CLI

```bash
python main.py
```

### Workflow

```
1. Select language
2. Select input source (MIDI/Audio)
3. Enter file path
4. Select conversion mode (angleData/Zipper)
5. Set parameters (based on mode)
6. Generate level file
```

### Parameters

#### MIDI Input
| Parameter | Description | Default |
|-----------|-------------|---------|
| Track selection | Enable/disable MIDI tracks | All enabled |
| Octave offset | Pitch adjustment | -4 |

#### Audio Input
| Parameter | Description | Default |
|-----------|-------------|---------|
| Smoothness | Beat density (-5 to 5) | 0 |
| Threshold | Filter weak beats | 0 |

#### Conversion Modes
| Parameter | Mode | Description | Default |
|-----------|------|-------------|---------|
| Base BPM | angleData | Fixed BPM for angle calculation | Auto |
| Angle | Zipper | Fixed angle between tiles | 15° |

## Technical Details

### Core Principle

**Time Formula**: `Time = RotationAngle / 180 × 60 / BPM`

Both modes produce identical timing:
- **angleData Mode**: Fixed BPM → Dynamic angle = Time × BPM × 180 / 60
- **Zipper Mode**: Fixed angle → Dynamic BPM = Angle / 180 × 60 / Time

### Magic Number

For Zipper mode:
```
Magic Number = 180 / Angle
Display BPM = Actual BPM / Magic Number
```

Example: 15° angle → Magic Number = 12

### Beat Detection (Audio)

1. **Energy Signal**: Sample²
2. **Gaussian Smoothing**: FFT convolution
3. **Peak Detection**: scipy.signal.find_peaks

### Angle Validation

| Angle | Behavior |
|-------|----------|
| ≤ 0° | Rejected (no movement) |
| 0° < θ < 180° | Normal operation |
| = 180° | Straight line level |
| > 180° | Rejected |

## Output Files

- angleData mode: `filename_angle.adofai`
- Zipper mode: `filename_zipper_XX.adofai` (XX = angle)
- Full Sample mode: `filename_fullsample_XXXX.adofai` (XXXX = sample rate)
- Big Circle mode: `filename_TrackN.adofai` (N = track index, one file per track)

## Version History

### v2.5.0
- Added Big Circle Mode (大圈圈模式)
- Each MIDI track generates a separate level file
- Track disable option for Big Circle Mode
- PositionTrack and enhanced Pause event support

### v2.4.0
- Use miniaudio instead of ffmpeg for audio decoding
- Support more audio formats: MP3, FLAC, VORBIS
- No system ffmpeg installation required, pure Python pip install

### v2.3.0
- Added audio file input support
- Merged apofai beat detection functionality
- Two conversion modes for both MIDI and audio
- Identical timing across all modes

### v2.2.0
- Simplified to two conversion modes
- Added Zipper Angle mode

### v2.1.0
- Modular project structure
- i18n support

### v2.0.0
- angleData mode
- Pause event support

### v1.0.0
- Initial Python rewrite

## Acknowledgments

- Original Java developer: [Luxus io](https://github.com/Luxusio/ADOFAI-Midi-Converter)
- [pyadofai](https://github.com/TonyLimps/pyadofai) - angleData calculations
- [apofai](https://github.com/sky-sama/apofai_main_console) - Audio beat detection reference
- [pyminiaudio](https://github.com/irmen/pyminiaudio) - Audio decoding library

## License

Open source. Refer to the original Java project for licensing terms.
