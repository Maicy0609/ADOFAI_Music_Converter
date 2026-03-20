# ADOFAI Music Converter

**[English Documentation](./README.md)**

将MIDI音乐文件转换为ADOFAI谱面文件的工具。

## 概述

本工具可将MIDI文件转换为《[冰与火之舞 (A Dance of Fire and Ice)](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/)》的可玩谱面文件。支持两种转换模式，以适应不同的使用场景和精度需求。

## 功能特点

- **双模式转换**：
  - **pathData模式 (RW模式)**：使用SetSpeed + Twirl事件控制节奏
  - **angleData模式**：纯角度控制，支持任意浮点数精度
- **多语言支持**：英文和简体中文
- **交互式CLI**：友好的命令行界面
- **自动BPM计算**：自动计算angleData模式的最优基准BPM

## 项目结构

```
ADOFAI_Music_Converter/
├── main.py                    # 主入口文件
├── lib/
│   └── midi/
│       ├── __init__.py        # 模块初始化
│       ├── common.py          # 共享数据结构和MIDI解析器
│       ├── pathD.py           # pathData模式实现
│       └── angleD.py          # angleData模式实现
├── i18n/
│   ├── i18n.py               # 国际化控制模块
│   ├── zh_CN.json            # 简体中文翻译
│   └── en_US.json            # 英文翻译
├── README.md                  # 英文文档
├── README_CN.md              # 中文文档（本文件）
└── requirements.txt          # Python依赖
```

## 安装依赖

```bash
pip install mido
```

## 使用方法

### 交互式命令行

```bash
python main.py
```

按照提示操作：
1. 选择语言（英文/中文）
2. 输入或拖入MIDI文件路径
3. 选择转换模式（1=pathData，2=angleData）
4. 选择要启用/禁用的轨道
5. 设置八度偏移（推荐：-4 到 -2）
6. angleData模式：设置基准BPM（留空自动计算）

### 输出文件

转换完成后，在MIDI文件同目录生成：
- pathData模式：`文件名_rw.adofai`
- angleData模式：`文件名_angle.adofai`

## 转换模式对比

| 特性 | pathData模式 | angleData模式 |
|------|-------------|---------------|
| 原理 | pathData + SetSpeed + Twirl | 纯angleData角度 |
| 兼容性 | 最佳 | 良好 |
| 精度 | 高 | 最高 |
| BPM变化 | 动态调整 | 固定基准BPM |
| 长延迟处理 | SetSpeed事件 | Pause事件 |

## 技术原理详解

### 魔法数字说明

本项目使用了一些重要的常量，以下是详细解释：

| 常量 | 值 | 说明 |
|------|-----|------|
| `12` | 12 | pathData模式下的BPM倍增因子。由于RW模式每拍实际旋转15°（180°/15°=12），音乐播放速度看起来是实际的12倍。公式：`显示BPM = 实际BPM / 12` |
| `15°` | 15 | pathData模式的有效旋转角度。R=0°, W=165°, Twirl使角度变为：180°-165°=15° |
| `180°` | 180 | ADOFAI中一拍的完整旋转角度 |
| `500000 μs` | 500000 | 默认MIDI速度（120 BPM = 每拍500000微秒） |

### pathData模式（RW模式）算法

pathData模式使用巧妙的技巧实现可变节奏：

1. **路径模式**：使用RWRW...模式，其中：
   - R = 0°（向右）
   - W = 165°（略小于180°）

2. **Twirl效果**：Twirl事件翻转旋转方向，使有效角度变为：
   - 无Twirl：180° - 0° = 180° 或 180° - 165° = 15°
   - 有Twirl：165°实际上变为15°（180° - 165° = 15°）

3. **BPM计算**：
   ```
   时间 = 15°/180° × 60/BPM 秒
   BPM = 60 × 1000000 / 微秒延迟 / 12
   ```

4. **为什么是12？**：由于每拍只旋转15°而不是180°，音乐播放速度是实际的12倍。我们除以12来补偿。

### angleData模式算法

angleData模式使用直接角度控制：

1. **角度表示**：每个瓷砖存储一个(0, 360]范围内的绝对角度

2. **旋转角度计算**：
   ```
   旋转角度 = (前一角度 + 180 - 当前角度) mod 360
   如果旋转角度 <= 0：
       旋转角度 += 360
   ```

3. **时间公式**：
   ```
   节拍数 = 旋转角度 / 180
   时间 = 节拍数 × 60 / BPM
   ```

4. **长延迟处理（>360°旋转）**：当所需旋转角度超过360°时，使用Pause事件：
   ```
   基础旋转角度 = 总旋转角度 % 360
   暂停节拍数 = (总旋转角度 - 基础旋转角度) / 180
   ```

5. **基准BPM选择**：使用所有pathData BPM值的中位数以保证稳定性。

### 核心类说明

| 类名 | 位置 | 用途 |
|------|------|------|
| `MidiParser` | `lib/midi/common.py` | 将MIDI文件解析为旋律数据 |
| `PathDataConverter` | `lib/midi/pathD.py` | 转换为pathData格式 |
| `AngleDataConverter` | `lib/midi/angleD.py` | 转换为angleData格式 |
| `MapData` | `lib/midi/common.py` | 表示ADOFAI谱面数据 |
| `TileData` | `lib/midi/common.py` | 表示单个瓷砖数据 |

## 命名规范

本项目严格遵循以下命名规范：

- **ADOFAI** - 必须大写（"A Dance of Fire and Ice"的缩写）
- **pathData** - 驼峰命名，首字母小写
- **angleData** - 驼峰命名，首字母小写

## 版本历史

### v2.1.0
- 模块化项目结构
- 国际化支持（i18n）
- 分离pathData和angleData实现

### v2.0.0
- 新增angleData模式
- 修复angleData时间计算问题
- 添加Pause事件支持长延迟
- 优化基准BPM选择算法

### v1.0.0
- 基于Java版本重写
- pathData模式支持

## 致谢

- 原版Java开发者：[Luxus io](https://github.com/Luxusio/ADOFAI-Midi-Converter)
- [pyadofai库](https://github.com/TonyLimps/pyadofai) - angleData计算参考

## 许可证

本项目为开源项目。请参考原Java项目了解许可条款。
