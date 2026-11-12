# Mac 实时字幕（Live Subtitles）

[English](README.md) · **简体中文** · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

为 Mac 上**正在播放的任何声音**实时生成字幕：YouTube、电影、Zoom、游戏都可以。字幕显示在一个透明的悬浮条里，始终位于所有窗口之上，包括全屏的 Chrome。

- **完全离线**：语音识别用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 在本机运行，不需要任何云端服务或账号。
- **录的是系统声音，不只是麦克风**：通过免费的 [BlackHole](https://github.com/ExistentialAudio/BlackHole) 虚拟声卡录制扬声器输出。
- **英文字幕**，或把**中文（以及约 95 种其他语言）实时翻译成英文字幕**。
- **低延迟**：边说边出字，大约每 0.6 秒刷新一次。

---

## 获取与安装（分步说明）

需要 macOS 12 或更高版本（Apple 芯片或 Intel 均可），以及大约 1.5 GB 的可用空间。

### 第 1 步：下载本项目

打开「终端」(Terminal)，运行：

```bash
git clone https://github.com/Helloworldceo/live_subtitles.git
cd live_subtitles
```

没有 git 的话，也可以在 GitHub 页面点击 **Code → Download ZIP**，解压后在终端里 `cd` 进入该文件夹。

### 第 2 步：一键安装

**在中国大陆**，建议使用镜像（Homebrew 和 PyPI 走清华镜像，模型走 hf-mirror.com）：

```bash
./install.sh --china
```

如果还需要「中文 → 英文」翻译，加上 `--translate`，会额外下载多语言模型（约 480 MB）：

```bash
./install.sh --china --translate
```

不在中国大陆的话，直接运行 `./install.sh` 即可。

安装脚本会自动：
1. 在缺少 Homebrew 时安装它；
2. 安装 `portaudio`、`python@3.12` 和 **BlackHole 2ch** 驱动（macOS 会要求输入一次开机密码）；
3. 在 `.venv` 中创建独立的 Python 环境，并安装 `requirements.txt` 里的所有依赖；
4. 下载一次 Whisper 模型，之后就可以完全离线使用。

### 第 3 步：重启 Mac

BlackHole 要重启后才会出现。

### 第 4 步：把系统声音同时送到 BlackHole

1. 打开 **音频 MIDI 设置**（Audio MIDI Setup，按 Cmd+空格 搜索 "Audio MIDI"）。
2. 点击左下角 **+**，选择 **创建多输出设备**（Create Multi-Output Device）。
3. 勾选你的**扬声器或耳机**，以及 **BlackHole 2ch**。
4. **主设备**选你的扬声器；只给 BlackHole 勾选**漂移校正**；两个设备都设为 **48,000 Hz**。
5. 打开 **系统设置 → 声音 → 输出**，选择刚建的**多输出设备**。

> 使用多输出设备时，键盘音量键会失效（这是 macOS 的限制）。可以在播放器里调音量，用完后再把输出切回扬声器。

### 第 5 步：给「终端」授权

打开 **系统设置 → 隐私与安全性**：
- **麦克风**：打开 **终端**。macOS 把 BlackHole 当作麦克风，不授权就只能录到静音。
- **输入监控**：打开 **终端**（可选，只有 Ctrl+Option 全局快捷键需要）。

授权后退出并重新打开终端。

### 第 6 步：测试并运行

```bash
./run.sh --list-devices     # 输入设备里应该能看到 "BlackHole 2ch"
./run.sh --test-audio       # 播放一个视频，电平条应该会动
./run.sh                    # 启动英文字幕
```

---

## 常用命令

| 用途 | 命令 |
|---|---|
| 英文字幕（默认 `base` 模型） | `./run.sh` |
| **中文视频 → 英文字幕** | `./run.sh --translate --language zh --model small --cpu-threads 8` |
| 任意语言 → 英文（自动识别语言） | `./run.sh --translate --model small` |
| 中文字幕（不翻译） | `./run.sh --language zh --model small` |
| 大号黄色字、半透明背景 | `./run.sh --font-size 34 --text-color yellow --bg-opacity 0.3` |
| 查看全部选项 | `./run.sh --help` |

## 快捷键

| 按键 | 作用 |
|---|---|
| **Ctrl+Option+Q** | 退出 |
| **Ctrl+Option+P** | 暂停 / 继续字幕 |
| **Ctrl+Option+H** | 隐藏 / 显示字幕条 |
| **Ctrl+C**（在终端里） | 退出 |

可以用鼠标拖动字幕条。

## 常见问题

| 现象 | 解决办法 |
|---|---|
| 找不到 BlackHole | 重启 Mac，或运行 `sudo killall coreaudiod` |
| `--test-audio` 一直是 0 | 输出没选多输出设备；多输出设备里没勾 BlackHole；或终端没有麦克风权限 |
| 扬声器没声音了 | 要选「多输出设备」，不要只选 BlackHole |
| 模型下载卡住 | 先运行 `export HF_ENDPOINT=https://hf-mirror.com`，或重新运行 `./install.sh --china` |
| 字幕延迟大 | 换小一点的 `--model`，或加 `--cpu-threads 8` |

更详细的说明（英文）见 [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)。
