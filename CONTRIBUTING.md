# Contributing

Got an idea or a fix? PRs welcome.

> [中文版](CONTRIBUTING_CN.md)

## Getting set up

```bash
git clone https://github.com/Atnagnohil/TerminalArt.git && cd TerminalArt
uv sync
```

## The usual flow

1. Fork → branch → make changes
2. `uv run python -m main` to check the GUI still works
3. Test with a real video file
4. Open a PR, tell us what and why

## Places to dig in

### Faster video export

The current approach is PIL + OpenCV, multi-threaded. Ways to make it faster:

- Pipe frames straight to ffmpeg stdin instead of going through cv2.VideoWriter
- GPU encode (NVENC / AMF / QSV) through ffmpeg
- Skip near-duplicate frames before encoding
- Numba-accelerate the ANSI parsing loop

### Crisper terminal rendering

- Braille chars (`⠁⠂⠄⡀`) pack 8 dots per cell, quadrupling detail
- Sixel or Kitty graphics protocol — actual pixels, no character grid
- Sub-character anti-aliasing with Unicode half-width glyphs
- Atkinson dithering across RGB for color modes

### A better GUI

tkinter works but it's showing its age. Possibilities:

- **Textual** — terminal-native TUI, fast, keyboard-driven
- **PySide6** — proper native widgets, GPU canvas for a live preview
- **Web UI** — local server + `xterm.js`, looks great, easy to theme

### Tech worth trying

| Layer | Now | Could be |
|:---|:---|:---|
| Image | OpenCV | skimage, torchvision |
| Video I/O | cv2.VideoCapture | PyAV, decord |
| Audio | pygame.mixer | miniaudio, sounddevice |
| Pack | PyInstaller | Nuitka (compiled, faster startup) |
| Terminal | raw ANSI | rich, textual, kitty protocol |

## Code map

| File | Does |
|:---|:---|
| `src/main.py` | Entry point, CLI parsing |
| `src/core/char_mapper.py` | Pixel-to-char, all modes and styles live here |
| `src/core/media_decoder.py` | Video/image/gif → numpy arrays |
| `src/core/terminal_renderer.py` | Frame timing, ANSI output, audio |
| `src/core/file_saver.py` | MP4/TXT/HTML export |
| `src/gui/main_window.py` | The tkinter window |

## Loose conventions

- Type hints where they help, skip where they don't
- 4 spaces, ~100 chars per line
- Comments explain *why*, code explains *what*
- Files stay under ~300 lines, split when they grow
- NumPy vector ops over Python loops in the hot path

## Filing a bug

Include: OS + terminal name, Python version, what file you tried, what you expected vs what happened.
