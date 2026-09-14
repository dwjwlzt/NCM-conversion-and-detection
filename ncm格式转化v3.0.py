import os
import sys
import base64
import json
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad as aes_unpad

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

MAGIC = b"CTENFDAM"
AES_KEY_RC4 = bytes.fromhex("687A4852416D736F356B496E62617857")
AES_KEY_META = bytes.fromhex("2331346C6A6B5F215C5D2630553C2728")
XOR_RC4_KEY = 0x64
XOR_META = 0x63
PREFIX_NETEASE = b"neteasecloudmusic"
PREFIX_META = b"163 key(Don't modify):"


def _ncm_rc4_build_box(key: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]
    key_box = bytearray(256)
    for i in range(256):
        j = (i + 1) & 0xFF
        sj = S[j]
        sjj = S[(sj + j) & 0xFF]
        key_box[i] = S[(sjj + sj) & 0xFF]
    return bytes(key_box)


def _ncm_rc4_decrypt(data: bytes, key_box: bytes) -> bytes:
    return bytes(b ^ key_box[i & 0xFF] for i, b in enumerate(data))


def decrypt_ncm(ncm_path: str, output_dir: str):
    with open(ncm_path, "rb") as f:
        raw = f.read()

    if raw[:8] != MAGIC:
        raise ValueError("不是有效的NCM文件（魔数校验失败）")

    pos = 10

    rc4_key_size = int.from_bytes(raw[pos:pos + 4], "little")
    pos += 4
    rc4_key_enc = raw[pos:pos + rc4_key_size]
    pos += rc4_key_size

    meta_size = int.from_bytes(raw[pos:pos + 4], "little")
    pos += 4
    meta_enc = raw[pos:pos + meta_size]
    pos += meta_size

    pos += 9

    cover_size = int.from_bytes(raw[pos:pos + 4], "little")
    pos += 4
    cover_data = raw[pos:pos + cover_size]
    pos += cover_size

    audio_enc = raw[pos:]

    rc4_key_xor = bytes(b ^ XOR_RC4_KEY for b in rc4_key_enc)
    cipher = AES.new(AES_KEY_RC4, AES.MODE_ECB)
    rc4_key_full = aes_unpad(cipher.decrypt(rc4_key_xor), 16)
    rc4_key = rc4_key_full[len(PREFIX_NETEASE):]

    meta_json = {}
    ext = ".flac"
    if meta_size > 0:
        try:
            meta_xor = bytes(b ^ XOR_META for b in meta_enc)
            if not meta_xor.startswith(PREFIX_META):
                raise ValueError("meta 前缀不匹配")
            meta_b64 = base64.b64decode(meta_xor[len(PREFIX_META):])
            cipher_meta = AES.new(AES_KEY_META, AES.MODE_ECB)
            meta_json_raw = aes_unpad(cipher_meta.decrypt(meta_b64), 16)
            meta_str = meta_json_raw.decode("utf-8", errors="replace")
            if meta_str.startswith("music:"):
                meta_json = json.loads(meta_str[6:])
                ext = "." + meta_json.get("format", "flac")
        except Exception:
            pass

    key_box = _ncm_rc4_build_box(rc4_key)
    audio_data = _ncm_rc4_decrypt(audio_enc, key_box)

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
            text="批量解密 .ncm 格式为原始音频文件（无需外部exe）",
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
                if ext in (".ncm", ".mp3", ".flac"):
                    file_list.append((full, ext))

        self.log(f"扫描到 {len(file_list)} 个待处理文件 (ncm/mp3/flac)")
        self.log("─" * 48)

        for filepath, ext in file_list:
            total += 1
            basename = os.path.basename(filepath)
            try:
                if ext == ".ncm":
                    self.log(f"[NCM] 解密：{basename}")
                    out_path, meta = decrypt_ncm(filepath, self.music_out_dir)
                    info_parts = []
                    if meta.get("musicName"):
                        info_parts.append(meta["musicName"])
                    if meta.get("artist"):
                        artists = "/".join(a[0] if isinstance(a, list) else str(a) for a in meta["artist"])
                        info_parts.append(artists)
                    if info_parts:
                        self.log(f"  信息：{' - '.join(info_parts)}")
                    self.log(f"  ✅ {os.path.basename(out_path)}")
                    success += 1
                else:
                    self.log(f"[{ext[1:].upper()}] 复制：{basename}")
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