# 贡献指南

有想法或修了个 bug？直接提 PR。

> [English version](CONTRIBUTING.md)

## 环境

```bash
git clone https://github.com/Atnagnohil/TerminalArt.git && cd TerminalArt
uv sync
```

## 流程

1. Fork → 开分支 → 改代码
2. `uv run python -m main` 确认 GUI 正常
3. 拿个视频文件跑一遍
4. 提 PR，说清楚改了啥、为什么

## 可以搞的方向

### 视频导出加速

现在是用 PIL + OpenCV 多线程渲染。可以更快：

- 帧直接管道写给 ffmpeg stdin，不走 cv2.VideoWriter
- 走硬件编码（NVENC / AMF / QSV）
- 编码前跳过几乎相同的连续帧
- Numba 加速 ANSI 解析循环

### 终端渲染更细

- 盲文字符（`⠁⠂⠄⡀`）一个格子塞 8 个点，比现在细 4 倍
- Sixel 或 Kitty 图形协议 — 直接画像素，不局限于字符网格
- Unicode 半宽字符做亚字符抗锯齿
- 彩色模式上 Atkinson 抖动

### 换个好点的 GUI

tkinter 能用但简陋。几个方向：

- **Textual** — 终端原生 TUI，快，全键盘操作
- **PySide6** — 正儿八经的桌面控件，GPU 画布能做实时预览
- **Web UI** — 本地起服务 + `xterm.js`，好看也好改样式

### 可以试的技术

| 层 | 现在 | 试试 |
|:---|:---|:---|
| 图像 | OpenCV | skimage, torchvision |
| 视频读 | cv2.VideoCapture | PyAV, decord |
| 音频 | pygame.mixer | miniaudio, sounddevice |
| 打包 | PyInstaller | Nuitka（编译型，启动更快） |
| 终端 | 裸 ANSI | rich, textual, kitty 协议 |

## 代码在哪

| 文件 | 干嘛的 |
|:---|:---|
| `src/main.py` | 入口，CLI 解析 |
| `src/core/char_mapper.py` | 像素→字符，所有模式和风格都在这里 |
| `src/core/media_decoder.py` | 视频/图片/GIF → numpy 数组 |
| `src/core/terminal_renderer.py` | 帧率控制，ANSI 输出，音频 |
| `src/core/file_saver.py` | 导出 MP4/TXT/HTML |
| `src/gui/main_window.py` | tkinter 窗口 |

## 代码风格

- 类型标注有用的地方加，没用就不加
- 4 空格缩进，行宽别超 100
- 注释解释**为什么**这么写，不是翻译代码
- 文件别太长，超 300 行考虑拆
- 热路径上能用 NumPy 向量化就别写 Python 循环

## 报告 bug

带上：系统 + 终端名、Python 版本、什么文件、预期效果 vs 实际效果。
