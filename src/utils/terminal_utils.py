"""终端尺寸获取、光标控制工具"""
import shutil
import sys


def get_terminal_size() -> tuple[int, int]:
    """返回 (columns, lines)，失败回退 (120, 40)"""
    try:
        size = shutil.get_terminal_size(fallback=(120, 40))
        return size.columns, size.lines
    except Exception:
        return 120, 40


def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def move_cursor_home():
    sys.stdout.write("\033[H")
    sys.stdout.flush()


def clear_screen():
    sys.stdout.write("\033[2J")
    sys.stdout.flush()


def reset_terminal():
    sys.stdout.write("\033[0m")
    sys.stdout.flush()
    show_cursor()
