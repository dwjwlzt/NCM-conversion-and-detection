import os
import sys
import struct
import base64
import json
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad as aes_unpad
    HAS_PYCRYPTODOME = True
except ImportError:
    HAS_PYCRYPTODOME = False

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

MAGIC = b"CTENFDAM"
CORE_KEY = bytes([
    0x68, 0x7A, 0x48, 0x6D, 0x73, 0xF1, 0x16, 0xB8,
    0x3D, 0x1C, 0xC8, 0x66, 0x16, 0xC5, 0x18, 0x2C,
])
META_KEY = bytes([
    0x23, 0x31, 0x34, 0x6C, 0x6A, 0x6B, 0x5F, 0x21,
    0x5C, 0x5D, 0x26, 0x30, 0x55, 0x3C, 0x27, 0x28,
])
META_PREFIX = b"163 key(Don't modify anything)"


def rc4_crypt(data: bytes, key: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]

    i = j = 0
    result = bytearray()
    for byte in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        result.append(byte ^ S[(S[i] + S[j]) % 256])
    return bytes(result)


def decrypt_ncm(ncm_path: str, output_dir: str):
    with open(ncm_path, "rb") as f:
        raw = f.read()

    if raw[:8] != MAGIC:
        raise ValueError("不是有效的NCM文件（魔数校验失败）")

    pos = 8
    key_len = struct.unpack(">H", raw[pos:pos + 2])[0]
    pos += 2
    encrypted_key = raw[pos:pos + key_len]
    pos += key_len

    aes_key = rc4_crypt(encrypted_key, CORE_KEY)

    meta_len = struct.unpack(">H", raw[pos:pos + 2])[0]
    pos += 2
    encrypted_meta = raw[pos:pos + meta_len]
    pos += meta_len

    meta_json = {}
    ext = ".mp3"

    if HAS_PYCRYPTODOME:
        meta_raw = rc4_crypt(encrypted_meta, META_KEY)
        try:
            if meta_raw.startswith(META_PREFIX):
                meta_raw = meta_raw[len(META_PREFIX):]
            cipher = AES.new(aes_key, AES.MODE_ECB)
            dec = aes_unpad(cipher.decrypt(base64.b64decode(meta_raw)), 16)
            meta_json = json.loads(dec.decode("utf-8", errors="replace"))
            ext = "." + meta_json.get("format", "mp3")
        except Exception:
            pass

    audio_data = rc4_crypt(raw[pos:], aes_key)

    song_name = meta_json.get("musicName", "") or os.path.splitext(
        os.path.basename(ncm_path)
    )[0]

    for ch in '<>:"/\\|?*':
        song_name = song_name.replace(ch, "_")

    out_name = f"{song_name}{ext}"
    out_path = os.path.join(output_dir, out_name)

    counter = 1
    base_root, base_ext = os.path.splitext(out_path)
    while os.path.exists(out_path):
        out_path = f"{base_root}_{counter}{base_ext}"
        counter += 1

    with open(out_path, "wb") as f:
        f.write(audio_data)

    return out_path, meta_json


class NcmConvertGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NCM 解密工具 (纯Python版)")
        w, h = 780, 520
        self.geometry(f"{w}x{h}")
        self.minsize(640, 420)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.source_dir = ctk.StringVar()
        self.music_out_dir = None

        self._build_ui()

        if not HAS_PYCRYPTODOME:
            messagebox.showwarning(
                "依赖提示",
                "未检测到 pycryptodome 库。\n"
                "将使用 NCM 文件名作为输出文件名，无法获取歌曲元数据。\n"
                "可在虚拟环境中运行: pip install pycryptodome",
            )

    def _build_ui(self):
        pad = 16

        title = ctk.CTkLabel(
            self,
            text="NCM 解密工具 (纯Python版)",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(pad, 4), padx=pad, anchor="w")

        subtitle = ctk.CTkLabel(
            self,
            text="批量解密 .ncm 格式为无损音频文件（无需外部exe）",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        subtitle.pack(pady=(0, pad), padx=pad, anchor="w")

        frame_sel = ctk.CTkFrame(self, fg_color="transparent")
        frame_sel.pack(fill=ctk.X, padx=pad, pady=(0, 12))

        ctk.CTkLabel(
            frame_sel,
            text="源文件夹",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(frame_sel, fg_color="transparent")
        row.pack(fill=ctk.X)

        self.entry_dir = ctk.CTkEntry(
            row,
            textvariable=self.source_dir,
            state="readonly",
            height=40,
            font=ctk.CTkFont(size=12),
            fg_color=self._entry_bg(),
            border_color=self._border(),
        )
        self.entry_dir.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))

        ctk.CTkButton(
            row,
            text="选择文件夹",
            command=self.select_source_dir,
            width=120,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10,
            hover=True,
        ).pack(side=ctk.RIGHT)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill=ctk.X, padx=pad, pady=(0, 12))
        frame_btn.grid_columnconfigure(0, weight=1)
        frame_btn.grid_columnconfigure(1, weight=1)
        frame_btn.grid_columnconfigure(2, weight=1)

        self.btn_start = ctk.CTkButton(
            frame_btn,
            text="▶  开始处理",
            command=self.on_start,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10,
            hover=True,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_open_out = ctk.CTkButton(
            frame_btn,
            text="📁  打开处理后文件夹",
            command=self.open_music_folder,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10,
            hover=True,
            fg_color="#4b5563",
            hover_color="#374151",
        )
        self.btn_open_out.grid(row=0, column=1, sticky="ew", padx=6)

        self.btn_exit = ctk.CTkButton(
            frame_btn,
            text="✕  退出",
            command=self.destroy,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10,
            hover=True,
            fg_color="#6b7280",
            hover_color="#4b5563",
        )
        self.btn_exit.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        frame_log = ctk.CTkFrame(self)
        frame_log.pack(fill=ctk.BOTH, expand=True, padx=pad, pady=(0, pad))

        header = ctk.CTkFrame(frame_log, fg_color="transparent")
        header.pack(fill=ctk.X, padx=12, pady=(12, 6))
        ctk.CTkLabel(
            header,
            text="运行日志",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side=ctk.LEFT)

        self.text_log = ctk.CTkTextbox(
            frame_log,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=10,
            height=200,
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
        src = self.source_dir.get().strip()
        if not os.path.isdir(src):
            messagebox.showerror("错误", "请先选择有效的源文件夹")
            return
        t = threading.Thread(target=self.task_thread, args=(src,), daemon=True)
        t.start()

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
                    self.log(f"[NCM] 解密：{basename}")
                    out_path, meta = decrypt_ncm(filepath, self.music_out_dir)
                    self.log(f"  ✅ {os.path.basename(out_path)}")
                    success += 1
                elif ext == ".mp3":
                    self.log(f"[MP3] 复制：{basename}")
                    dst = self.resolve_conflict(
                        os.path.join(self.music_out_dir, basename)
                    )
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