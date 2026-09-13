import sys
import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading


class NcmConvertGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NCM解密工具(调用ncmdump)")
        self.root.geometry("720x460")
        self.root.resizable(True, True)

        self.source_dir = tk.StringVar()
        self.music_out_dir = None
        # 外部解密程序，和脚本同目录
        self.dumper_exe = os.path.join(os.getcwd(), "ncmdump.exe")

        frame_top = ttk.Frame(root, padding=10)
        frame_top.pack(fill=tk.X)
        ttk.Label(frame_top, text="源文件夹（包含ncm/mp3）：").pack(anchor="w")
        frame_sel = ttk.Frame(frame_top)
        frame_sel.pack(fill=tk.X, pady=4)
        ttk.Entry(frame_sel, textvariable=self.source_dir, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame_sel, text="选择文件夹", command=self.select_source_dir).pack(side=tk.RIGHT, padx=5)

        frame_btn = ttk.Frame(root, padding=5)
        frame_btn.pack()
        self.btn_start = ttk.Button(frame_btn, text="开始处理", command=self.on_start, width=12)
        self.btn_start.pack()

        frame_log = ttk.Frame(root, padding=10)
        frame_log.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame_log, text="运行日志：").pack(anchor="w")
        self.text_log = tk.Text(frame_log)
        self.text_log.pack(fill=tk.BOTH, expand=True)

        frame_bottom = ttk.Frame(root, padding=10)
        frame_bottom.pack(fill=tk.X)
        ttk.Button(frame_bottom, text="打开输出音乐文件夹", command=self.open_music_folder).pack(side=tk.LEFT)
        ttk.Button(frame_bottom, text="退出", command=self.root.destroy).pack(side=tk.RIGHT)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="选择源文件夹")
        if path:
            self.source_dir.set(path)

    def log(self, msg):
        self.text_log.insert(tk.END, msg + "\n")
        self.text_log.see(tk.END)
        self.root.update_idletasks()

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
        if not os.path.exists(self.dumper_exe):
            messagebox.showerror("缺少程序", "请把 ncmdump.exe 和本程序放在同一个目录！")
            return
        src = self.source_dir.get().strip()
        if not os.path.isdir(src):
            messagebox.showerror("错误", "请先选择有效的源文件夹")
            return
        t = threading.Thread(target=self.task_thread, args=(src,), daemon=True)
        t.start()

    def task_thread(self, src_dir):
        self.btn_start.config(state=tk.DISABLED)
        self.text_log.delete(1.0, tk.END)

        self.music_out_dir = os.path.join(src_dir, "音乐")
        os.makedirs(self.music_out_dir, exist_ok=True)
        self.log(f"✅输出目录：{self.music_out_dir}")

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

        self.log(f"📋扫描到 {len(file_list)} 个待处理文件(ncm/mp3)")

        for filepath, ext in file_list:
            total += 1
            basename = os.path.basename(filepath)
            try:
                if ext == ".ncm":
                    self.log(f"处理NCM：{basename}")
                    # 调用ncmdump，输出到目标音乐文件夹
                    ret = subprocess.run(
                        [self.dumper_exe, "-o", self.music_out_dir, filepath],
                        capture_output=True,
                        shell=False
                    )
                    if ret.returncode == 0:
                        self.log(f"✅解密完成：{basename}")
                        success +=1
                    else:
                        err_text = ret.stderr.decode("utf-8",errors="replace")
                        raise Exception(f"ncmdump执行失败:{err_text}")

                elif ext == ".mp3":
                    self.log(f"复制MP3：{basename}")
                    dst = os.path.join(self.music_out_dir, basename)
                    if os.path.exists(dst):
                        name_noext, e = os.path.splitext(basename)
                        dst = os.path.join(self.music_out_dir, f"{name_noext}_copy{e}")
                    shutil.copy2(filepath, dst)
                    self.log(f"✅复制完成 → {os.path.basename(dst)}")
                    success += 1

            except Exception as e:
                self.log(f"❌失败 {basename}：{str(e)}")
                fail += 1

        self.log("\n--------------------")
        self.log(f"📊处理完成，总计：{total} | ✅成功：{success} | ❌失败：{fail}")
        self.log("--------------------")
        self.btn_start.config(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = NcmConvertGUI(root)
    root.mainloop()
