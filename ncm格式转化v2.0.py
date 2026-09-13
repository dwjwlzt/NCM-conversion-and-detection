import sys
import os
import shutil
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def resource_path(relative_path):
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


class NcmConvertGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NCM 解密工具")
        w, h = 780, 520
        self.geometry(f"{w}x{h}")
        self.minsize(640, 420)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.source_dir = ctk.StringVar()
        self.music_out_dir = None
        self.converter_exe = resource_path("NCM转mp3拖一拖.exe")

        self._build_ui()

    def _build_ui(self):
        pad = 16

        title = ctk.CTkLabel(
            self, text="NCM 解密工具",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(pad, 4), padx=pad, anchor="w")

        subtitle = ctk.CTkLabel(
            self, text="批量解密 .ncm 格式为无损音频文件",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        subtitle.pack(pady=(0, pad), padx=pad, anchor="w")

        frame_sel = ctk.CTkFrame(self, fg_color="transparent")
        frame_sel.pack(fill=ctk.X, padx=pad, pady=(0, 12))

        ctk.CTkLabel(
            frame_sel, text="源文件夹",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(frame_sel, fg_color="transparent")
        row.pack(fill=ctk.X)

        self.entry_dir = ctk.CTkEntry(
            row, textvariable=self.source_dir, state="readonly",
            height=40, font=ctk.CTkFont(size=12),
            fg_color=self._entry_bg(),
            border_color=self._border(),
        )
        self.entry_dir.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))

        ctk.CTkButton(
            row, text="选择文件夹", command=self.select_source_dir,
            width=120, height=40, font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, hover=True,
        ).pack(side=ctk.RIGHT)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill=ctk.X, padx=pad, pady=(0, 12))
        frame_btn.grid_columnconfigure(0, weight=1)
        frame_btn.grid_columnconfigure(1, weight=1)
        frame_btn.grid_columnconfigure(2, weight=1)

        self.btn_start = ctk.CTkButton(
            frame_btn, text="▶  开始处理", command=self.on_start,
            height=42, font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10, hover=True,
            fg_color="#2563eb", hover_color="#1d4ed8",
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_open_out = ctk.CTkButton(
            frame_btn, text="📁  打开处理后文件夹", command=self.open_music_folder,
            height=42, font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, hover=True,
            fg_color="#4b5563", hover_color="#374151",
        )
        self.btn_open_out.grid(row=0, column=1, sticky="ew", padx=6)

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
            corner_radius=10, height=200,
        )
        self.text_log.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(0, 12))

    def _entry_bg(self):
        return "#1f2937" if ctk.get_appearance_mode() == "Dark" else "#f3f4f6"

    def _border(self):
        return "#374151" if ctk.get_appearance_mode() == "Dark" else "#d1d5db"

    def select_source_dir(self):
        path = filedialog.askdirectory(title="选择源文件夹")
        if path:
            self.source_dir.set(path)

    def log(self, msg):
        self.text_log.insert(ctk.END, msg + "\n")
        self.text_log.see(ctk.END)

    def open_music_folder(self):
        if self.music_out_dir and os.path.exists(self.music_out_dir):
            if sys.platform == "win32":
                os.startfile(self.music_out_dir)
            elif sys.platform == "darwin":
                os.system(f'open "{self.music_out_dir}"')
            else:
                os.system(f'xdg-open "{self.music_out_dir}"')
        else:
            messagebox.showinfo("提示", "输出文件夹还未生成")

    def on_start(self):
        if not os.path.exists(self.converter_exe):
            messagebox.showerror("缺少程序", "请把 NCM转mp3拖一拖.exe 和本程序放在同一个目录！")
            return
        src = self.source_dir.get().strip()
        if not os.path.isdir(src):
            messagebox.showerror("错误", "请先选择有效的源文件夹")
            return
        t = threading.Thread(target=self.task_thread, args=(src,), daemon=True)
        t.start()

    def find_new_file(self, dir_path, before_set):
        after_set = set(os.listdir(dir_path))
        new_files = after_set - before_set
        for name in new_files:
            ext = os.path.splitext(name)[1].lower()
            if ext in (".mp3", ".flac", ".wav"):
                return os.path.join(dir_path, name)
        return None

    def resolve_conflict(self, dst):
        if not os.path.exists(dst):
            return dst
        name_noext, e = os.path.splitext(dst)
        return f"{name_noext}_copy{e}"

    def task_thread(self, src_dir):
        self.btn_start.configure(state=ctk.DISABLED, text="处理中…")
        self.text_log.delete("1.0", ctk.END)

        self.music_out_dir = os.path.join(src_dir, "音乐")
        os.makedirs(self.music_out_dir, exist_ok=True)
        self.log(f"输出目录：{self.music_out_dir}")

        total = 0
        success = 0
        fail = 0

        file_list = []
        for name in os.listdir(src_dir):
            full = os.path.join(src_dir, name)
            if os.path.isfile(full):
                ext = os.path.splitext(name)[1].lower()
                if ext in (".ncm", ".mp3"):
                    file_list.append((full, ext))

        self.log(f"扫描到 {len(file_list)} 个待处理文件 (ncm/mp3)")
        self.log("─" * 48)

        for filepath, ext in file_list:
            total += 1
            basename = os.path.basename(filepath)
            try:
                if ext == ".ncm":
                    self.log(f"[NCM] 处理：{basename}")
                    temp_ncm = os.path.join(self.music_out_dir, basename)
                    shutil.copy2(filepath, temp_ncm)

                    before_set = set(os.listdir(self.music_out_dir))

                    ret = subprocess.run(
                        [self.converter_exe, temp_ncm],
                        capture_output=True,
                        shell=False
                    )

                    try:
                        os.remove(temp_ncm)
                    except OSError:
                        pass

                    new_file = self.find_new_file(self.music_out_dir, before_set)

                    if ret.returncode == 0 and new_file and os.path.exists(new_file):
                        new_basename = os.path.basename(new_file)
                        dst = self.resolve_conflict(os.path.join(self.music_out_dir, new_basename))
                        shutil.move(new_file, dst)
                        self.log(f"  ✅ {os.path.basename(dst)}")
                        success += 1
                    else:
                        err_text = ret.stderr.decode("utf-8", errors="replace").strip()
                        if ret.returncode != 0 and err_text:
                            self.log(f"  转换器输出: {err_text}")
                        raise Exception(f"返回码={ret.returncode}, 未检测到输出文件")

                elif ext == ".mp3":
                    self.log(f"[MP3] 复制：{basename}")
                    dst = self.resolve_conflict(os.path.join(self.music_out_dir, basename))
                    shutil.copy2(filepath, dst)
                    self.log(f"  ✅ {os.path.basename(dst)}")
                    success += 1

            except Exception as e:
                self.log(f"  ❌ 失败：{e}")
                fail += 1

        self.log("─" * 48)
        self.log(f"完成  总计 {total}  |  成功 {success}  |  失败 {fail}")

        self.btn_start.configure(state=ctk.NORMAL, text="▶  开始处理")


if __name__ == "__main__":
    app = NcmConvertGUI()
    app.mainloop()