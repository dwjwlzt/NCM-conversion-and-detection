# NCM 格式转换工具

批量解密网易云音乐 .ncm 加密格式，转换为原始音频文件（.flac / .mp3）。

## 版本概览

本项目经历了三个版本的演化，核心差异在于 **NCM 解密方式** 和 **GUI 技术栈**：

| | v1.0 | v2.0 | v3.0 |
|---|------|------|------|
| 脚本 | ncm格式转化.py | ncm格式转化v2.0.py | ncm格式转化v3.0.py |
| 解密方式 | 调用 ncmdump.exe（网上找的） | 调用 NCM转mp3拖一拖.exe（原MP3工具附带） | **纯Python实现，无外部exe** |
| GUI 框架 | tkinter（标准库） | customtkinter | customtkinter |
| 元数据支持 | 依赖exe输出 | 依赖exe输出 | **独立获取歌名/艺术家/格式** |
| 输出格式 | 依赖exe行为 | 依赖exe行为 | **自动识别flac/mp3原始格式** |
| 额外依赖 | 无（仅标准库） | customtkinter | customtkinter + pycryptodome |

### 各版本详解

#### v1.0 — 调用 ncmdump.exe

最早的版本，GUI 基于 Python 标准库 tkinter，通过 subprocess 调用网上找到的 ncmdump.exe 进行解密。

#### v2.0 — 调用 NCM转mp3拖一拖.exe

使用 customtkinter 重写了现代化界面，改为调用之前 MP3 转换工具附带的 NCM转mp3拖一拖.exe。由于 exe 行为不透明，文件处理逻辑（临时文件、输出文件检测）较为繁琐。

#### v3.0 — 纯Python实现（推荐）

完全用 Python 实现了 NCM v2 格式的解密算法，**不再依赖任何外部 exe**。核心原理：

```
文件结构:
  [8字节魔数 "CTENFDAM"]
  [2字节 gap]
  [4字节小端长度] + 加密的 RC4 Key (128字节)
  [4字节小端长度] + 加密的 Meta JSON
  [4字节 CRC32]
  [5字节 gap]
  [4字节小端长度] + 封面图片
  [加密的音频数据]

解密流程:
  1. RC4 Key: XOR 0x64 → AES-ECB (key=0x687A4852...) → 去padding → 去 "neteasecloudmusic" 前缀
  2. Meta:    XOR 0x63 → 去 "163 key(Don't modify):" 前缀 → Base64 → AES-ECB (key=0x2331346C...) → JSON
  3. 音频:    使用 NCM 变体 RC4（预计算key_box，非标准RC4）解密
```

## 功能特性

- **批量转换**：选择文件夹，一键批量解密所有 .ncm 文件
- **自动整理**：转换后的文件统一输出到源文件夹下的 音乐/ 子目录
- **实时日志**：图形界面显示处理进度和成功/失败状态
- **现代 UI**：基于 CustomTkinter，支持深色/浅色主题
- **冲突处理**：同名文件自动添加 _copy 后缀，不会覆盖
- **多线程**：转换过程不阻塞界面

## 环境要求

- Windows 系统
- Python 3.8+
- 依赖库：customtkinter、pycryptodome

## 安装依赖

```powershell
pip install -r requirements.txt
```

或单独安装：

```powershell
pip install customtkinter pycryptodome
```

## 使用方法

### 方式一：运行 v3.0 纯Python版（推荐）

```powershell
python ncm格式转化v3.0.py
```

### 方式二：运行 v2.0（需外部exe）

1. 确保 NCM转mp3拖一拖.exe 和脚本在同一目录
2. 运行 `python ncm格式转化v2.0.py`

### 方式三：运行 v1.0（需外部exe）

1. 确保 ncmdump.exe 和脚本在同一目录
2. 运行 `python ncm格式转化.py`

### 通用操作

1. 点击「选择文件夹」，选择包含 .ncm 文件的目录
2. 点击「开始处理」，等待转换完成
3. 转换后的文件保存在源文件夹的 音乐/ 子目录中

### 打包为 EXE

```powershell
pyinstaller -F -w ncm格式转化v3.0.py
```

## 文件说明

| 文件 | 说明 |
|------|------|
| ncm格式转化v3.0.py | **推荐使用**：纯Python解密，无需外部exe |
| ncm格式转化v2.0.py | 调用 NCM转mp3拖一拖.exe 的版本 |
| ncm格式转化.py | 最早版本，调用 ncmdump.exe |
| flac检测.py | FLAC 文件检测工具 |
| NCM转mp3拖一拖.exe | v2.0 所需的核心转换引擎 |
| ncmdump.exe | v1.0 所需的备用转换工具 |
| requirements.txt | Python 依赖清单 |

## 注意事项

- 三个版本功能等价，但 v3.0 不再需要任何外部 exe，部署更简单
- 源文件路径请避免包含特殊字符
- 转换后的音频质量取决于原始 .ncm 文件的编码质量
- 本工具仅供学习交流使用，请支持正版音乐

## 版本历史

- **v3.0**：纯Python实现NCM解密算法，不再依赖外部exe；使用customtkinter；正确获取元数据和原始格式
- **v2.0**：使用customtkinter重写界面，切换exe为 NCM转mp3拖一拖.exe；增加批量处理、日志显示、冲突处理
- **v1.0**：基于tkinter的初始版本，调用 ncmdump.exe 完成解密
