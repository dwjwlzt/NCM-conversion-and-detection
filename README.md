# NCM 格式转换 & FLAC 检测工具

批量解密网易云音乐 .ncm 加密格式，以及识别由有损转码的假无损 FLAC 文件。

## 目录

- [NCM 格式转换](#ncm-格式转换)
  - [v3.0 — 纯Python实现（推荐）](#v30--纯python实现推荐)
  - [v1.0 / v2.0](#v10--调用-ncmdumpexe)
  - [使用方法](#使用方法)
- [FLAC 假无损检测](#flac-假无损检测)
- [环境要求与安装](#环境要求与安装)
- [文件说明](#文件说明)

---

## NCM 格式转换

### v3.0 — 纯Python实现（推荐）

完全用 Python 实现 NCM v2 格式的解密算法，**不再依赖任何外部 exe**。

#### 解密原理

```
文件结构:
  [8字节魔数 "CTENFDAM"]
  [2字节 gap]
  [4字节小端长度] + 加密的 RC4 Key
  [4字节小端长度] + 加密的 Meta JSON
  [4字节 CRC32]
  [5字节 gap]
  [4字节小端长度] + 封面图片
  [加密的音频数据]

解密流程:
  1. RC4 Key: XOR 0x64 → AES-ECB → 去padding → 去 "neteasecloudmusic" 前缀
  2. Meta:    XOR 0x63 → 去 "163 key(Don't modify):" 前缀 → Base64 → AES-ECB → JSON
  3. 音频:    NCM 变体 RC4（预计算 key_box）解密
```

#### 输出格式识别

解密后会按以下优先级确定文件扩展名：

| 优先级 | 方式 | 说明 |
|--------|------|------|
| 1 | **音频文件头魔数检测** | 直接检查解密后音频的前 16 字节，识别 FLAC（`fLaC`）、MP3（`ID3` / `0xFF 0xFB`）、OGG（`OggS`）、WAV（`RIFF`）——最准确 |
| 2 | NCM meta 元数据 | JSON 中的 `format` 字段作为兜底 |
| 3 | `.flac` | 最终兜底 |

相比旧版本硬编码 `.flac` 的策略，现在即便 meta 数据缺失或损坏也能正确识别真实格式。

#### 文件名命名规则

输出文件名按以下策略生成：

| 条件 | 输出格式 | 示例 |
|------|---------|------|
| 有歌曲名 + 有歌手 | `歌曲名 - 歌手.ext` | `Alone - Alan Walker.flac` |
| 只有歌曲名 | `歌曲名.ext` | `Title.flac` |
| 只有歌手 | `歌手.ext` | `Artist.flac` |
| meta 全空 | `原始文件名.ext` | `fallback.flac` |

多歌手用 `/` 连接，如 `Song - A/B/C.flac`。文件名中的非法字符（`<>:"/\|?*`）自动替换为 `_`。

#### 功能特性

- **纯 Python 解密**：无需任何外部 exe
- **音频魔数检测**：从文件头识别真实格式，避免格式错标
- **文件名含歌手**：自动拼接为 `歌曲名 - 歌手`
- **批量转换**：选择文件夹，一键处理所有 .ncm 文件
- **自动整理**：输出到源文件夹下的 `音乐/` 子目录
- **实时日志**：图形界面显示处理进度
- **现代 UI**：基于 CustomTkinter，支持深色/浅色主题
- **冲突处理**：同名文件自动加 `_copy` 后缀
- **多线程**：转换不阻塞界面

### v1.0 — 调用 ncmdump.exe

最早的版本，基于 Python 标准库 tkinter，通过 subprocess 调用外部 ncmdump.exe 解密。

### v2.0 — 调用 NCM转mp3拖一拖.exe

使用 customtkinter 重写界面，改为调用之前 MP3 转换工具附带的 exe。文件处理逻辑较为繁琐。

> v1.0 / v2.0 均依赖外部 exe，推荐直接使用 v3.0。

### 使用方法

```powershell
python ncm格式转化v3.0.py
```

1. 点击「选择文件夹」，选择包含 .ncm 文件的目录
2. 点击「开始处理」，等待转换完成
3. 输出文件保存在源文件夹的 `音乐/` 子目录中

可选：打包为 exe
```powershell
pyinstaller -F -w ncm格式转化v3.0.py
```

---

## FLAC 假无损检测

一个独立的 GUI 工具，批量扫描 .flac 文件，识别那些由有损格式（如低码率 MP3）转码而来的**假无损**文件。

### 原理

FLAC 是真正的无损格式，解码后 PCM 数据与原始 PCM 完全一致。但如果源文件本身就是有损的（比如 128kbps MP3），再转码成 FLAC 也无法恢复丢失的信息——这种文件就是「假无损」。

`flac检测.py` 通过调用 [flac-detective](https://pypi.org/project/flac-detective/) 这个外部 Python 库，对音频频谱、编码痕迹等进行分析，生成 HTML 检测报告。

### 使用方法

```powershell
python flac检测.py
```

1. 点击「选择文件夹」，选择包含 .flac 文件的目录
2. 可选勾选「深度扫描」——更严格识别高码率有损转码，速度稍慢
3. 点击「开始检测」，等待完成
4. 检测完成后可点击「打开报告」查看 HTML 报告

### 运行依赖

除了 customtkinter，还需要安装 `flac-detective`：

```powershell
pip install flac-detective
```

---

## 环境要求与安装

- Windows 系统
- Python 3.8+

```powershell
pip install -r requirements.txt
```

或按需单独安装：

| 工具 | 依赖 |
|------|------|
| ncm格式转化v3.0.py | `customtkinter`, `pycryptodome` |
| flac检测.py | `customtkinter`, `flac-detective` |
| v1.0 / v2.0 | 还需对应的外部 exe 文件 |

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `ncm格式转化v3.0.py` | **推荐使用**：纯 Python NCM 解密，音频魔数检测 + 歌手命名 |
| `flac检测.py` | 独立工具：FLAC 假无损检测，生成 HTML 报告 |
| `ncm格式转化v2.0.py` | v2.0 版本，调用 NCM转mp3拖一拖.exe |
| `ncm格式转化.py` | v1.0 版本，调用 ncmdump.exe |
| `NCM转mp3拖一拖.exe` | v2.0 所需的外部转换引擎 |
| `ncmdump.exe` | v1.0 所需的外部转换工具 |
| `requirements.txt` | Python 依赖清单 |

---

## 注意事项

- NCM 解密工具仅供学习交流使用，请支持正版音乐
- FLAC 检测工具依赖 flac-detective 外部库，首次使用需单独安装
- 源文件路径请避免包含特殊字符