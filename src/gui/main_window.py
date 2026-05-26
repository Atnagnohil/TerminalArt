"""tkinter GUI 主窗口"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import subprocess
from core.media_decoder import MediaDecoder
from core.char_mapper import (
    CHAR_SETS, CharMapper,
)
from core.file_saver import FileSaver
from main import create_mapper
from utils.terminal_utils import get_terminal_size


class TerminalArtGUI:
    """TerminalArt 主窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TerminalArt v1.0")
        self.root.geometry("600x540")
        self.root.resizable(False, False)

        self.file_path = tk.StringVar()
        self.mode = tk.StringVar(value="A")
        self._style_key = "classic"
        self._dot_mode = tk.BooleanVar(value=False)
        self.threshold = tk.IntVar(value=128)
        self.width = tk.IntVar(value=120)
        self.fps_limit = tk.DoubleVar(value=30.0)
        self.loop_play = tk.BooleanVar(value=True)
        self.save_height = tk.IntVar(value=200)
        self.status_text = tk.StringVar(value="就绪")

        self._play_proc: subprocess.Popen | None = None

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 4}

        # ── 文件区 ──
        file_frame = ttk.LabelFrame(self.root, text="文件", padding=8)
        file_frame.pack(fill="x", **pad)

        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x")
        ttk.Button(file_row, text="选择文件", command=self._on_file_select).pack(
            side="left", padx=(0, 8))
        ttk.Entry(file_row, textvariable=self.file_path, state="readonly").pack(
            side="left", fill="x", expand=True)

        # ── 方案区 ──
        mode_frame = ttk.LabelFrame(self.root, text="字符方案", padding=8)
        mode_frame.pack(fill="x", **pad)

        ttk.Radiobutton(mode_frame, text="A - ASCII 黑白（字符艺术家）",
                        variable=self.mode, value="A",
                        command=self._on_mode_change).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="B - ANSI 真彩色",
                        variable=self.mode, value="B",
                        command=self._on_mode_change).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="C - 半块高清彩色（推荐）",
                        variable=self.mode, value="C",
                        command=self._on_mode_change).pack(anchor="w")

        # 风格选择器（仅方案 A 时显示）
        self.style_row = ttk.Frame(mode_frame)
        ttk.Label(self.style_row, text="  字符风格:").pack(side="left")
        style_names = [v["name"] for v in CHAR_SETS.values()]
        self.style_combo = ttk.Combobox(
            self.style_row, state="readonly", width=20,
            values=style_names)
        self.style_combo.current(0)
        self.style_combo.pack(side="left", padx=(4, 0))
        self.style_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        self.style_row.pack(fill="x", pady=(4, 0))

        # 点阵模式复选框（仅方案 B 时显示）
        self.dot_row = ttk.Frame(mode_frame)
        ttk.Checkbutton(self.dot_row, text="点阵模式（仅保留彩色 .）",
                        variable=self._dot_mode,
                        command=self._on_dot_mode_change).pack(anchor="w")

        # ── 参数区 ──
        param_frame = ttk.LabelFrame(self.root, text="参数", padding=8)
        param_frame.pack(fill="x", **pad)

        width_row = ttk.Frame(param_frame)
        width_row.pack(fill="x", pady=2)
        ttk.Label(width_row, text="字符宽度").pack(side="left")
        ttk.Scale(width_row, from_=40, to=400, variable=self.width,
                  orient="horizontal", command=self._on_width_change).pack(
            side="left", fill="x", expand=True, padx=8)
        self.width_label = ttk.Label(width_row, text=str(self.width.get()))
        self.width_label.pack(side="right")

        fps_row = ttk.Frame(param_frame)
        fps_row.pack(fill="x", pady=2)
        ttk.Label(fps_row, text="帧率上限").pack(side="left")
        ttk.Scale(fps_row, from_=1, to=60, variable=self.fps_limit,
                  orient="horizontal", command=self._on_fps_change).pack(
            side="left", fill="x", expand=True, padx=8)
        self.fps_label = ttk.Label(fps_row, text=f"{self.fps_limit.get():.0f} fps")
        self.fps_label.pack(side="right")

        ttk.Checkbutton(param_frame, text="循环播放",
                        variable=self.loop_play).pack(anchor="w")

        # 点阵阈值（方案 A 点阵风格 / 方案 B 点阵模式 时显示）
        self.thresh_row = ttk.Frame(param_frame)
        ttk.Label(self.thresh_row, text="点阵阈值").pack(side="left")
        ttk.Scale(self.thresh_row, from_=0, to=255, variable=self.threshold,
                  orient="horizontal", command=self._on_threshold_change).pack(
            side="left", fill="x", expand=True, padx=8)
        self.thresh_label = ttk.Label(self.thresh_row,
                                      text=str(self.threshold.get()))
        self.thresh_label.pack(side="right")

        # ── 控制区 ──
        ctrl_frame = ttk.LabelFrame(self.root, text="控制", padding=8)
        ctrl_frame.pack(fill="x", **pad)

        btn_row = ttk.Frame(ctrl_frame)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="在终端播放", command=self._on_play).pack(
            side="left", padx=(0, 8))
        ttk.Button(btn_row, text="停止", command=self._on_stop).pack(
            side="left", padx=(0, 8))
        ttk.Button(btn_row, text="保存为视频", command=self._on_save).pack(
            side="left")

        # 视频保存高度
        save_h_row = ttk.Frame(ctrl_frame)
        save_h_row.pack(fill="x", pady=(4, 0))
        ttk.Label(save_h_row, text="视频字符高度").pack(side="left")
        ttk.Scale(save_h_row, from_=50, to=500, variable=self.save_height,
                  orient="horizontal",
                  command=self._on_save_height_change).pack(
            side="left", fill="x", expand=True, padx=8)
        self.save_height_label = ttk.Label(
            save_h_row, text=str(self.save_height.get()))
        self.save_height_label.pack(side="right")

        # 保存进度条
        self.progress_row = ttk.Frame(ctrl_frame)
        self.progress_bar = ttk.Progressbar(
            self.progress_row, mode="determinate", length=300)
        self.progress_bar.pack(side="left", padx=(0, 8))
        self.progress_label = ttk.Label(self.progress_row, text="")

        # ── 状态栏 ──
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom", **pad)
        ttk.Label(status_frame, textvariable=self.status_text).pack(side="left")
        # 终端尺寸提示
        ttk.Label(status_frame, text="终端:").pack(side="right", padx=(0, 2))
        self.term_label = ttk.Label(status_frame, text="")
        self.term_label.pack(side="right", padx=(0, 8))
        self._update_term_label()

    def _update_term_label(self):
        cols, lines = get_terminal_size()
        self.term_label.config(text=f"{cols}x{lines}")

    def _on_file_select(self):
        path = filedialog.askopenfilename(
            title="选择媒体文件",
            filetypes=[
                ("支持的所有格式", "*.mp4;*.avi;*.mov;*.mkv;*.flv;*.wmv;"
                                   "*.jpg;*.jpeg;*.png;*.bmp;*.gif"),
                ("视频文件", "*.mp4;*.avi;*.mov;*.mkv;*.flv;*.wmv"),
                ("图片文件", "*.jpg;*.jpeg;*.png;*.bmp;*.gif"),
            ])
        if path:
            self.file_path.set(path)
            self.status_text.set(f"已选择: {os.path.basename(path)}")

    def _on_mode_change(self):
        self._stop_playback()
        mode = self.mode.get()
        if mode == "A":
            self.style_row.pack(fill="x", pady=(4, 0))
            self.dot_row.pack_forget()
        elif mode == "B":
            self.style_row.pack_forget()
            self.dot_row.pack(fill="x", pady=(4, 0))
        else:
            self.style_row.pack_forget()
            self.dot_row.pack_forget()
            self.thresh_row.pack_forget()
        self._update_thresh_visibility()
        self.status_text.set(f"方案 {mode} 已选择")

    def _on_style_change(self, _event=None):
        self._stop_playback()
        name_to_key = {v["name"]: k for k, v in CHAR_SETS.items()}
        name = self.style_combo.get()
        if name in name_to_key:
            self._style_key = name_to_key[name]
            self.status_text.set(f"字符风格: {name}")
        self._update_thresh_visibility()

    def _on_dot_mode_change(self):
        self._stop_playback()
        self._update_thresh_visibility()

    def _update_thresh_visibility(self):
        """根据当前模式和风格决定是否显示阈值滑块"""
        mode = self.mode.get()
        show = False
        if mode == "A" and self._style_key == "dot":
            show = True
        elif mode == "B" and self._dot_mode.get():
            show = True

        if show:
            self.thresh_row.pack(fill="x", pady=2)
        else:
            self.thresh_row.pack_forget()

    def _on_threshold_change(self, val):
        v = int(float(val))
        self.thresh_label.config(text=str(v))

    def _on_width_change(self, val):
        v = int(float(val))
        self.width_label.config(text=str(v))
        self._update_term_label()

    def _on_fps_change(self, val):
        v = int(float(val))
        self.fps_label.config(text=f"{v} fps")

    def _on_save_height_change(self, val):
        v = int(float(val))
        self.save_height_label.config(text=str(v))

    def _on_play(self):
        if not self.file_path.get():
            messagebox.showwarning("提示", "请先选择媒体文件")
            return

        self._stop_playback()

        mode = self.mode.get()
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--console-play", self.file_path.get()]
        else:
            cmd = [sys.executable, "-m", "main", "--console-play",
                   self.file_path.get()]
            "--mode", mode,
            "--fps", str(int(self.fps_limit.get())),
            "--loop", "1" if self.loop_play.get() else "0",
            "--cols", str(self.width.get()),
        ]
        if mode == "A":
            cmd += ["--style", self._style_key,
                    "--threshold", str(self.threshold.get())]
        elif mode == "B":
            cmd += ["--dot-mode", "1" if self._dot_mode.get() else "0",
                    "--threshold", str(self.threshold.get())]

        self._play_proc = subprocess.Popen(
            cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        self.status_text.set(f"新终端已启动 | 模式:{mode} | 宽度:{self.width.get()}")

    def _stop_playback(self):
        """终止播放子进程"""
        if self._play_proc:
            try:
                self._play_proc.kill()
            except Exception:
                pass
            self._play_proc = None

    def _on_stop(self):
        self._stop_playback()
        self.status_text.set("已停止")

    def _set_controls_state(self, state: str):
        """递归设置/禁用交互式控件，保持进度条和标签处于活动状态"""
        def traverse(widget):
            if isinstance(widget, (ttk.Button, ttk.Scale, ttk.Combobox, ttk.Checkbutton, ttk.Radiobutton, ttk.Entry)):
                try:
                    widget.configure(state=state)
                except tk.TclError:
                    pass
            for child in widget.winfo_children():
                traverse(child)
        traverse(self.root)

    def _on_save(self):
        if not self.file_path.get():
            messagebox.showwarning("提示", "请先选择媒体文件")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 视频", "*.mp4"), ("AVI 视频", "*.avi")])
        if not path:
            return

        # 快照当前所有关键参数，保证线程安全
        file_path_snap = self.file_path.get()
        video_h_snap = self.save_height.get()
        mode_snap = self.mode.get()
        style_snap = self._style_key
        dot_mode_snap = self._dot_mode.get()
        threshold_snap = self.threshold.get()
        fps_limit_snap = self.fps_limit.get()

        # 禁用交互控件，避免多次点击或调参冲突
        self._set_controls_state("disabled")

        # 初始化并显示进度条
        self.progress_row.pack(fill="x", pady=(4, 0))
        self.progress_bar["value"] = 0
        self.progress_label.config(text="0/0")
        self.status_text.set("正在初始化后台任务...")

        # 用于主线程与后台线程同步的状态字典
        progress_data = {
            "current": 0,
            "total": 0,
            "status": "正在解码源文件...",
            "done": False,
            "error": None
        }

        def save_thread_fn():
            try:
                # 1. 解码源文件
                progress_data["status"] = "正在解码源文件..."
                dec = MediaDecoder(file_path_snap)
                fps = min(dec.get_fps(), fps_limit_snap)
                raw_frames = dec.read_all_frames()
                if not raw_frames:
                    dec.release()
                    progress_data["error"] = "无法从文件中解码任何帧"
                    progress_data["done"] = True
                    return
                source_audio = dec.extract_audio()
                vh, vw = raw_frames[0].shape[:2]
                dec.release()

                # 2. 计算字符宽高与渲染
                video_width = max(40, video_h_snap * 2 * vw // vh)
                progress_data["status"] = f"正在渲染字符帧 ({video_width}x{video_h_snap})..."
                progress_data["total"] = len(raw_frames)

                mapper = create_mapper(
                    mode=mode_snap,
                    width=video_width,
                    max_lines=video_h_snap,
                    style=style_snap,
                    dot_mode=dot_mode_snap,
                    threshold=threshold_snap
                )

                save_frames = []
                for idx, f in enumerate(raw_frames):
                    save_frames.append(mapper.frame_to_str(f))
                    progress_data["current"] = idx + 1

                # 3. 编码保存视频
                progress_data["status"] = "正在编码视频..."
                progress_data["current"] = 0  # 重新为编码阶段计数

                def update_cb(current, total):
                    progress_data["current"] = current
                    progress_data["total"] = total
                    progress_data["status"] = f"正在编码视频 ({current}/{total})..."

                FileSaver.save_video(
                    save_frames, path, fps=fps,
                    source_audio=source_audio,
                    progress_cb=update_cb
                )
                progress_data["done"] = True
            except Exception as e:
                import traceback
                traceback.print_exc()
                progress_data["error"] = str(e)
                progress_data["done"] = True

        # 启动后台工作线程
        threading.Thread(target=save_thread_fn, daemon=True).start()

        # 主线程定时轮询更新 GUI 状态
        def check_status():
            if progress_data["error"]:
                messagebox.showerror("错误", f"保存失败: {progress_data['error']}")
                self.progress_row.pack_forget()
                self._set_controls_state("normal")
                self.status_text.set("保存失败")
                return

            if progress_data["done"]:
                self.progress_row.pack_forget()
                self._set_controls_state("normal")
                self.status_text.set(f"已保存: {os.path.basename(path)}")
                messagebox.showinfo("成功", f"视频保存成功！\n文件路径: {path}")
                return

            # 更新 UI 进度和文本
            self.status_text.set(progress_data["status"])
            if progress_data["total"] > 0:
                self.progress_bar["maximum"] = progress_data["total"]
                self.progress_bar["value"] = progress_data["current"]
                self.progress_label.config(text=f"{progress_data['current']}/{progress_data['total']}")

            self.root.after(100, check_status)

        self.root.after(100, check_status)

    def run(self):
        self.root.mainloop()
