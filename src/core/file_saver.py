"""文件保存模块 —— 字符帧 → 视频 / .txt / .html"""
import zipfile
import re
import os
import subprocess
import tempfile
import cv2
import numpy as np
from utils.ansi_to_html import ansi_to_html

_ANSI_RE = re.compile(r'\033\[([0-9;]*)m')


class FileSaver:
    """保存字符画到文件"""

    @staticmethod
    def save_txt(frames: list[str], path: str):
        clean_frames = [_strip_ansi(f) for f in frames]
        with open(path, "w", encoding="utf-8") as fp:
            if len(clean_frames) == 1:
                fp.write(clean_frames[0])
            else:
                fp.write(f"\n{'='*60}\n".join(clean_frames))
        return path

    @staticmethod
    def save_html(frames: list[str], path: str):
        if len(frames) == 1:
            html = ansi_to_html(frames[0])
        else:
            parts = [ansi_to_html(f) for f in frames]
            separator = '<hr style="border:1px solid #333;margin:10px 0">'
            combined = separator.join(parts)
            html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    background: #000;
    color: #fff;
    font-family: "Cascadia Mono", "SF Mono", "Consolas", "Courier New", monospace;
    font-size: 8px;
    line-height: 1.0;
    white-space: pre;
  }}
</style>
</head>
<body>{combined}</body>
</html>"""
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(html)
        return path

    @staticmethod
    def save_zip(frames: list[str], path: str):
        base = path.rsplit(".", 1)[0] if "." in path else path
        zip_path = base + ".zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            z = len(str(len(frames)))
            for i, frame in enumerate(frames):
                name = f"frame_{i:0{z}d}.txt"
                zf.writestr(name, _strip_ansi(frame))
        return zip_path

    @staticmethod
    def save_video(frames: list[str], path: str, fps: float = 30.0,
                   source_audio: str | None = None,
                   progress_cb=None):
        """渲染字符帧为 MP4 视频，使用多线程分段并行渲染，可选合并源音频"""
        if not frames:
            return path

        from PIL import Image, ImageDraw, ImageFont
        import concurrent.futures
        import threading
        import tempfile

        font = None
        for font_name in ["Cascadia Mono", "SF Mono", "Consolas",
                           "Courier New", "DejaVu Sans Mono"]:
            try:
                font = ImageFont.truetype(font_name + ".ttf", 14)
                break
            except Exception:
                pass
        if font is None:
            try:
                font = ImageFont.truetype("cour.ttf", 14)
            except Exception:
                font = ImageFont.load_default()

        # 动态测量字符宽度和行高 (终端字体默认 2:1 宽高比)
        try:
            bbox = font.getbbox("█")
            if bbox:
                left, top, right, bottom = bbox
                char_w = right - left
            else:
                char_w = 0
        except AttributeError:
            try:
                char_w, _ = font.getsize("█")
            except Exception:
                char_w = 0
        if char_w < 4:
            char_w = 9
        line_h = char_w * 2

        # 收集所有独特的字符用于预先渲染字形遮罩
        unique_chars = set()
        for f in frames:
            unique_chars.update(_strip_ansi(f))

        # 预先生成字符掩膜缓存
        mask_cache = {}
        for ch in unique_chars:
            if ch == "\n":
                continue
            if ch == "█":
                mask = np.ones((line_h, char_w, 1), dtype=np.float32)
            elif ch == "▀":
                mask = np.zeros((line_h, char_w, 1), dtype=np.float32)
                mask[:line_h // 2, :, :] = 1.0
            elif ch in (" ", "\xa0"):
                mask = np.zeros((line_h, char_w, 1), dtype=np.float32)
            elif 0x2800 <= ord(ch) <= 0x28FF:
                # 盲文点阵手动掩膜生成，避免依赖字体文件
                offset = ord(ch) - 0x2800
                dots = [
                    (offset & 1) > 0,      # Row 0, Col 0
                    (offset & 2) > 0,      # Row 1, Col 0
                    (offset & 4) > 0,      # Row 2, Col 0
                    (offset & 8) > 0,      # Row 0, Col 1
                    (offset & 16) > 0,     # Row 1, Col 1
                    (offset & 32) > 0,     # Row 2, Col 1
                    (offset & 64) > 0,     # Row 3, Col 0
                    (offset & 128) > 0,    # Row 3, Col 1
                ]
                cell_img = Image.new("L", (char_w, line_h), color=0)
                cell_draw = ImageDraw.Draw(cell_img)
                cw = char_w / 2.0
                rh = line_h / 4.0
                dot_r = max(1.0, min(cw, rh) * 0.35)
                
                positions = [
                    (0, 0), (1, 0), (2, 0),  # 点 1, 2, 3
                    (0, 1), (1, 1), (2, 1),  # 点 4, 5, 6
                    (3, 0), (3, 1)           # 点 7, 8
                ]
                for idx, active in enumerate(dots):
                    if active:
                        r_idx, c_idx = positions[idx]
                        cx = cw * (c_idx + 0.5)
                        cy = rh * (r_idx + 0.5)
                        cell_draw.ellipse(
                            [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                            fill=255
                        )
                arr = np.array(cell_img).astype(np.float32) / 255.0
                mask = np.expand_dims(arr, axis=-1)
            else:
                try:
                    cell_img = Image.new("L", (char_w, line_h), color=0)
                    cell_draw = ImageDraw.Draw(cell_img)
                    cell_draw.text((0, 0), ch, fill=255, font=font)
                    arr = np.array(cell_img).astype(np.float32) / 255.0
                    mask = np.expand_dims(arr, axis=-1)
                except Exception:
                    mask = np.zeros((line_h, char_w, 1), dtype=np.float32)
            mask_cache[ch] = mask

        clean = _strip_ansi(frames[0])
        lines = clean.split("\n")
        img_w = max(len(line) for line in lines) * char_w + 4
        img_h = len(lines) * line_h + 4

        # 始终先写临时文件，最后用 ffmpeg 转 H.264
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(tmp_fd)
        write_path = tmp_path

        total = len(frames)
        num_threads = min(4, os.cpu_count() or 1)

        # 当帧数足够多且 CPU 支持多核时启用并行渲染
        if total >= 20 and num_threads > 1:
            chunk_size = (total + num_threads - 1) // num_threads
            chunks = []
            temp_files = []
            
            for idx in range(num_threads):
                start = idx * chunk_size
                end = min(start + chunk_size, total)
                if start >= total:
                    break
                chunks.append(frames[start:end])
                
                temp_fd, temp_path = tempfile.mkstemp(suffix=f"_chunk_{idx}.mp4")
                os.close(temp_fd)
                temp_files.append(temp_path)

            progress_lock = threading.Lock()
            rendered_count = [0]

            def update_progress():
                with progress_lock:
                    rendered_count[0] += 1
                    if progress_cb:
                        progress_cb(rendered_count[0], total)

            def chunk_worker(chunk_idx, frames_chunk, temp_path):
                chunk_writer = None
                try:
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    chunk_writer = cv2.VideoWriter(temp_path, fourcc, fps, (img_w, img_h))
                    for frame_str in frames_chunk:
                        img = _render_frame_image(frame_str, img_w, img_h, char_w, line_h, mask_cache)
                        chunk_writer.write(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                        update_progress()
                    return True
                except Exception as e:
                    print(f"[Thread {chunk_idx}] Error rendering chunk: {e}")
                    return False
                finally:
                    if chunk_writer is not None:
                        chunk_writer.release()

            success = True
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(chunk_worker, idx, chunk, tf) for idx, (chunk, tf) in enumerate(zip(chunks, temp_files))]
                for fut in concurrent.futures.as_completed(futures):
                    if not fut.result():
                        success = False

            if success:
                try:
                    # 优先试用 ffmpeg 拼接 (近乎瞬间完成，无编码损耗)
                    _concat_videos_ffmpeg(temp_files, write_path)
                except Exception as e:
                    print(f"ffmpeg concat failed ({e}), trying OpenCV fallback concat...")
                    try:
                        # 备路：使用 OpenCV 自拼接
                        _concat_videos_opencv(temp_files, write_path, fps, img_w, img_h)
                    except Exception as ex:
                        print(f"OpenCV concat fallback also failed: {ex}")
                        success = False

            # 清除所有临时片段
            for tf in temp_files:
                try:
                    if os.path.exists(tf):
                        os.unlink(tf)
                except Exception:
                    pass

            # 最终拼接若失败，退回单线程写
            if not success:
                print("Parallel encoding failed. Falling back to single-threaded rendering...")
                _save_video_single(frames, write_path, fps, img_w, img_h, char_w, line_h, mask_cache, progress_cb)
        else:
            _save_video_single(frames, write_path, fps, img_w, img_h, char_w, line_h, mask_cache, progress_cb)

        _finalize_video(write_path, source_audio, path)
        try:
            os.unlink(write_path)
        except Exception:
            pass

        return path


def _save_video_single(frames: list[str], path: str, fps: float, img_w: int, img_h: int,
                       char_w: int, line_h: int, mask_cache: dict, progress_cb=None):
    """单线程兜底视频渲染写入"""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (img_w, img_h))
    total = len(frames)
    try:
        for i, frame_str in enumerate(frames):
            img = _render_frame_image(frame_str, img_w, img_h, char_w, line_h, mask_cache)
            writer.write(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            if progress_cb:
                progress_cb(i + 1, total)
    finally:
        writer.release()


def _concat_videos_ffmpeg(temp_files: list[str], output_path: str):
    """使用 ffmpeg concat copy 无损无重编码极速拼接视频片段"""
    import tempfile
    import subprocess
    txt_fd, txt_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(txt_fd, 'w', encoding='utf-8') as f:
            for tf in temp_files:
                safe_path = tf.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", txt_path,
            "-c", "copy",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=30)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode('utf-8', errors='ignore'))
    finally:
        try:
            os.unlink(txt_path)
        except Exception:
            pass


def _concat_videos_opencv(temp_files: list[str], output_path: str, fps: float, img_w: int, img_h: int):
    """使用 OpenCV 重新解码并拼接临时视频片段"""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (img_w, img_h))
    try:
        for tf in temp_files:
            cap = cv2.VideoCapture(tf)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                writer.write(frame)
            cap.release()
    finally:
        writer.release()


def _finalize_video(temp_video: str, audio_path: str | None,
                    output_path: str):
    """用 ffmpeg 将视频重编码为 H.264，可选合并音频"""
    cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
    ]
    if audio_path:
        cmd += ["-i", audio_path]
    cmd += [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "23",
    ]
    if audio_path:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [output_path]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120)
    except Exception:
        import shutil
        shutil.copy(temp_video, output_path)


def _render_frame_image(frame_str: str, w: int, h: int,
                        char_w: int, line_h: int, mask_cache: dict) -> np.ndarray:
    """将 ANSI 字符帧渲染为 RGB 像素图（行级向量化，NumPy 释放 GIL 实现真正多线程并行）"""
    segments = _parse_ansi_line(frame_str)

    # ── 1. 将 segments 展开为逐行的 (chars, fgs, bgs) 网格 ──
    grid_rows = []  # list of (chars_list, fgs_list, bgs_list)
    cur_chars, cur_fgs, cur_bgs = [], [], []

    for seg_text, seg_fg, seg_bg in segments:
        fg = seg_fg or (255, 255, 255)
        bg = seg_bg or (0, 0, 0)
        for ch in seg_text:
            if ch == '\n':
                grid_rows.append((cur_chars, cur_fgs, cur_bgs))
                cur_chars, cur_fgs, cur_bgs = [], [], []
            else:
                cur_chars.append(ch)
                cur_fgs.append(fg)
                cur_bgs.append(bg)
    if cur_chars:
        grid_rows.append((cur_chars, cur_fgs, cur_bgs))

    img_arr = np.zeros((h, w, 3), dtype=np.uint8)
    if not grid_rows:
        return img_arr

    # ── 2. 构建遮罩索引查找表 (字符 → 整数索引) ──
    mask_keys = sorted(mask_cache.keys())
    char_to_idx = {ch: i for i, ch in enumerate(mask_keys)}
    default_mask = np.zeros((line_h, char_w, 1), dtype=np.float32)
    mask_stack = np.stack([mask_cache[ch] for ch in mask_keys] + [default_mask])
    # mask_stack shape: (N+1, line_h, char_w, 1)，最后一个是未知字符的空遮罩
    default_idx = len(mask_keys)

    # ── 3. 逐行向量化渲染 ──
    # 每行内所有列的遮罩混合由单次 NumPy 广播完成，释放 GIL
    avail_w = w - 2  # 可用像素宽度 (跳过左边 2px 边距)

    for r, (chars, fgs, bgs) in enumerate(grid_rows):
        nc = len(chars)
        if nc == 0:
            continue
        y0 = 2 + r * line_h
        if y0 + line_h > h:
            break

        # 本行的字符索引数组和颜色矩阵
        row_idx = np.array([char_to_idx.get(ch, default_idx) for ch in chars],
                           dtype=np.int32)                       # (nc,)
        row_fg = np.array(fgs, dtype=np.float32)                 # (nc, 3)
        row_bg = np.array(bgs, dtype=np.float32)                 # (nc, 3)

        # 向量化查找: 一次取出本行所有列的遮罩
        row_masks = mask_stack[row_idx]                          # (nc, line_h, char_w, 1)

        # 广播混合: tile = mask * fg + (1 - mask) * bg
        fg_e = row_fg[:, np.newaxis, np.newaxis, :]              # (nc, 1, 1, 3)
        bg_e = row_bg[:, np.newaxis, np.newaxis, :]              # (nc, 1, 1, 3)
        row_tiles = (row_masks * fg_e + (1.0 - row_masks) * bg_e).astype(np.uint8)
        # row_tiles shape: (nc, line_h, char_w, 3)

        # 拼接为本行的横向像素带: (line_h, nc * char_w, 3)
        row_img = row_tiles.transpose(1, 0, 2, 3).reshape(line_h, nc * char_w, 3)

        # 裁剪并写入输出图像
        pw = min(row_img.shape[1], avail_w)
        img_arr[y0:y0 + line_h, 2:2 + pw] = row_img[:, :pw]

    return img_arr


def _parse_ansi_line(text: str) -> list[tuple[str, tuple[int, int, int] | None, tuple[int, int, int] | None]]:
    segments = []
    ansi_re = _ANSI_RE

    pos = 0
    current_fg = None
    current_bg = None

    while pos < len(text):
        m = ansi_re.match(text, pos)
        if m:
            params = m.group(1).split(';')
            if not params or params == [''] or params == ['0']:
                current_fg = None
                current_bg = None
            else:
                idx = 0
                while idx < len(params):
                    if params[idx] == '38' and idx + 4 < len(params) and params[idx+1] == '2':
                        try:
                            current_fg = (int(params[idx+2]), int(params[idx+3]), int(params[idx+4]))
                        except ValueError:
                            pass
                        idx += 5
                    elif params[idx] == '48' and idx + 4 < len(params) and params[idx+1] == '2':
                        try:
                            current_bg = (int(params[idx+2]), int(params[idx+3]), int(params[idx+4]))
                        except ValueError:
                            pass
                        idx += 5
                    elif params[idx] == '0' or params[idx] == '':
                        current_fg = None
                        current_bg = None
                        idx += 1
                    else:
                        idx += 1
            pos = m.end()
        else:
            m_next = ansi_re.search(text, pos)
            next_pos = m_next.start() if m_next else len(text)
            plain = text[pos:next_pos]
            if plain:
                segments.append((plain, current_fg, current_bg))
            pos = next_pos

    return segments


def _strip_ansi(text: str) -> str:
    return re.sub(r'\033\[[0-9;]*m', '', text)
