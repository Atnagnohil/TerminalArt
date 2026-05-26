"""TerminalArt —— 终端字符画播放器

启动方式:
  1. 双击 exe / python main.py → GUI 模式
  2. 拖拽文件到 exe / python main.py <file> → CLI 快速播放
  3. python main.py --console-play <file> [options] → 新终端窗口播放
"""
import sys
import os
import subprocess
from core.media_decoder import MediaDecoder
from core.char_mapper import create_mapper
from core.terminal_renderer import TerminalRenderer
from utils.terminal_utils import get_terminal_size, clear_screen


def quick_play(file_path: str, mode: str = "A", width: int = 120):
    """CLI 快速播放"""
    decoder = MediaDecoder(file_path)
    fps = decoder.get_fps()
    raw_frames = decoder.read_all_frames()
    if not raw_frames:
        decoder.release()
        print("错误: 无法从文件中解码任何帧")
        return
    audio_path = decoder.extract_audio()
    decoder.release()

    term_cols, term_lines = get_terminal_size()
    w = min(width, term_cols - 1)
    h = term_lines - 1

    mapper = create_mapper(mode, w, max_lines=h)
    frames = [mapper.frame_to_str(f) for f in raw_frames]

    print(f"TerminalArt - {file_path}")
    print(f"Frames: {len(frames)} | FPS: {fps:.1f} | Mode: {mode}")
    print(f"Audio: {'ON' if audio_path else 'OFF'}")
    input("按 Enter 开始播放...")

    renderer = TerminalRenderer(fps=fps, audio_path=audio_path)
    try:
        renderer.render_loop(frames, loop=True)
    except KeyboardInterrupt:
        renderer.stop()
    finally:
        print("\n播放结束")


def console_play(file_path: str, mode: str = "A", style: str = "classic",
                 dot_mode: bool = False, threshold: int = 128,
                 fps_limit: float = 30.0, loop: bool = True,
                 cols: int | None = None):
    """在新终端窗口中以最佳尺寸播放，保证不溢出"""
    decoder = MediaDecoder(file_path)
    fps = min(decoder.get_fps(), fps_limit)
    raw_frames = decoder.read_all_frames()
    if not raw_frames:
        decoder.release()
        print("错误: 无法从文件中解码任何帧")
        return
    audio_path = decoder.extract_audio()
    vh, vw = raw_frames[0].shape[:2]
    decoder.release()

    # ── 1. 确定视频播放尺寸 (保持宽高比) ──
    target_cols = cols if cols is not None else 120
    target_lines = max(1, target_cols * vh // vw // 2)

    # 限制高度，防止普通字号下超出物理屏幕底部
    if target_lines > 50:
        target_lines = 50
        target_cols = max(40, target_lines * 2 * vw // vh)

    # ── 2. 设置终端窗口大小 ──
    try:
        os.system(f"mode con cols={target_cols} lines={target_lines + 2}")
    except Exception:
        pass

    mapper = create_mapper(mode, target_cols, max_lines=target_lines,
                           style=style, dot_mode=dot_mode,
                           threshold=threshold)
    frames = [mapper.frame_to_str(f) for f in raw_frames]

    print(f"TerminalArt - {file_path}")
    print(f"Resolution: {target_cols}x{target_lines} | FPS: {fps:.1f} | Mode: {mode}")
    print(f"Audio: {'ON' if audio_path else 'OFF'}")
    input("按 Enter 开始播放...")

    # 清屏以擦除残留提示信息
    clear_screen()

    renderer = TerminalRenderer(fps=fps, audio_path=audio_path)
    try:
        renderer.render_loop(frames, loop=loop)
    except KeyboardInterrupt:
        renderer.stop()
    finally:
        print("\n播放结束")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="TerminalArt —— 终端字符画播放器 / Terminal ASCII Art Video Player"
    )
    parser.add_argument("file_path", nargs="?", help="要播放的多媒体文件路径 (视频/图片/GIF)")
    parser.add_argument("--console-play", action="store_true", help="在新终端窗口中以最佳尺寸播放")
    parser.add_argument("--mode", choices=["A", "B", "C"], default="A", help="字符画映射方案: A (ASCII黑白), B (ANSI彩色), C (半块高清)")
    parser.add_argument("--style", default="classic", help="方案 A 的字符风格")
    parser.add_argument("--dot-mode", type=int, choices=[0, 1], default=0, help="方案 B 的点阵模式 (0: 禁用, 1: 启用)")
    parser.add_argument("--threshold", type=int, default=128, help="点阵二值化阈值 (0-255)")
    parser.add_argument("--fps", type=float, default=30.0, dest="fps_limit", help="播放帧率上限")
    parser.add_argument("--loop", type=int, choices=[0, 1], default=1, help="是否循环播放 (0: 否, 1: 是)")
    parser.add_argument("--cols", type=int, help="终端播放的字符宽度")
    parser.add_argument("--gui", action="store_true", help="强制启动图形界面模式")

    args = parser.parse_args()

    if args.gui or (not args.file_path and not args.console_play):
        from gui.main_window import TerminalArtGUI
        app = TerminalArtGUI()
        app.run()
    elif args.console_play:
        if not args.file_path:
            parser.error("使用 --console-play 时必须指定文件路径 (file_path)")
        console_play(
            file_path=args.file_path,
            mode=args.mode,
            style=args.style,
            dot_mode=(args.dot_mode == 1),
            threshold=args.threshold,
            fps_limit=args.fps_limit,
            loop=(args.loop == 1),
            cols=args.cols
        )
    else:
        quick_play(args.file_path, mode=args.mode)


if __name__ == "__main__":
    main()
