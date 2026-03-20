# ADOFAI Music Converter

**[English Documentation](./README.md)**

将MIDI音乐文件转换为ADOFAI谱面文件的工具。

## 概述

本工具可将MIDI文件转换为《[冰与火之舞 (A Dance of Fire and Ice)](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/)》的谱面文件。支持三种转换模式。

## 功能特点

- **三种转换模式**：
  - **pathData模式 (RW模式)**：使用SetSpeed + Twirl事件，固定15°夹角
  - **angleData模式**：纯角度控制，固定基准BPM，支持任意浮点数精度
  - **自定义夹角模式**：使用angleData + SetSpeed，可自定义夹角角度
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
│       ├── angleD_custom.py   # 自定义夹角模式实现
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
3. 选择转换模式（1=pathData，2=angleData，3=自定义夹角）
4. 选择要启用/禁用的轨道
5. 设置八度偏移（推荐：-4 到 -2）
6. 根据模式设置额外参数（BPM/夹角）

### 输出文件

转换完成后，在MIDI文件同目录生成：
- pathData模式：`文件名_rw.adofai`
- angleData模式：`文件名_angle.adofai`
- 自定义夹角模式：`文件名_custom_角度.adofai`

## 转换模式对比

| 特性 | pathData模式 | angleData模式 | 自定义夹角模式 |
|------|-------------|---------------|----------------|
| 原理 | pathData + SetSpeed + Twirl | 纯angleData | angleData + SetSpeed |
| 夹角 | 固定15° | 动态计算 | 用户自定义 |
| BPM | 动态调整 | 固定基准 | 动态调整 |
| 精度 | 高 | 最高 | 高 |
| 长延迟 | SetSpeed | Pause | Pause |

## 技术原理详解

### 魔法数字说明

本项目使用了一些重要的常量，以下是详细解释：

| 常量 | 值 | 说明 |
|------|-----|------|
| `魔法数字` | 180/夹角 | BPM倍增因子。夹角越小，魔法数字越大。公式：`显示BPM = 实际BPM / 魔法数字` |
| `15°` | 15 | pathData模式的默认夹角。R=0°, W=165°, Twirl使角度变为：180°-165°=15° |
| `180°` | 180 | ADOFAI中一拍的完整旋转角度。夹角180°时为直线 |
| `500000 μs` | 500000 | 默认MIDI速度（120 BPM = 每拍500000微秒） |

### 自定义夹角模式算法

自定义夹角模式允许用户设置瓷砖之间的固定夹角：

1. **夹角定义**：用户输入夹角θ（0° < θ ≤ 180°）

2. **角度序列计算**：
   ```
   angle[0] = 0°
   angle[i] = (angle[i-1] + 180 - θ) mod 360
   ```

3. **魔法数字计算**：
   ```
   魔法数字 = 180 / θ
   ```

4. **BPM计算**：
   ```
   时间 = θ/180 × 60/BPM 秒
   BPM = 60 × 1000000 / 微秒延迟 / 魔法数字
   ```

5. **特殊处理**：
   - 夹角 = 0°：拒绝（不合法，无法移动）
   - 夹角 = 180°：生成直线谱面

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

4. **长延迟处理（>360°旋转）**：当所需旋转角度超过360°时，使用Pause事件

### 核心类说明

| 类名 | 位置 | 用途 |
|------|------|------|
| `MidiParser` | `lib/midi/common.py` | 将MIDI文件解析为旋律数据 |
| `AngleCustomConverter` | `lib/midi/angleD_custom.py` | 自定义夹角模式转换器 |
| `AngleDataConverter` | `lib/midi/angleD.py` | angleData模式转换器 |
| `MapData` | `lib/midi/common.py` | 表示ADOFAI谱面数据 |
| `TileData` | `lib/midi/common.py` | 表示单个瓷砖数据 |

## 命名规范

本项目严格遵循以下命名规范：

- **ADOFAI** - 必须大写（"A Dance of Fire and Ice"的缩写）
- **pathData** - 驼峰命名，首字母小写
- **angleData** - 驼峰命名，首字母小写

## 版本历史

### v2.2.0
- 新增自定义夹角模式
- 夹角验证：拒绝0°，特殊处理180°
- 重命名pathD.py为angleD_custom.py
- 魔法数字动态计算

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
