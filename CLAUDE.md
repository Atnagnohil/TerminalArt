# TerminalArt —— 终端字符画播放器

## 完整项目计划书 v1.0

---

## 目录

1. [项目概述](#1-项目概述)
2. [功能需求](#2-功能需求)
3. [技术栈](#3-技术栈)
4. [系统架构](#4-系统架构)
5. [模块设计](#5-模块设计)
6. [字符映射方案详解](#6-字符映射方案详解)
7. [GUI 设计规范](#7-gui-设计规范)
8. [目录结构](#8-目录结构)
9. [开发计划](#9-开发计划)
10. [打包与发布](#10-打包与发布)
11. [技术难点与解决方案](#11-技术难点与解决方案)
12. [未来扩展](#12-未来扩展)

---

## 1. 项目概述

### 1.1 项目名称

**TerminalArt** —— 终端字符画播放器

### 1.2 项目目标

将视频/图片转换为字符画，在系统终端中实时播放，并支持将转换结果保存为文件。通过 GUI 操作界面提供文件导入、参数配置、播放控制等功能，最终打包为独立 `.exe` 可执行文件，无需安装任何依赖。

### 1.3 核心特性

| 特性             | 描述                                             |
| ---------------- | ------------------------------------------------ |
| 多媒体支持       | 视频文件 + 图片文件（动态高帧率刷新）            |
| 三种字符映射方案 | A（ASCII黑白）/ B（ANSI彩色）/ C（半块高清彩色） |
| 终端实时播放     | ANSI 转义码渲染，无闪烁，帧率同步                |
| 结果保存         | 将字符画输出保存为 `.txt` / `.html` 文件     |
| GUI 控制面板     | 文件选择、方案切换、播放控制一体化               |
| 一键打包         | PyInstaller 打包为单个 `.exe`，免安装          |

---

## 2. 功能需求

### 2.1 输入支持

#### 视频

- 支持格式：`.mp4` `.avi` `.mov` `.mkv` `.flv` `.wmv`
- 自动读取原始帧率（FPS），按原速播放
- 支持循环播放

#### 图片（动态高帧率刷新）

- 支持格式：`.jpg` `.jpeg` `.png` `.bmp` `.gif`（gif 逐帧播放）
- 静态图片以单帧渲染
- 图片序列可按自定义帧率刷新（高帧率，人眼无法察觉切换）

### 2.2 输出功能

#### 终端播放

- 打开独立终端窗口，实时渲染字符画
- 自动适配终端窗口尺寸（`os.get_terminal_size()`）
- 帧率精准同步（`time.perf_counter()` 精确计时）
- 无闪烁渲染（ANSI 光标归位，非 `clear` 命令）

#### 文件保存

- `.txt` 格式：纯字符（方案A适用）
- `.html` 格式：带 ANSI 颜色的彩色字符画（方案B/C适用，浏览器可直接打开）
- 视频保存：逐帧导出 → 打包为 `.zip`

### 2.3 字符映射方案

| 方案        | 名称            | 色彩 | 画质     | 说明                         |
| ----------- | --------------- | ---- | -------- | ---------------------------- |
| **A** | ASCII 黑白      | 无   | ★★☆   | 经典风格，用字符密度模拟亮度 |
| **B** | ANSI True Color | 全彩 | ★★★   | 用彩色"█"还原原始色彩       |
| **C** | 半块高清彩色    | 全彩 | ★★★★ | 纵向分辨率翻倍，画质最高     |

### 2.4 GUI 功能

- **文件选择**：系统原生文件选择框，支持拖拽
- **方案选择**：A/B/C 三选一，实时切换
- **分辨率控制**：字符宽度滑块（40～200）
- **播放控制**：播放 / 暂停 / 停止 / 循环开关
- **帧率显示**：实时 FPS 计数器
- **保存按钮**：选择输出路径，保存当前/全部帧

---

## 3. 技术栈

### 3.1 运行时依赖

```
Python 3.10+
│
├── opencv-python       # 视频/图片解帧，格式支持最广
├── numpy               # 像素矩阵向量化运算（性能核心）
├── Pillow              # 辅助图片格式支持（GIF 逐帧）
├── colorama            # Windows 终端 ANSI 兼容层
├── pygame              # 音频同步播放（可选模块）
└── tkinter             # GUI 界面（Python 内置，无额外体积）
```

### 3.2 开发/打包工具

```
PyInstaller 6.x         # 打包 .exe
pyinstaller-hooks-contrib  # 第三方库钩子（处理 cv2/numpy）
```

### 3.3 各库版本锁定（requirements.txt）

```txt
opencv-python==4.9.0.80
numpy==1.26.4
Pillow==10.3.0
colorama==0.4.6
pygame==2.5.2
pyinstaller==6.6.0
```

---

## 4. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      TerminalArt                            │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │   GUI 层      │    │           核心引擎               │  │
│  │  (tkinter)   │───▶│                                  │  │
│  │              │    │  ┌──────────┐  ┌──────────────┐  │  │
│  │  • 文件选择   │    │  │ 媒体解码  │  │  字符映射器  │  │  │
│  │  • 方案切换   │    │  │ (cv2)    │─▶│  A / B / C  │  │  │
│  │  • 播放控制   │    │  └──────────┘  └──────┬───────┘  │  │
│  │  • 参数调节   │    │                        │          │  │
│  └──────────────┘    │  ┌─────────────────────▼────────┐ │  │
│                      │  │       帧缓冲区 (内存预渲染)    │ │  │
│                      │  └─────────────────────┬────────┘ │  │
│                      │                         │          │  │
│                      │  ┌──────────────────────▼───────┐ │  │
│                      │  │         输出路由器             │ │  │
│                      │  │   ┌──────────┐ ┌──────────┐  │ │  │
│                      │  │   │ 终端渲染  │ │ 文件保存  │  │ │  │
│                      │  │   │ (stdout) │ │(.txt/.html│  │ │  │
│                      │  │   └──────────┘ └──────────┘  │ │  │
│                      │  └──────────────────────────────┘ │  │
│                      └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 数据流

```
输入文件
  │
  ▼
MediaDecoder（cv2）
  │ 原始帧 BGR numpy array (H×W×3)
  ▼
FrameProcessor
  │ resize → 适配终端尺寸
  │ pixel → char（根据所选方案 A/B/C）
  ▼
FrameBuffer（list of strings）
  │
  ├──▶ TerminalRenderer（ANSI 输出到 stdout）
  │         帧率控制 → perf_counter 精准计时
  │
  └──▶ FileSaver（.txt / .html 输出）
```

---

## 5. 模块设计

### 5.1 `media_decoder.py` —— 媒体解码模块

```python
class MediaDecoder:
    """
    职责：解码视频/图片，返回原始帧序列
    """
    def __init__(self, file_path: str)
    def get_fps(self) -> float
    def get_total_frames(self) -> int
    def read_frame(self) -> np.ndarray | None   # 逐帧读取
    def read_all_frames(self) -> list[np.ndarray]  # 全部预加载
    def release(self)
```

支持类型检测：自动判断 video / static_image / gif

---

### 5.2 `char_mapper.py` —— 字符映射核心

```python
class CharMapper:
    """
    职责：将 numpy 图像帧转换为字符串（ANSI 或纯文本）
    """
    def __init__(self, mode: str, width: int = 120)
    def frame_to_str(self, frame: np.ndarray) -> str

# 三个子类
class ModeA_ASCII(CharMapper):   # 黑白 ASCII
class ModeB_Color(CharMapper):   # ANSI True Color "█"
class ModeC_HalfBlock(CharMapper):  # 半块 "▀▄" 高分辨率
```

---

### 5.3 `terminal_renderer.py` —— 终端渲染器

```python
class TerminalRenderer:
    """
    职责：将字符串帧渲染到终端，控制帧率
    """
    def __init__(self, fps: float)
    def render(self, frame_str: str)          # 渲染单帧
    def render_loop(self, frames: list[str])  # 循环播放
    def stop(self)
    def _move_cursor_home(self)   # "\033[H" 光标归位（无闪烁）
    def _hide_cursor(self)        # "\033[?25l"
    def _show_cursor(self)        # "\033[?25h"
```

---

### 5.4 `file_saver.py` —— 文件保存模块

```python
class FileSaver:
    """
    职责：将字符帧保存为 txt 或 html 文件
    """
    def save_txt(self, frames: list[str], path: str)
    def save_html(self, frames: list[str], path: str)
    # html 输出：将 ANSI 转义码转换为 CSS span 标签
    # 支持浏览器直接查看彩色字符画
```

---

### 5.5 `gui.py` —— 图形界面

```python
class TerminalArtGUI:
    """
    职责：tkinter 主窗口，串联所有模块
    """
    def __init__(self)
    def _build_ui(self)
    def _on_file_select(self)      # 打开文件对话框
    def _on_mode_change(self)      # A/B/C 方案切换
    def _on_play(self)             # 启动终端播放（子线程）
    def _on_stop(self)
    def _on_save(self)             # 保存输出文件
    def _update_preview(self)      # GUI 内小预览（可选）
```

---

### 5.6 `main.py` —— 程序入口

```python
"""
支持两种启动方式：
  1. 双击 exe → 弹出 GUI
  2. 拖拽文件到 exe → 直接播放（sys.argv[1]）
"""
import sys
from gui import TerminalArtGUI
from media_decoder import MediaDecoder
from terminal_renderer import TerminalRenderer

if len(sys.argv) > 1:
    # 拖拽模式：直接用默认配置播放
    quick_play(sys.argv[1])
else:
    # GUI 模式
    app = TerminalArtGUI()
    app.run()
```

---

## 6. 字符映射方案详解

### 方案 A —— ASCII 黑白

**原理**：计算每个像素的灰度值，映射到由暗到亮的字符序列。

```python
CHARS_A = " .:-=+*#%@█"
# 灰度 0～255 均匀映射到字符索引

def pixel_to_char_A(r, g, b) -> str:
    gray = 0.299*r + 0.587*g + 0.114*b   # 加权灰度公式
    idx = int(gray / 255 * (len(CHARS_A) - 1))
    return CHARS_A[idx]
```

**特点**：经典风格，兼容所有终端，文件体积小，可保存纯 `.txt`

---

### 方案 B —— ANSI True Color 彩色

**原理**：每个字符固定为 "█"（全填充块），用 ANSI 前景色还原像素 RGB。

```python
def pixel_to_char_B(r, g, b) -> str:
    return f"\033[38;2;{r};{g};{b}m█\033[0m"
```

**终端要求**：需支持 True Color（Windows Terminal / iTerm2 / 主流 Linux 终端均支持）

**特点**：颜色接近原图，实现简单，字体等宽即可正常显示

---

### 方案 C —— 半块高清彩色（推荐★）

**原理**：每个字符对应上下两个像素。"▀" 的前景色 = 上像素 RGB，背景色 = 下像素 RGB。纵向分辨率相比方案 B **翻倍**。

```python
def pixel_pair_to_char_C(r1,g1,b1, r2,g2,b2) -> str:
    # "▀" 上半块：前景=上像素，背景=下像素
    return (f"\033[38;2;{r1};{g1};{b1}m"   # 前景色
            f"\033[48;2;{r2};{g2};{b2}m"   # 背景色
            f"▀\033[0m")

# 处理时：每次取两行像素，合并为一行字符
for y in range(0, height, 2):
    row_top = frame[y]
    row_bot = frame[y+1] if y+1 < height else frame[y]
    # 逐列配对合成
```

**特点**：画质最高，同等终端尺寸下清晰度约为方案B的2倍，推荐作为默认方案。

---

### 性能对比

| 方案 | 渲染速度   | 内存占用 | 终端兼容性 | 视觉效果 |
| ---- | ---------- | -------- | ---------- | -------- |
| A    | ★★★★★ | 最低     | 全部终端   | ★★☆   |
| B    | ★★★★☆ | 中等     | True Color | ★★★   |
| C    | ★★★☆☆ | 较高     | True Color | ★★★★ |

---

## 7. GUI 设计规范

### 7.1 主窗口布局

```
┌─────────────────────────────────────────────┐
│  TerminalArt  v1.0                    [─][□][×]│
├─────────────────────────────────────────────┤
│                                             │
│  ┌─ 文件 ──────────────────────────────┐   │
│  │  [📁 选择文件]  path/to/file.mp4    │   │
│  │  或将文件拖拽到此处                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─ 字符方案 ──────────────────────────┐   │
│  │  (●) A - ASCII 黑白                 │   │
│  │  ( ) B - ANSI 彩色                  │   │
│  │  ( ) C - 半块高清（推荐）            │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─ 参数 ───────────────────────────────┐  │
│  │  字符宽度  [━━━━●━━━━━━━━━]  120     │  │
│  │  帧率上限  [━━━━━━━━●━━━━━]  30 fps  │  │
│  │  [ ] 循环播放    [ ] 同步音频        │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌─ 控制 ──────────────────────────────┐   │
│  │  [▶ 在终端播放]  [⏹ 停止]          │   │
│  │  [💾 保存输出]   格式: (●).txt ( ).html│  │
│  └─────────────────────────────────────┘   │
│                                             │
│  状态：就绪  |  FPS: --  |  帧: --/--      │
└─────────────────────────────────────────────┘
```

### 7.2 交互行为

| 操作             | 行为                                 |
| ---------------- | ------------------------------------ |
| 点击"选择文件"   | 弹出系统文件选择框，过滤支持格式     |
| 拖拽文件到窗口   | 自动识别路径，填入输入框             |
| 点击"在终端播放" | 新开终端窗口，子线程渲染，GUI 不阻塞 |
| 切换方案 A/B/C   | 立即更新，下次播放生效               |
| 点击"保存输出"   | 弹出保存路径框，后台渲染保存         |

---

## 8. 目录结构

```
TerminalArt/
│
├── main.py                  # 程序入口（GUI / 拖拽双模式）
│
├── core/
│   ├── __init__.py
│   ├── media_decoder.py     # 媒体解码（cv2）
│   ├── char_mapper.py       # 字符映射 A/B/C
│   ├── terminal_renderer.py # 终端渲染 + 帧率控制
│   └── file_saver.py        # 保存 txt/html
│
├── gui/
│   ├── __init__.py
│   └── main_window.py       # tkinter 主窗口
│
├── utils/
│   ├── __init__.py
│   ├── ansi_to_html.py      # ANSI 转 HTML CSS
│   └── terminal_utils.py    # 终端尺寸、光标控制工具
│
├── assets/
│   └── icon.ico             # 应用图标（打包用）
│
├── requirements.txt         # 依赖锁定
├── build.bat                # 一键打包脚本（Windows）
└── README.md
```

---

## 9. 开发计划

### 阶段一：核心引擎（第 1～2 天）

**目标**：命令行跑通基础流程

- [X] 搭建项目结构
- [ ] `media_decoder.py`：视频/图片读帧
- [ ] `char_mapper.py`：方案 A（ASCII 黑白）实现
- [ ] `terminal_renderer.py`：终端渲染 + 帧率控制
- [ ] 命令行测试：`python main.py test.mp4`

**验收标准**：终端能流畅播放视频，帧率稳定 ≥ 15fps

---

### 阶段二：彩色方案（第 3 天）

**目标**：补全 B/C 方案

- [ ] `char_mapper.py`：方案 B（ANSI True Color）
- [ ] `char_mapper.py`：方案 C（半块 ▀▄ 高分辨率）
- [ ] 性能测试与 numpy 向量化优化
- [ ] Windows colorama 兼容性测试

**验收标准**：三种方案均可正常渲染，方案C帧率 ≥ 20fps

---

### 阶段三：文件保存（第 4 天）

**目标**：保存字符画到文件

- [ ] `file_saver.py`：纯文本 `.txt` 保存
- [ ] `file_saver.py`：彩色 `.html` 保存（ANSI → CSS）
- [ ] 视频多帧打包为 `.zip`

**验收标准**：保存的 html 文件在浏览器中正确显示彩色字符画

---

### 阶段四：GUI 界面（第 5～6 天）

**目标**：完整 GUI 控制面板

- [ ] `main_window.py`：基础布局搭建
- [ ] 文件选择框 + 拖拽支持
- [ ] A/B/C 方案单选按钮
- [ ] 字符宽度 + 帧率滑块
- [ ] 播放/停止/保存按钮联通核心引擎
- [ ] 状态栏（实时 FPS 显示）

**验收标准**：GUI 完整可用，播放不阻塞界面

---

### 阶段五：打包与测试（第 7 天）

**目标**：生成可分发的 exe

- [ ] 编写 `build.bat` 打包脚本
- [ ] PyInstaller spec 文件配置（处理 cv2 资源）
- [ ] 在无 Python 环境的 Windows 上测试 exe
- [ ] 修复 exe 相关路径问题（`sys._MEIPASS`）

**验收标准**：exe 单文件，双击运行，无需安装任何依赖

---

### 阶段六：优化与收尾（第 8 天）

- [ ] 音频同步（pygame，可选）
- [ ] 性能剖析，瓶颈优化
- [ ] README 文档
- [ ] 打包图标设计

---

## 10. 打包与发布

### 10.1 打包命令

```bash
# build.bat 内容

pyinstaller ^
  --onefile ^
  --console ^
  --icon=assets/icon.ico ^
  --name=TerminalArt ^
  --add-data "assets;assets" ^
  --hidden-import=cv2 ^
  --hidden-import=numpy ^
  --hidden-import=PIL ^
  --hidden-import=colorama ^
  --hidden-import=pygame ^
  main.py
```

### 10.2 exe 路径适配

```python
# 处理 PyInstaller 打包后的资源路径
import sys, os

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS   # PyInstaller 解压临时目录
    return os.path.dirname(__file__)

ASSETS_DIR = os.path.join(get_base_path(), 'assets')
```

### 10.3 输出产物

```
dist/
└── TerminalArt.exe    # 单文件，约 50～80 MB（含 cv2/numpy）
```

---

## 11. 技术难点与解决方案

### 难点一：Windows 终端 ANSI 兼容

**问题**：老版 Windows cmd 不支持 ANSI 转义码，颜色代码会原样打印。

**解决**：

```python
import colorama
colorama.init()  # 自动处理 Windows ANSI 兼容，Mac/Linux 无副作用
```

---

### 难点二：GUI 与终端播放不阻塞

**问题**：tkinter 是单线程的，终端播放会阻塞 GUI。

**解决**：

```python
import threading

def on_play():
    t = threading.Thread(target=render_loop, daemon=True)
    t.start()
```

---

### 难点三：高帧率图片刷新（视觉欺骗）

**问题**：图片需要以高帧率在终端刷新（≥60fps），让人眼无法捕捉切换。

**解决**：

```python
# 预渲染所有帧到内存，播放时只做 write()，不做计算
frames = [mapper.frame_to_str(f) for f in raw_frames]

# 精准计时，避免 sleep 精度误差
target_time = time.perf_counter()
for frame_str in frames:
    sys.stdout.write("\033[H" + frame_str)
    sys.stdout.flush()
    target_time += 1.0 / fps
    wait = target_time - time.perf_counter()
    if wait > 0:
        time.sleep(wait)
```

---

### 难点四：PyInstaller 打包 cv2 资源

**问题**：cv2 包含原生动态库，PyInstaller 有时无法自动检测。

**解决**：

```bash
# 在 spec 文件中手动添加 cv2 数据文件
datas=[
    (cv2.__file__, 'cv2'),
]
```

---

### 难点五：终端尺寸自适应

**问题**：不同用户终端大小不同，字符宽度需自适应。

**解决**：

```python
import shutil

def get_terminal_size():
    size = shutil.get_terminal_size(fallback=(120, 40))
    # 方案C纵向分辨率翻倍，height 需×2
    return size.columns, size.lines * 2
```

---

## 12. 未来扩展

| 功能                 | 优先级 | 说明                       |
| -------------------- | ------ | -------------------------- |
| 音频同步             | 高     | pygame.mixer 与视频帧对齐  |
| 实时摄像头输入       | 中     | cv2.VideoCapture(0)        |
| 网络直播流           | 低     | 支持 rtmp/http 视频流 URL  |
| GPU 加速             | 低     | CUDA numpy 加速像素映射    |
| 导出为 ANSI 艺术格式 | 中     | 标准 .ans 文件格式         |
| 方案 D：彩色 ASCII   | 中     | 方案A字符 + 方案B颜色结合  |
| Web 版               | 低     | 用 xterm.js 在浏览器中运行 |

---

## 附录：关键 ANSI 转义码参考

```
\033[H          光标移到左上角（帧刷新核心）
\033[2J         清屏
\033[?25l       隐藏光标
\033[?25h       显示光标
\033[38;2;R;G;Bm  设置前景色（True Color）
\033[48;2;R;G;Bm  设置背景色（True Color）
\033[0m         重置所有颜色/样式
```

---

*TerminalArt Project Plan v1.0 — 准备开干 🚀*
