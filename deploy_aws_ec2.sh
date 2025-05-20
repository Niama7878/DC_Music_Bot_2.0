set -e

echo ">>> 安装 ffmpeg..."
curl -LO https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xvf ffmpeg-release-amd64-static.tar.xz
cd ffmpeg-*-amd64-static
sudo mv ffmpeg /usr/local/bin/
sudo mv ffprobe /usr/local/bin/
cd ..
rm ffmpeg-release-amd64-static.tar.xz

echo ">>> 安装 pip 和 opus..."
sudo yum install python3-pip opus opus-devel -y

echo ">>> 安装 Python 依赖..."
pip3 install --user discord.py PyNaCl python-dotenv yt-dlp Flask flask-socketio watchdog psutil

DOWNLOADER_PATH="/home/ec2-user/DC_Music_Bot_2.0/downloader.py"
echo ">>> 修改 downloader.py 启用 cookies..."
if grep -q '^[[:space:]]*#.*"cookiefile": "cookies.txt"' "$DOWNLOADER_PATH"; then
    sed -i 's/^[[:space:]]*#\(.*"cookiefile": "cookies.txt"\)/\1/' "$DOWNLOADER_PATH"
    echo ">>> 已成功启用 cookies。"
else
    echo ">>> downloader.py 已经修改过或不存在目标注释行。"
fi

echo ">>> 执行 env_fill.py 设置 TOKEN 和 SECRET_KEY..."
cd /home/ec2-user/DC_Music_Bot_2.0
python3 env_fill.py

echo ">>> 请粘贴你的 Google Cookie（输入 EOF 并回车保存）："
COOKIE_PATH="/home/ec2-user/DC_Music_Bot_2.0/cookies.txt"
rm -f "$COOKIE_PATH"
touch "$COOKIE_PATH"

while true; do
    read -r line
    if [[ "$line" == "EOF" ]]; then
        break
    fi
    echo "$line" >> "$COOKIE_PATH"
done
echo ">>> Cookie 已保存到 cookies.txt"

echo ">>> 配置 systemd 服务..."
SERVICE_PATH="/etc/systemd/system/musicbot_flask.service"
sudo tee $SERVICE_PATH > /dev/null <<EOL
[Unit]
Description=Flask-SocketIO Music Bot
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/DC_Music_Bot_2.0
ExecStart=/usr/bin/python3 /home/ec2-user/DC_Music_Bot_2.0/app.py
Restart=always
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOL

echo ">>> 启动服务..."
sudo systemctl enable musicbot_flask
sudo systemctl start musicbot_flask
sudo systemctl status musicbot_flask --no-pager