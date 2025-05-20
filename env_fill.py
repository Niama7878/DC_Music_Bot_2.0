import secrets
import os
from dotenv import load_dotenv

load_dotenv()

current_discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
current_secret_key = os.getenv("SECRET_KEY", "")

new_discord_token = current_discord_token
new_secret_key = current_secret_key

print("1. 查看当前的 DISCORD_BOT_TOKEN 和 SECRET_KEY")
print("2. 替换 DISCORD_BOT_TOKEN")
print("3. 替换 SECRET_KEY")
print("4. 同时替换两项")

choice = input("请输入你的选择（1-4）：").strip()

if choice == "1":
    print("\n当前 .env 配置：")
    print(f"DISCORD_BOT_TOKEN: {current_discord_token or '[未设置]'}")
    print(f"SECRET_KEY: {current_secret_key or '[未设置]'}")
    exit(0)
elif choice == "2":
    new_discord_token = input("请输入新的 DISCORD_BOT_TOKEN：").strip()
elif choice == "3":
    new_secret_key = secrets.token_hex(32)
elif choice == "4":
    new_discord_token = input("请输入新的 DISCORD_BOT_TOKEN：").strip()
    new_secret_key = secrets.token_hex(32)
else:
    print("无效选择，程序终止。")
    exit(1)

env_lines = [
    f"DISCORD_BOT_TOKEN={new_discord_token}",
    f"SECRET_KEY={new_secret_key}"
]

with open(".env", "w") as f:
    f.write("\n".join(env_lines))

print("以下是更新的内容：")
if choice in ["2", "4"]:
    print(f"DISCORD_BOT_TOKEN: {new_discord_token}")
if choice in ["3", "4"]:
    print(f"SECRET_KEY: {new_secret_key}")