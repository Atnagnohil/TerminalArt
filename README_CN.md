<br>
<p align="center">
  <pre>
 █████╗ ███████╗ ██████╗██╗██╗    █████╗ ██████╗ ████████╗
██╔══██╗██╔════╝██╔════╝██║██║   ██╔══██╗██╔══██╗╚══██╔══╝
███████║███████╗██║     ██║██║   ███████║██████╔╝   ██║
██╔══██║╚════██║██║     ██║██║   ██╔══██║██╔══██╗   ██║
██║  ██║███████║╚██████╗██║██║   ██║  ██║██║  ██║   ██║
╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
  </pre>
</p>

<p align="center">
  <b>终端字符画播放器</b>
  <br>
  视频 → 字符画，在终端里实时播放。
  <br><br>
  <a href="README.md">English</a>
</p>

---

<br>

<p align="center">
  <img src="demo_C.gif" width="720" alt="Mode C half-block">
  <br><sub>方案 C — 半块高清</sub>
</p>

<p align="center">
  <img src="demo_A.gif" width="720" alt="Mode A ASCII">
  <br><sub>方案 A — 经典密度风格</sub>
</p>

<br>

### 干嘛的

给它视频或图片，它在终端里用字符画出来，还能动。

- **4 种渲染** — ASCII 灰度 · ANSI 真彩 · 半块高清 · 盲文点阵超分辨率
- **6 种字符风格** — 经典渐变、极简线条、数字矩阵、书法笔触、复古打印、点阵
- **点阵模式** — `*` 二值化阈值，方案 A/B 都有
- **盲文超分辨率** — 一个字符 8 个点，比单字符精细 4 倍
- **有序抖动** — Bayer 4×4 或 Floyd-Steinberg，半色调平滑过渡
- **独立终端** — 弹新窗口，自动适配视频比例
- **音频同步** — ffmpeg 提取音轨，循环时音频跟着走
- **导出 MP4** — H.264 编码，可调字符高度，多线程渲染

<br>

### 安装

```bash
git clone https://github.com/Atnagnohil/TerminalArt.git && cd TerminalArt
uv sync
```

Python 3.12+，ffmpeg 可选（导出带音频才需要）。

<br>

### 跑起来

```bash
uv run python -m main                        # GUI
uv run python -m main video.mp4              # 命令行直接播
uv run python -m main --console-play video.mp4 --mode C   # 新终端自动适配
```

<br>

### 四种方案

> **A · ASCII**
> 灰度映射到字符密度。6 种风格可选，GUI 下拉或 `--style`。

> **B · ANSI 彩色**
> 每个像素一个彩色 `█`。24 位色，最接近原画面。

> **C · 半块高清**
> `▀` 一个字符塞两个像素。纵向分辨率翻倍。好终端上最清晰的彩色方案。

> **D · 盲文点阵**
> `⠿` 每个字符编码 2×4 个点。点密度是单字符的 8 倍。可选有序抖动（Bayer 4×4，快）或 Floyd-Steinberg（更平滑，较慢）。

<br>

### 方案 A 字符风格

| 风格 | 字符集 | 感觉 |
|---:|:---|:---|
| `classic` | ` .:-=+*#%@` | 10 级渐变，细腻 |
| `minimal` | `./\|*` | 高对比，轮廓硬 |
| `matrix` | `01` | 赛博朋克代码雨 |
| `ink` | `丶丿丨乀` | 水墨笔触，粗糙有质感 |
| `vintage` | `@%#*+=-:. ` | 老式打印机味 |
| `dot` | `*` | 二值点阵，阈值控制疏密 |

<br>

### 点阵模式

方案 A 和 B 都有。设亮度阈值——高于阈值打 `*`，低于留空。阈值越低点越密。没有抖动，粗暴二分，反而好看。

<br>

### 命令行参数

```
--mode A/B/C/D     --style classic/minimal/matrix/ink/vintage/dot
--dot-mode 0/1     --threshold 0-255    --dither ordered/floyd-steinberg/none
--fps N            --loop 0/1           --cols N
```

<br>

### 导出视频

先在 GUI 播一次（后台自动缓存渲染帧），点**保存为视频**。字符高度可调（50–500，默认 200）。多线程渲染，H.264 编码，有 ffmpeg 自动合音轨。

<br>

### 画质说明

终端播放受限于 cmd 窗口大小，一屏塞不下太多字符。**方案 A** 受影响最大——在 ~100×30 的字符网格上，灰度渐变会显得颗粒感重。

想要真正细腻的效果，**保存成视频再看**。导出的 MP4 不受终端尺寸限制，字符独立编码，高度默认 200，清晰度远超终端实时播放。

渲染速度上：**方案 A 很快**（NumPy 向量化，逐帧几乎瞬间完成）。**方案 B 和 C 比较慢**——逐像素解析 ANSI 再渲染彩色字形，这是正常的。视频较长的话心里有个数。

### 碰到问题？

- **cmd.exe 乱码** → 换 Windows Terminal
- **画面跑出终端** → `--console-play` 自动适配，或把终端拉大
- **导出没声音** → 装 ffmpeg
- **点太稀** → 阈值调低，试试 80-100

<br>

### 代码结构

```
src/
├── main.py                    # 入口：gui / cli / 新终端
├── core/
│   ├── char_mapper.py         # 像素 → ansi（A/B/C + 风格）
│   ├── media_decoder.py       # 视频解码 → numpy
│   ├── terminal_renderer.py   # 帧率、输出、音频
│   └── file_saver.py          # mp4 / txt / html 导出
├── gui/
│   └── main_window.py         # tkinter 面板
└── utils/
    ├── ansi_to_html.py        # ansi → css
    └── terminal_utils.py      # 光标、尺寸、清屏
```

<br>

### 技术栈

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white">
  <img alt="NumPy" src="https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white">
  <img alt="Pillow" src="https://img.shields.io/badge/Pillow-181717?style=flat-square&logo=pillow&logoColor=white">
  <img alt="Pygame" src="https://img.shields.io/badge/Pygame-00AA00?style=flat-square&logo=pygame&logoColor=white">
  <img alt="tkinter" src="https://img.shields.io/badge/tkinter-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Colorama" src="https://img.shields.io/badge/Colorama-3776AB?style=flat-square&logo=python&logoColor=white">
</p>

<br>
