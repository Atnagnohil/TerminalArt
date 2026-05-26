"""终端渲染器 —— ANSI 输出 + 帧率控制 + 音频同步"""
import sys
import time
import threading
import colorama
from utils.terminal_utils import (
    hide_cursor, show_cursor, move_cursor_home, clear_screen,
)


class TerminalRenderer:
    """将预渲染的字符串帧按帧率输出到终端，支持音频同步"""

    def __init__(self, fps: float = 30.0, audio_path: str | None = None):
        colorama.init()
        self.fps = fps
        self.audio_path = audio_path
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self._audio_started = False

    def render_frame(self, frame_str: str):
        """渲染单帧（覆盖上一帧）"""
        move_cursor_home()
        sys.stdout.write(frame_str)
        sys.stdout.flush()

    def render_loop(self, frames: list[str], loop: bool = True):
        """循环播放帧序列"""
        hide_cursor()
        self._stop_event.clear()
        self._paused.clear()

        frame_interval = 1.0 / self.fps if self.fps > 0 else 1.0 / 30.0

        first_loop = True
        while not self._stop_event.is_set():
            if first_loop:
                self._start_audio()
                first_loop = False
            elif loop:
                self._stop_audio()
                self._start_audio()

            play_start_time = time.perf_counter()
            paused_duration = 0.0
            consecutive_drops = 0

            i = 0
            num_frames = len(frames)
            while i < num_frames and not self._stop_event.is_set():
                if self._paused.is_set():
                    pause_start = time.perf_counter()
                    while self._paused.is_set() and not self._stop_event.is_set():
                        time.sleep(0.01)
                    paused_duration += time.perf_counter() - pause_start

                if self._stop_event.is_set():
                    break

                # 确定当前播放进度（秒）
                if self._audio_started:
                    try:
                        import pygame
                        audio_ms = pygame.mixer.music.get_pos()
                    except Exception:
                        audio_ms = -1
                    if audio_ms >= 0:
                        elapsed = audio_ms / 1000.0
                    else:
                        elapsed = time.perf_counter() - play_start_time - paused_duration
                else:
                    elapsed = time.perf_counter() - play_start_time - paused_duration

                target_frame = int(elapsed / frame_interval)

                # 主动跳帧以对齐音视频，并包含最大连续跳帧安全阀 (MAX_CONSECUTIVE_DROPS = 5)
                if target_frame > i:
                    if consecutive_drops < 5:
                        dropped_count = min(target_frame - i, 5 - consecutive_drops)
                        i += dropped_count
                        consecutive_drops += dropped_count
                        if i >= num_frames:
                            break
                    else:
                        # 触发安全阀，强制渲染，防止画面完全静止
                        consecutive_drops = 0
                else:
                    consecutive_drops = 0

                self.render_frame(frames[i])

                # 等待下一帧的渲染时间点
                i += 1
                next_frame_time = i * frame_interval

                if self._audio_started:
                    try:
                        import pygame
                        audio_ms = pygame.mixer.music.get_pos()
                    except Exception:
                        audio_ms = -1
                    curr_elapsed = audio_ms / 1000.0 if audio_ms >= 0 else (time.perf_counter() - play_start_time - paused_duration)
                else:
                    curr_elapsed = time.perf_counter() - play_start_time - paused_duration

                wait = next_frame_time - curr_elapsed
                if wait > 0:
                    time.sleep(wait)

            if not loop:
                break

        self._stop_audio()
        clear_screen()
        show_cursor()

    def _start_audio(self):
        if not self.audio_path:
            return
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            pygame.mixer.music.load(self.audio_path)
            pygame.mixer.music.play()
            self._audio_started = True
        except Exception:
            self._audio_started = False

    def _stop_audio(self):
        if self._audio_started:
            try:
                import pygame
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass
            self._audio_started = False

    def stop(self):
        self._stop_event.set()
        self._paused.clear()

    def pause(self):
        self._paused.set()
        if self._audio_started:
            try:
                import pygame
                pygame.mixer.music.pause()
            except Exception:
                pass

    def resume(self):
        self._paused.clear()
        if self._audio_started:
            try:
                import pygame
                pygame.mixer.music.unpause()
            except Exception:
                pass

    @property
    def is_playing(self) -> bool:
        return not self._stop_event.is_set()
