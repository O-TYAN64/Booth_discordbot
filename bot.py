import discord
from discord import app_commands
from discord.ext import tasks
import yaml
import json
import os
import requests
from bs4 import BeautifulSoup

# --- 設定読み込み ---
with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

TOKEN = config["discord"]["token"]
NOTIFY_CHANNEL_ID = config["discord"]["notify_channel_id"]
NOTIFY_INTERVAL = config["discord"]["notify_interval_minutes"]
TAG_PRESETS = config["booth"]["tag_presets"]
CURRENT_PRESET = config["booth"]["notify_preset"]

# --- 通知済み記録 ---
NOTIFIED_FILE = "notified_items.json"
if os.path.exists(NOTIFIED_FILE):
    with open(NOTIFIED_FILE, "r", encoding="utf-8") as f:
        notified_items = set(json.load(f))
else:
    notified_items = set()

# --- Bot本体 ---
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

current_preset_name = CURRENT_PRESET

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user}")
    notify_new_items.start()

# --- 検索処理 ---
def fetch_booth_items(include_tags, exclude_tags):
    query = " ".join(include_tags)
    url = f"https://booth.pm/ja/search/{query.replace(' ', '%20')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select(".item-card__link")
    results = []

    for item in items[:10]:  # 多めに取得してフィルタする
        link = "https://booth.pm" + item.get("href")
        title = item.get("aria-label", "商品")

        if any(ex in title for ex in exclude_tags):
            continue

        results.append((title, link))
        if len(results) >= 5:
            break

    return results

# --- 通知処理 ---
async def notify_booth_items(channel):
    global current_preset_name
    preset = TAG_PRESETS[current_preset_name]
    include = preset["include"]
    exclude = preset.get("exclude", [])

    results = fetch_booth_items(include, exclude)

    new_posts = []
    for title, link in results:
        if link not in notified_items:
            notified_items.add(link)
            new_posts.append(f"[{title}]({link})")

    if new_posts:
        await channel.send("🆕 新着BOOTHアイテム:\n" + "\n".join(new_posts))
        with open(NOTIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(notified_items), f, ensure_ascii=False, indent=2)

# --- 定期通知 ---
@tasks.loop(minutes=NOTIFY_INTERVAL)
async def notify_new_items():
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    if channel:
        await notify_booth_items(channel)

# --- /booth コマンド（検索）---
@tree.command(name="booth", description="タグ付きでBOOTHを検索します")
@app_commands.describe(keyword="検索キーワード")
async def booth(interaction: discord.Interaction, keyword: str):
    preset = TAG_PRESETS[current_preset_name]
    include = preset["include"]
    exclude = preset.get("exclude", [])
    full_query = [keyword] + include

    results = fetch_booth_items(full_query, exclude)
    if not results:
        await interaction.response.send_message("😢 商品が見つかりませんでした。")
    else:
        text = "\n".join([f"[{title}]({link})" for title, link in results])
        await interaction.response.send_message(f"🔍 検索結果:\n{text}")

# --- /boothnow コマンド（手動通知）---
@tree.command(name="boothnow", description="今すぐ通知対象の商品をチェックします")
async def boothnow(interaction: discord.Interaction):
    await interaction.response.defer()
    await notify_booth_items(interaction.channel)
    await interaction.followup.send("✅ 通知確認完了！")

# --- /boothtag コマンド（プリセット切替）---
@tree.command(name="boothtag", description="タグプリセットを切り替えます")
@app_commands.describe(preset="プリセット名（例: live2d, vrchat）")
async def boothtag(interaction: discord.Interaction, preset: str):
    global current_preset_name
    if preset not in TAG_PRESETS:
        await interaction.response.send_message("❌ 指定されたプリセットが存在しません。")
    else:
        current_preset_name = preset
        await interaction.response.send_message(f"✅ プリセットを `{preset}` に切り替えました。")

# --- /boothtags コマンド（現在のタグ表示）---
@tree.command(name="boothtags", description="現在のタグプリセットと内容を表示します")
async def boothtags(interaction: discord.Interaction):
    preset = TAG_PRESETS[current_preset_name]
    include = preset.get("include", [])
    exclude = preset.get("exclude", [])
    await interaction.response.send_message(
        f"🔖 現在のプリセット: `{current_preset_name}`\n"
        f"📌 含むタグ: {', '.join(include)}\n"
        f"🚫 除外タグ: {', '.join(exclude) if exclude else 'なし'}"
    )

# --- 起動 ---
client.run(TOKEN)
