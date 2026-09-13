import sys
import os
import re
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

DEFAULT_SCAN_DIR = r"输入路径"
REPORT_FILENAME = "flac_report.html"

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
_PROGRESS_HINTS = ("Analyzing audio files", "━━", "╺", "⠋", "⠙", "⠹", "⠸",
                   "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def _clean_line(raw):
    text = _ANSI_RE.sub("", raw).replace("\r", "").replace("\n", "").strip()
    if not text:
        return None
    if any(h in text for h in _PROGRESS_HINTS):
        return None
    return text


class FlacDetectiveGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FLAC 假无损检测")
        w, h = 800, 560
        self.geometry(f"{w}x{h}")
        self.minsize(680, 440)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.scan_dir = ctk.StringVar(value=DEFAULT_SCAN_DIR)
        self.deep_scan = ctk.BooleanVar(value=True)
        self.report_path = None

        self._build_ui()

    def _build_ui(self):
        pad = 16

        title = ctk.CTkLabel(
            self, text="FLAC 假无损检测",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(pad, 4), padx=pad, anchor="w")

        subtitle = ctk.CTkLabel(
            self, text="批量扫描无损音频文件，识别由有损格式转码的假无损",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        subtitle.pack(pady=(0, pad), padx=pad, anchor="w")

        frame_sel = ctk.CTkFrame(self, fg_color="transparent")
        frame_sel.pack(fill=ctk.X, padx=pad, pady=(0, 12))

        ctk.CTkLabel(
            frame_sel, text="扫描文件夹",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(frame_sel, fg_color="transparent")
        row.pack(fill=ctk.X)

        self.entry_dir = ctk.CTkEntry(
            row, textvariable=self.scan_dir,
            height=40, font=ctk.CTkFont(size=12),
            fg_color=self._entry_bg(),
            border_color=self._border(),
        )
        self.entry_dir.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))

        ctk.CTkButton(
            row, text="选择文件夹", command=self.select_scan_dir,
            width=120, height=40, font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, hover=True,
        ).pack(side=ctk.RIGHT)

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill=ctk.X, padx=pad, pady=(0, 12))

        ctk.CTkCheckBox(
            opts, text="深度扫描（更严格识别高码率有损转码，速度稍慢）",
            variable=self.deep_scan,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w")

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill=ctk.X, padx=pad, pady=(0, 12))
        frame_btn.grid_columnconfigure(0, weight=1)
        frame_btn.grid_columnconfigure(1, weight=1)
        frame_btn.grid_columnconfigure(2, weight=1)

        self.btn_start = ctk.CTkButton(
            frame_btn, text="▶  开始检测", command=self.on_start,
            height=42, font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10, hover=True,
            fg_color="#2563eb", hover_color="#1d4ed8",
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_open_report = ctk.CTkButton(
            frame_btn, text="📄  打开报告", command=self.open_report,
            height=42, font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, hover=True,
            fg_color="#4b5563", hover_color="#374151",
        )
        self.btn_open_report.grid(row=0, column=1, sticky="ew", padx=6)

        self.btn_exit = ctk.CTkButton(
            frame_btn, text="✕  退出", command=self.destroy,
            height=42, font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, hover=True,
            fg_color="#6b7280", hover_color="#4b5563",
        )
        self.btn_exit.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        frame_log = ctk.CTkFrame(self)
        frame_log.pack(fill=ctk.BOTH, expand=True, padx=pad, pady=(0, pad))

        header = ctk.CTkFrame(frame_log, fg_color="transparent")
        header.pack(fill=ctk.X, padx=12, pady=(12, 6))
        ctk.CTkLabel(
            header, text="运行日志",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side=ctk.LEFT)

        self.text_log = ctk.CTkTextbox(
            frame_log, font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=10, height=220,
        )
        self.text_log.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(0, 12))

    def _entry_bg(self):
        return "#1f2937" if ctk.get_appearance_mode() == "Dark" else "#f3f4f6"

    def _border(self):
        return "#374151" if ctk.get_appearance_mode() == "Dark" else "#d1d5db"

    def select_scan_dir(self):
        path = filedialog.askdirectory(title="选择要扫描的文件夹")
        if path:
            self.scan_dir.set(path)

    def log(self, msg):
        self.text_log.insert(ctk.END, msg + "\n")
        self.text_log.see(ctk.END)

    def open_report(self):
        if self.report_path and os.path.exists(self.report_path):
            if sys.platform == "win32":
                os.startfile(self.report_path)
            elif sys.platform == "darwin":
                os.system(f'open "{self.report_path}"')
            else:
                os.system(f'xdg-open "{self.report_path}"')
        else:
            messagebox.showinfo("提示", "报告还未生成")

    def on_start(self):
        src = self.scan_dir.get().strip()
        if not os.path.isdir(src):
            messagebox.showerror("错误", "请先选择有效的扫描文件夹")
            return
        t = threading.Thread(target=self.task_thread, args=(src,), daemon=True)
        t.start()

    def task_thread(self, src_dir):
        self.btn_start.configure(state=ctk.DISABLED, text="检测中…")
        self.text_log.delete("1.0", ctk.END)

        self.report_path = os.path.join(src_dir, REPORT_FILENAME)

        cmd = ["flac-detective", src_dir, "--format", "html", "--output", self.report_path]
        if self.deep_scan.get():
            cmd.insert(2, "--deep")

        self.log(f"扫描目录：{src_dir}")
        self.log(f"报告输出：{self.report_path}")
        self.log(f"深度扫描：{'开启' if self.deep_scan.get() else '关闭'}")
        self.log("─" * 48)
        self.log("开始分析，请稍候…")

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", shell=False,
                bufsize=1,
            )

            for raw_line in proc.stdout:
                line = _clean_line(raw_line)
                if line is not None:
                    self.log(line)

            returncode = proc.wait()

            if returncode == 0:
                self.log("─" * 48)
                self.log("✅ 检测完成")
                if os.path.exists(self.report_path):
                    self.log(f"📄 HTML 报告已生成：{self.report_path}")
                else:
                    self.log("⚠️ 未找到报告文件")
            else:
                self.log("─" * 48)
                self.log(f"❌ 检测异常，返回码：{returncode}")

        except FileNotFoundError:
            self.log("❌ 未找到 flac-detective，请先安装：pip install flac-detective")
        except Exception as e:
            self.log(f"❌ 运行出错：{e}")

        self.btn_start.configure(state=ctk.NORMAL, text="▶  开始检测")


if __name__ == "__main__":
    app = FlacDetectiveGUI()
    app.mainloop()