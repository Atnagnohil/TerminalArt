"""字符映射核心 —— 像素帧 → ANSI/纯文本字符串"""
import cv2
import numpy as np

# ── 方案 A 字符集注册表 ──────────────────────────
CHAR_SETS = {
    "classic":  {"name": "经典密度风", "chars": " .:-=+*#%@"},
    "minimal":  {"name": "极简线条风", "chars": "./\\|*"},
    "matrix":   {"name": "数字矩阵风", "chars": "01"},
    "ink":      {"name": "书法笔触风", "chars": "丶丿丨乀"},
    "vintage":  {"name": "复古打印风",  "chars": "@%#*+=-:. "},
    "dot":      {"name": "点阵风格",    "chars": " *"},
}

# Bayer 4×4 有序抖动矩阵（0~15，归一化到 0~255）
BAYER_4x4 = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5]
], dtype=np.float32) * (255.0 / 16.0)


class CharMapper:
    """字符映射基类"""

    def __init__(self, width: int = 120, max_lines: int = 0):
        self.width = width
        self.max_lines = max_lines  # 0 表示不限制

    def _fit_size(self, frame_h: int, frame_w: int) -> tuple[int, int]:
        """根据终端约束计算等比缩放后的 (char_w, output_lines)"""
        w = self.width
        if self.max_lines <= 0:
            lines = max(1, w * frame_h // frame_w // 2)
            return w, lines

        # output_lines = w * frame_h / frame_w / 2
        # 由 max_lines 反算最大宽度: w <= max_lines * 2 * frame_w / frame_h
        w_from_h = self.max_lines * 2 * frame_w // frame_h
        w = min(w, w_from_h)
        w = max(1, w)
        lines = max(1, w * frame_h // frame_w // 2)
        return w, lines

    def frame_to_str(self, frame: np.ndarray) -> str:
        """将 RGB numpy 帧 (H×W×3) 转换为字符串"""
        raise NotImplementedError


class ModeA_ASCII(CharMapper):
    """方案 A: 灰度 → 字符密度，支持六种字符风格"""

    def __init__(self, width: int = 120, max_lines: int = 0,
                 style: str = "classic", threshold: int = 128):
        super().__init__(width, max_lines)
        if style not in CHAR_SETS:
            raise ValueError(f"未知风格: {style}，可选: {list(CHAR_SETS.keys())}")
        self.style = style
        self.threshold = threshold
        # 点阵风格加倍宽度，让点更密集
        if style == "dot":
            self.width = width * 2
        chars = CHAR_SETS[style]["chars"]
        self._char_array = np.array(list(chars))

    @property
    def style_name(self) -> str:
        return CHAR_SETS[self.style]["name"]

    @staticmethod
    def available_styles() -> list[dict]:
        return [{"key": k, "name": v["name"], "chars": v["chars"]}
                for k, v in CHAR_SETS.items()]

    def frame_to_str(self, frame: np.ndarray) -> str:
        fh, fw = frame.shape[:2]
        char_w, char_h = self._fit_size(fh, fw)
        small = cv2.resize(frame, (char_w, char_h), interpolation=cv2.INTER_AREA)

        gray = (small[:, :, 0].astype(np.float64) * 0.299 +
                small[:, :, 1].astype(np.float64) * 0.587 +
                small[:, :, 2].astype(np.float64) * 0.114)

        if self.style == "dot":
            mask = gray > self.threshold
            ch = self._char_array[1]
            sp = self._char_array[0]
            lines = ["".join(ch if m else sp for m in row) for row in mask]
        else:
            n_chars = len(self._char_array)
            # round 避免少字符集（如 01）全部映射到同一个字符
            indices = np.round(gray / 255.0 * (n_chars - 1)).astype(int)
            indices = np.clip(indices, 0, n_chars - 1)
            lines = ["".join(self._char_array[i] for i in row)
                     for row in indices]
        return "\n".join(lines)


class ModeB_Color(CharMapper):
    """方案 B: 每个像素 → 彩色 █/. (ANSI True Color 前景)"""

    def __init__(self, width: int = 120, max_lines: int = 0,
                 dot_mode: bool = False, threshold: int = 128):
        super().__init__(width, max_lines)
        self.dot_mode = dot_mode
        self.threshold = threshold
        if dot_mode:
            self.width = width * 2

    def frame_to_str(self, frame: np.ndarray) -> str:
        fh, fw = frame.shape[:2]
        char_w, char_h = self._fit_size(fh, fw)
        small = cv2.resize(frame, (char_w, char_h), interpolation=cv2.INTER_AREA)

        if self.dot_mode:
            gray = (small[:, :, 0].astype(np.float64) * 0.299 +
                    small[:, :, 1].astype(np.float64) * 0.587 +
                    small[:, :, 2].astype(np.float64) * 0.114)
            lines = []
            for y, row in enumerate(small):
                parts = []
                for x in range(char_w):
                    if gray[y, x] > self.threshold:
                        r, g, b = int(row[x][0]), int(row[x][1]), int(row[x][2])
                        parts.append(f"\033[38;2;{r};{g};{b}m*")
                    else:
                        parts.append(" ")
                parts.append("\033[0m")
                lines.append("".join(parts))
            return "\n".join(lines)
        else:
            lines = []
            for row in small:
                parts = []
                for r, g, b in row:
                    r, g, b = int(r), int(g), int(b)
                    parts.append(f"\033[38;2;{r};{g};{b}m█")
                parts.append("\033[0m")
                lines.append("".join(parts))
            return "\n".join(lines)


class ModeC_HalfBlock(CharMapper):
    """方案 C: 半块 ▀ (前景=上像素, 背景=下像素)，纵向分辨率翻倍"""

    def frame_to_str(self, frame: np.ndarray) -> str:
        fh, fw = frame.shape[:2]
        char_w, out_lines = self._fit_size(fh, fw)
        pixel_h = max(2, out_lines * 2)  # C 每输出行处理 2 像素行
        small = cv2.resize(frame, (char_w, pixel_h), interpolation=cv2.INTER_AREA)

        lines = []
        for y in range(0, pixel_h - 1, 2):
            row_top = small[y]
            row_bot = small[y + 1]
            parts = []
            for x in range(char_w):
                rt, gt, bt = int(row_top[x][0]), int(row_top[x][1]), int(row_top[x][2])
                rb, gb, bb = int(row_bot[x][0]), int(row_bot[x][1]), int(row_bot[x][2])
                parts.append(
                    f"\033[38;2;{rt};{gt};{bt}m"
                    f"\033[48;2;{rb};{gb};{bb}m"
                    f"▀"
                )
            parts.append("\033[0m")
            lines.append("".join(parts))
        return "\n".join(lines)


class ModeD_Braille(CharMapper):
    """方案 D: 盲文点阵超分辨率渲染 (Braille Patterns U+2800 ~ U+28FF)"""

    def __init__(self, width: int = 120, max_lines: int = 0, threshold: int = 128, dither: str | bool = "ordered"):
        super().__init__(width, max_lines)
        self.threshold = threshold
        if isinstance(dither, bool):
            self.dither = "ordered" if dither else "none"
        else:
            self.dither = dither

        # 8个点在 4x2 块中的二进制权重
        self.BRAILLE_WEIGHTS = np.array([
            [1,   8],
            [2,  16],
            [4,  32],
            [64, 128]
        ], dtype=np.uint8)

    def _fit_size(self, frame_h: int, frame_w: int) -> tuple[int, int]:
        """盲文模式下点阵像素天然 1:1，不需要 // 2 宽高比补偿"""
        w = self.width
        if self.max_lines <= 0:
            lines = max(1, w * frame_h // frame_w)
            return w, lines

        w_from_h = self.max_lines * frame_w // frame_h
        w = min(w, w_from_h)
        w = max(1, w)
        lines = max(1, w * frame_h // frame_w)
        return w, lines

    def _ordered_dither(self, gray: np.ndarray) -> np.ndarray:
        """Bayer 4×4 有序抖动 — 100% NumPy 向量化，无 Python 循环"""
        h, w = gray.shape
        bayer_tiled = np.tile(BAYER_4x4, ((h + 3) // 4, (w + 3) // 4))[:h, :w]
        return gray > bayer_tiled

    def _floyd_steinberg_dither(self, gray: np.ndarray) -> np.ndarray:
        """Floyd-Steinberg 误差扩散抖动，输入 0.0 ~ 255.0 的 float64 灰度图，返回 bool 二值图"""
        h, w = gray.shape
        arr = gray.copy().astype(np.float32)
        out = np.zeros((h, w), dtype=bool)
        threshold = float(self.threshold)

        for y in range(h):
            for x in range(w):
                old_val = arr[y, x]
                new_val = 255.0 if old_val > threshold else 0.0
                out[y, x] = (new_val > 127.0)
                err = old_val - new_val

                if x + 1 < w:
                    arr[y, x + 1] += err * (7.0 / 16.0)
                if y + 1 < h:
                    if x - 1 >= 0:
                        arr[y + 1, x - 1] += err * (3.0 / 16.0)
                    arr[y + 1, x] += err * (5.0 / 16.0)
                    if x + 1 < w:
                        arr[y + 1, x + 1] += err * (1.0 / 16.0)
        return out

    def frame_to_str(self, frame: np.ndarray) -> str:
        fh, fw = frame.shape[:2]
        char_w, char_h = self._fit_size(fh, fw)

        # Braille 每个字符是 2x4 的点阵，所以像素宽高为 char_w * 2, char_h * 4
        pixel_w = char_w * 2
        pixel_h = char_h * 4

        # 缩放至像素分辨率
        small = cv2.resize(frame, (pixel_w, pixel_h), interpolation=cv2.INTER_AREA)

        # 计算灰度
        gray = (small[:, :, 0].astype(np.float64) * 0.299 +
                small[:, :, 1].astype(np.float64) * 0.587 +
                small[:, :, 2].astype(np.float64) * 0.114)

        # 二值化
        if self.dither == "floyd-steinberg":
            binary_frame = self._floyd_steinberg_dither(gray)
        elif self.dither == "ordered":
            binary_frame = self._ordered_dither(gray)
        else:
            binary_frame = gray > self.threshold

        # 1. 切块重构为 (char_h, 4, char_w, 2)，转置为 (char_h, char_w, 4, 2)
        blocks = binary_frame.reshape(char_h, 4, char_w, 2).transpose(0, 2, 1, 3)

        # 2. 与权重相乘求和，得到 U+2800 偏移量
        offsets = np.sum(blocks * self.BRAILLE_WEIGHTS, axis=(2, 3))

        # 3. 亮区均值着色 (Active Pixel Averaging) - NumPy 向量化计算
        color_blocks = small.reshape(char_h, 4, char_w, 2, 3).transpose(0, 2, 1, 3, 4)
        
        # 计算每个 4x2 块中亮区像素的 RGB 累加值
        blocks_expanded = np.expand_dims(blocks, axis=-1)  # (char_h, char_w, 4, 2, 1)
        active_pixel_colors = color_blocks * blocks_expanded  # (char_h, char_w, 4, 2, 3)
        color_sums = np.sum(active_pixel_colors, axis=(2, 3))  # (char_h, char_w, 3)
        
        # 计算每个块中的亮点数量，使用 np.maximum 避免除以 0
        active_counts = np.sum(blocks, axis=(2, 3))  # (char_h, char_w)
        counts_div = np.maximum(1, np.expand_dims(active_counts, axis=-1))
        avg_colors = (color_sums / counts_div).astype(np.int32)  # (char_h, char_w, 3)

        lines = []
        for y in range(char_h):
            parts = []
            for x in range(char_w):
                offset = offsets[y, x]
                if offset == 0:
                    parts.append(" ")
                else:
                    r, g, b = avg_colors[y, x]
                    char_code = chr(0x2800 + offset)
                    parts.append(f"\033[38;2;{r};{g};{b}m{char_code}")
            if parts:
                parts.append("\033[0m")
            lines.append("".join(parts))

        return "\n".join(lines)


def create_mapper(mode: str, width: int, max_lines: int = 0,
                  style: str = "classic", dot_mode: bool = False,
                  threshold: int = 128, dither: str = "ordered") -> CharMapper:
    if mode == "A":
        return ModeA_ASCII(width=width, max_lines=max_lines, style=style,
                           threshold=threshold)
    elif mode == "B":
        return ModeB_Color(width=width, max_lines=max_lines,
                           dot_mode=dot_mode, threshold=threshold)
    elif mode == "C":
        return ModeC_HalfBlock(width=width, max_lines=max_lines)
    elif mode == "D":
        return ModeD_Braille(width=width, max_lines=max_lines, threshold=threshold, dither=dither)
    raise ValueError(f"未知模式: {mode}")

