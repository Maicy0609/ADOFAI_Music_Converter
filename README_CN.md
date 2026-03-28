# ADOFAI Music Converter

**[English Documentation](./README.md)**

将MIDI或音频文件转换为ADOFAI谱面文件的工具。

## 概述

本工具可将MIDI文件或音频文件转换为《[冰与火之舞 (A Dance of Fire and Ice)](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/)》的谱面文件。

### 输入源
- **MIDI文件**：从MIDI音符事件提取节拍
- **音频文件**：从音频波形自动检测节拍（支持WAV、MP3、FLAC、VORBIS）

### 转换模式
两种模式生成的**拍子绝对时间完全相同**！

| 模式 | 描述 | BPM | 角度 |
|------|------|-----|------|
| angleData | 纯角度控制 | 固定 | 动态 |
| 拉链夹角 | 固定角度 + SetSpeed | 动态 | 固定 |
| 全采音 | 直线轨道 + 打击音 | 固定 | 固定(直线) |
| 大圈圈 | 圆弧轨道 | 动态 | 动态 |

## 功能特点

- **双输入支持**：MIDI文件和音频文件
- **四种转换模式**：angleData模式、拉链夹角模式、全采音模式、大圈圈模式
- **多语言**：英文和简体中文
- **自动BPM检测**：自动计算最优BPM
- **可调参数**：角度、平滑度、阈值等
- **大圈圈模式**：每个MIDI轨道单独输出文件，可禁用指定轨道

## 项目结构

```
ADOFAI_Music_Converter/
├── main.py                    # 主入口
├── lib/
│   ├── midi/
│   │   ├── common.py          # MIDI解析器和数据结构
│   │   ├── angleD.py          # angleData模式 (MIDI)
│   │   ├── angleD_custom.py   # 拉链模式 (MIDI)
│   │   └── bigcircle.py       # 大圈圈模式 (MIDI)
│   └── audio/
│       ├── processor.py       # 音频加载器
│       ├── detector.py        # 节拍检测 (FFT + 高斯)
│       └── converter.py       # angleData + 拉链模式 (音频)
├── i18n/
│   ├── i18n.py               # 国际化
│   ├── zh_CN.json            # 简体中文
│   └── en_US.json            # 英文
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

或者手动安装：
```bash
pip install mido numpy scipy miniaudio
```

**注意**：音频处理使用 [miniaudio](https://github.com/irmen/pyminiaudio) 库，无需安装 ffmpeg。

## 使用方法

### 交互式命令行

```bash
python main.py
```

### 工作流程

```
1. 选择语言
2. 选择输入源（MIDI/音频）
3. 输入文件路径
4. 选择转换模式（angleData/拉链）
5. 设置参数（根据模式不同）
6. 生成谱面文件
```

### 参数说明

#### MIDI输入
| 参数 | 描述 | 默认值 |
|------|------|--------|
| 轨道选择 | 启用/禁用MIDI轨道 | 全部启用 |
| 八度偏移 | 音高调整 | -4 |

#### 音频输入
| 参数 | 描述 | 默认值 |
|------|------|--------|
| 平滑度 | 节拍密度（-5到5） | 0 |
| 阈值 | 过滤弱节拍 | 0 |

#### 转换模式
| 参数 | 模式 | 描述 | 默认值 |
|------|------|------|--------|
| 基准BPM | angleData | 角度计算的基准BPM | 自动 |
| 夹角 | 拉链 | 瓷砖间的固定夹角 | 15° |

## 技术原理

### 核心原则

**时间公式**：`时间 = 旋转角度/180 × 60/BPM`

两种模式产生相同的时间：
- **angleData模式**：固定BPM → 动态角度 = 时间 × BPM × 180 / 60
- **拉链模式**：固定角度 → 动态BPM = 角度/180 × 60/时间

### 魔法数字

拉链模式中：
```
魔法数字 = 180 / 夹角
显示BPM = 实际BPM / 魔法数字
```

示例：15°夹角 → 魔法数字 = 12

### 节拍检测（音频）

1. **能量信号**：样本²
2. **高斯平滑**：FFT卷积
3. **峰值检测**：scipy.signal.find_peaks

### 角度验证

| 角度 | 行为 |
|------|------|
| ≤ 0° | 拒绝（无法移动） |
| 0° < θ < 180° | 正常处理 |
| = 180° | 生成直线谱面 |
| > 180° | 拒绝 |

## 输出文件

- angleData模式：`文件名_angle.adofai`
- 拉链模式：`文件名_zipper_XX.adofai`（XX为角度值）
- 全采音模式：`文件名_fullsample_XXXX.adofai`（XXXX为采样率）
- 大圈圈模式：`文件名_TrackN.adofai`（N为轨道索引，每个轨道一个文件）

## 版本历史

### v2.5.0
- 新增大圈圈模式 (Big Circle Mode)
- 每个MIDI轨道单独生成谱面文件
- 大圈圈模式支持禁用指定轨道
- 支持 PositionTrack 事件和增强的 Pause 事件

### v2.4.0
- 使用 miniaudio 替代 ffmpeg 进行音频解码
- 支持更多音频格式：MP3、FLAC、VORBIS
- 无需系统安装 ffmpeg，纯 Python pip 安装即可

### v2.3.0
- 新增音频文件输入支持
- 合并apofai节拍检测功能
- MIDI和音频均支持两种转换模式
- 所有模式生成相同的拍子时间

### v2.2.0
- 简化为两种转换模式
- 新增拉链夹角模式

### v2.1.0
- 模块化项目结构
- i18n国际化支持

### v2.0.0
- angleData模式
- Pause事件支持

### v1.0.0
- 基于Java版本重写

## 致谢

- 原版Java开发者：[Luxus io](https://github.com/Luxusio/ADOFAI-Midi-Converter)
- [pyadofai](https://github.com/TonyLimps/pyadofai) - angleData计算参考
- [apofai](https://github.com/sky-sama/apofai_main_console) - 音频节拍检测参考
- [pyminiaudio](https://github.com/irmen/pyminiaudio) - 音频解码库

## 许可证

开源项目。请参考原Java项目了解许可条款。
