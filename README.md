# DC_Music_Bot_2.0

一个功能丰富的 Discord 音乐机器人，带有 Web 控制面板，支持从 YouTube 和 Bilibili 下载音乐并进行播放管理。它允许用户通过 Discord 命令或 Web 界面控制音乐播放、管理音乐库以及下载新歌曲。

## 目录

- [主要功能](#主要功能)
- [环境要求](#环境要求)
- [安装与配置](#安装与配置)
  - [克隆仓库](#克隆仓库)
  - [安装 Python 依赖](#安装-python-依赖)
  - [配置环境变量](#配置环境变量)
  - [配置 `cookies.txt` (重要，尤其对于服务器部署)](#配置-cookiestxt-重要尤其对于服务器部署)
- [运行机器人 (本地)](#运行机器人-本地)
- [AWS EC2 一键部署 (使用 `deploy_aws_ec2.sh`)](#aws-ec2-一键部署-使用-deploy_aws_ec2sh)
  - [准备 EC2 实例](#准备-ec2-实例)
  - [执行部署脚本](#执行部署脚本)
  - [脚本执行流程](#脚本执行流程)
  - [检查服务状态](#检查服务状态)
- [Web 控制面板](#web-控制面板)
- [Discord 命令](#discord-命令)
  - [音乐播放与控制](#音乐播放与控制)
  - [音乐管理](#音乐管理)
  - [播放器与频道](#播放器与频道)
- [文件结构简介](#文件结构简介)
- [注意事项](#注意事项)

## 主要功能

*   **Discord 音乐播放**: 支持播放单个 MP3 文件和整个播放列表。
*   **全面的播放控制**:
    *   播放、暂停、恢复
    *   下一首、上一首
    *   音量调节 (0-100)
    *   多种播放模式: 单曲循环、列表循环、随机播放、播放完停止
    *   跳转到指定时间点 (seek)
*   **音乐下载**:
    *   通过 Discord 命令 (`/download`) 或 Web 界面下载。
    *   支持 YouTube 和 Bilibili 的视频链接。
    *   可选择将下载的音乐保存为单曲或添加到指定的播放列表（新旧均可）。
*   **音乐库管理**:
    *   通过 Discord 命令或 Web 界面查看所有音乐和播放列表。
    *   删除单曲、播放列表中的单曲或整个播放列表。
*   **Web 控制面板**:
    *   使用 Flask 和 SocketIO 构建，提供实时状态更新。
    *   查看播放器状态和播放队列。
    *   浏览音乐库，删除音乐或播放列表。
    *   提交音乐下载任务，并查看下载进度。
*   **智能语音频道管理**: 当机器人所在的语音频道内没有其他用户时，会在一段时间后自动断开连接。
*   **Cookie 支持**: `yt-dlp` 支持使用 `cookies.txt` 文件，这有助于在下载 YouTube 视频时绕过可能的人机验证，特别是在服务器环境（如 AWS EC2）上。
*   **AWS EC2 一键部署**: 提供 `deploy_aws_ec2.sh` 脚本，简化在 AWS EC2 上的部署流程。

## 环境要求

*   此项目开发使用 Python 3.12.8
*   pip 
*   Git
*   **FFmpeg 和 FFprobe**: 用于音频处理和获取时长。 (部署脚本会自动安装)
*   **Opus library**: Discord 语音通话依赖。 (部署脚本会自动安装)

## 安装与配置

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/Niama7878/DC_Music_Bot_2.0.git
    cd DC_Music_Bot_2.0
    ```

2.  **安装 Python 依赖**:
    ```bash
    pip install discord.py PyNaCl python-dotenv yt-dlp Flask flask-socketio watchdog psutil
    ```

3.  **配置环境变量**:
    *   项目使用 `.env` 文件来管理敏感信息。你可以手动填写此文件，或运行 `env_fill.py` 脚本来引导填写。
        ```bash
        python3 env_fill.py
        ```
        脚本会提示你输入以下信息：
        *   `DISCORD_BOT_TOKEN`: 你的 Discord Bot Token。可以从 [Discord Developer Portal](https://discord.com/developers/applications) 获取。
        *   `SECRET_KEY`: Flask 应用用于会话签名等操作的密钥。脚本会自动生成一个安全的随机密钥。

    *   `.env` 文件内容示例:
        ```env
        DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
        SECRET_KEY=YOUR_RANDOMLY_GENERATED_SECRET_KEY_HERE
        ```

4.  **配置 `cookies.txt` (重要，尤其对于服务器部署)**:
    *   **用途**: YouTube 视频（会触发人机验证）需要登录信息才能正常下载。`cookies.txt` 文件可以让 `yt-dlp` 使用你的 Google 登录会话。
    *   **何时需要**:
        *   **AWS EC2 或其他无头服务器**: 强烈建议配置，因为这些服务器通常没有浏览器环境，`yt-dlp` 无法自动获取 cookies。
        *   **本地环境 (Windows/Mac)**: 如果你已在本地浏览器登录了 Google，`yt-dlp` 可能能自动使用。但如果遇到下载问题，配置 `cookies.txt` 仍然是个好办法。
    *   **如何获取**:
        1.  在你的 Chrome 或 Edge 浏览器中安装 "Get cookies.txt LOCALLY" 扩展: [Chrome Web Store](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
        2.  打开任意 Google 网站，点击该扩展图标，导出 cookies。
        3.  将导出的内容保存为项目根目录下的 `cookies.txt` 文件。
    *   **注意**: 部署脚本 `deploy_aws_ec2.sh` 会在 AWS EC2 环境下提示你粘贴 Cookie 内容来创建 `cookies.txt`，并自动启用 `downloader.py` 中的 cookiefile 配置。如果你在其他环境手动配置，请确保 `downloader.py` 中 `ydl_opts` 字典里的 `"cookiefile": "cookies.txt"` 行没有被注释。

## 运行机器人 (本地)

完成上述配置后，可以直接运行 `app.py` 来启动 Web 服务和 Discord 机器人：
```bash
python3 app.py
```
机器人成功启动后，你会在控制台看到类似 "xxx 成功启动！" 的消息。同时，Flask Web 服务会运行在 `0.0.0.0:5000`。

## AWS EC2 一键部署 (使用 `deploy_aws_ec2.sh`)

项目提供了一个便捷的部署脚本 `deploy_aws_ec2.sh`，专为 Amazon Linux 2 设计。

1.  **准备 EC2 实例**:
    *   启动一个 Amazon Linux 2 EC2 实例。
    *   确保实例的安全组开放了 TCP 端口 `5000` (用于 Web 控制面板) 以及 Discord Bot 所需的出站连接。

2.  **执行部署脚本**:
    通过 SSH 连接到你的 EC2 实例，然后执行以下命令：
    ```bash
    sudo yum install git -y
    git clone https://github.com/Niama7878/DC_Music_Bot_2.0.git
    cd DC_Music_Bot_2.0
    chmod +x deploy_aws_ec2.sh
    ./deploy_aws_ec2.sh
    ```

3.  **脚本执行流程**:
    *   安装 `ffmpeg`, `pip`, `opus` 等系统依赖。
    *   安装 Python 依赖包。
    *   自动修改 `downloader.py` 以启用 `cookies.txt` (取消相关行的注释)。
    *   运行 `env_fill.py` 引导你设置 `DISCORD_BOT_TOKEN` 和 `SECRET_KEY` 并保存到 `.env` 文件。
    *   提示你粘贴 Google 的 Cookie 内容，并将其保存到 `cookies.txt`。
    *   配置并启动一个 `systemd` 服务 (`musicbot_flask.service`)，使机器人在后台运行并开机自启。
    *   显示服务的状态。

4.  **检查服务状态**:
    ```bash
    sudo systemctl status musicbot_flask --no-pager
    ```
    你可以使用 `sudo systemctl stop/start/restart musicbot_flask` 来管理服务。

## Web 控制面板

机器人启动后 (无论是本地运行还是通过 EC2 部署)，你可以通过浏览器访问 Web 控制面板：
`http://<你的服务器IP或localhost>:5000`

主要功能包括：
*   查看当前播放器状态、播放队列。
*   浏览音乐库中的单曲和播放列表。
*   删除音乐或播放列表。
*   提交 YouTube/Bilibili 链接下载音乐，并实时查看下载进度。

## Discord 命令

所有命令均为斜杠命令 (Slash Commands)。

*   **音乐播放与控制**:
    *   `/play <歌曲名称或播放列表名称>`: 播放指定的歌曲或播放列表。
    *   `/pause`: 暂停当前播放。
    *   `/resume`: 恢复播放。
    *   `/next`: 播放队列中的下一首。
    *   `/previous`: 播放队列中的上一首。
    *   `/volume <0-100>`: 设置音量。
    *   `/loop_one`: 设置为单曲循环模式。
    *   `/loop_all`: 设置为列表循环模式。
    *   `/shuffle`: 设置为随机播放模式。
    *   `/no_loop`: 设置为播放完当前列表后停止。
    *   `/seek <秒数 或 mm:ss>`: 跳转到当前歌曲的指定时间点。

*   **音乐管理**:
    *   `/download <URL> [播放列表名称]`: 从指定的 URL 下载音乐。可选择添加到现有播放列表或创建新列表。
    *   `/music_view`: 查看所有音乐和播放列表中的歌曲。
    *   `/delete_music <音乐或播放列表名称>`: 删除指定的单曲、播放列表中的单曲或整个播放列表。

*   **播放器与频道**:
    *   `/player_view`: 查看当前音乐播放器的详细状态。
    *   `/leave`:让机器人离开当前的语音频道。

## 文件结构简介

```
.
├── app.py                 # Flask Web 应用主文件，也负责启动 Discord Bot 线程
├── dc.py                  # Discord Bot 启动和线程管理
├── dc_command.py          # 定义所有 Discord 斜杠命令
├── dc_config.py           # Discord Bot 配置, MusicPlayer 类, 消息文本等
├── dc_event.py            # Discord Bot 事件处理 
├── dc_extra.py            # Discord 命令的辅助函数 
├── downloader.py          # 使用 yt-dlp 下载和转换视频的模块
├── tools.py               # 通用工具函数 (路径处理, 状态获取等)
├── env_fill.py            # 辅助填写 .env 文件的脚本
├── deploy_aws_ec2.sh      # AWS EC2 一键部署脚本
├── mp3/                   # (默认创建) 存放下载的 MP3 文件的目录
├── templates/
│   └── index.html         # Web 控制面板的 HTML 模板
├── static/
│   ├── script.js          # Web 控制面板的 JavaScript 逻辑
│   └── style.css          # Web 控制面板的 CSS 样式
│   └── favicon.ico        # 网站图标
├── .env                   # 存储环境变量
├── cookies.txt            # (用户创建/脚本创建) 存储 Google cookies
└── README.md              # 本文件
```

## 注意事项
*   确保你的 Discord Bot 拥有必要的权限（特别是在语音频道中连接、说话、以及读取消息历史以便正确同步应用命令）。
*   下载的音乐会存储在项目根目录下的 `mp3` 文件夹中。单曲直接存放在 `mp3/` 下，播放列表则会创建 `mp3/<播放列表名>/` 的子文件夹。
*   `deploy_aws_ec2.sh` 脚本中的路径是为 `ec2-user` 用户和 `DC_Music_Bot_2.0` 项目名硬编码的，如果你的用户名或项目目录不同，请相应修改脚本。