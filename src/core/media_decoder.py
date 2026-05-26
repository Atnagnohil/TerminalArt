"""媒体解码模块 —— 视频/图片 → numpy 帧序列"""
import cv2
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import os


class MediaDecoder:
    """解码视频/图片/GIF，返回原始帧序列"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = self.file_path.suffix.lower()
        self._type: str
        self._audio_path: str | None = None

        if ext in (".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"):
            self._type = "video"
            self._cap = cv2.VideoCapture(str(file_path))
            if not self._cap.isOpened():
                raise ValueError(f"无法打开视频: {file_path}")
        elif ext == ".gif":
            self._type = "gif"
            from PIL import Image
            self._gif = Image.open(str(file_path))
            self._gif_frames: list[np.ndarray] = []
            self._load_gif_frames()
            self._gif_idx = 0
        elif ext in (".jpg", ".jpeg", ".png", ".bmp"):
            self._type = "image"
            bgr = cv2.imread(str(file_path))
            if bgr is None:
                raise ValueError(f"无法读取图片: {file_path}")
            self._img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _load_gif_frames(self):
        try:
            while True:
                frame = self._gif.copy().convert("RGB")
                self._gif_frames.append(np.array(frame))
                self._gif.seek(self._gif.tell() + 1)
        except EOFError:
            pass
        self._gif.seek(0)

    @property
    def media_type(self) -> str:
        return self._type

    def get_fps(self) -> float:
        if self._type == "video":
            fps = self._cap.get(cv2.CAP_PROP_FPS)
            return fps if fps > 0 else 30.0
        elif self._type == "gif":
            return 10.0
        return 30.0

    def get_total_frames(self) -> int:
        if self._type == "video":
            return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        elif self._type == "gif":
            return len(self._gif_frames)
        return 1

    def read_frame(self) -> np.ndarray | None:
        """逐帧读取，返回 RGB numpy array，EOF 返回 None"""
        if self._type == "video":
            ret, frame = self._cap.read()
            if not ret:
                return None
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        elif self._type == "gif":
            if self._gif_idx >= len(self._gif_frames):
                return None
            frame = self._gif_frames[self._gif_idx]
            self._gif_idx += 1
            return frame.copy()
        else:
            if self._img is None:
                return None
            img = self._img
            self._img = None
            return img.copy()

    def read_all_frames(self) -> list[np.ndarray]:
        """预加载所有帧到内存"""
        frames = []
        if self._type == "video":
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            while True:
                ret, frame = self._cap.read()
                if not ret:
                    break
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        elif self._type == "gif":
            frames = [f.copy() for f in self._gif_frames]
        else:
            frames = [self._img.copy()]
        return frames

    def extract_audio(self) -> str | None:
        """提取视频音轨为临时 WAV 文件，返回路径；失败返回 None"""
        if self._type != "video":
            return None
        if self._audio_path:
            return self._audio_path

        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(self.file_path),
                 "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                 tmp.name],
                capture_output=True,
                timeout=30,
            )
            if os.path.getsize(tmp.name) > 0:
                self._audio_path = tmp.name
                return self._audio_path
            os.unlink(tmp.name)
            return None
        except Exception:
            return None

    def reset(self):
        """重置读取位置到开头"""
        if self._type == "video":
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        elif self._type == "gif":
            self._gif_idx = 0
        else:
            bgr = cv2.imread(str(self.file_path))
            self._img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def release(self):
        if self._type == "video":
            self._cap.release()
