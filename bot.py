import discord
from discord import app_commands
from discord.ext import tasks
import yaml
import requests
from bs4 import BeautifulSoup
import json
import os

# 設定読み込み
with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

TOKEN = config["discord"]["token"]
NOTIFY_CHANNEL_ID = config["booth"].get("notify_channel_id")
NOTIFY_INTERVAL = config["booth"].get("notify_interval_minutes", 60)
DEFAULT_TAGS = config["booth"].get("default_tags", [])

# 通知済みファイル
NOTIFIED_FILE = "notified_items.json"
if os.path.exists(NOTIFIED_FILE):
    with open(NOTIFIED_FILE, "r", encoding="utf-8") as f:
        notified_items = set(json.load(f))
else:
    notified_items = set()

user_defined_tags = DEFAULT_TAGS.copy()

# Bot本体
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user}")
    notify_new_items.start()

# 商品検索処理
def fetch_booth_items(query):
    url = f"https://booth.pm/ja/search/{query.replace(' ', '%20')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select(".item-card__link")
    results = []
    for item in items[:5]:
        link = "https://booth.pm" + item.get("href")
        title = item.get("aria-label", "商品")
        results.append((title, link))
    return results

# 通知送信処理
async def notify_booth_items(channel):
    keyword = " ".join(user_defined_tags)
    results = fetch_booth_items(keyword)

    new_posts = []
    for title, link in results:
        if link not in notified_items:
            notified_items.add(link)
            new_posts.append(f"[{title}]({link})")

    if new_posts:
        await channel.send("🆕 新着BOOTHアイテム:\n" + "\n".join(new_posts))
        with open(NOTIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(notified_items), f, ensure_ascii=False, indent=2)

# 定期通知
@tasks.loop(minutes=NOTIFY_INTERVAL)
async def notify_new_items():
    if NOTIFY_CHANNEL_ID is None:
        return
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    if channel:
        await notify_booth_items(channel)

# スラッシュコマンド: /booth
@tree.command(name="booth", description="BOOTHでキーワード検索")
@app_commands.describe(keyword="検索キーワード")
async def booth(interaction: discord.Interaction, keyword: str):
    query = f"{keyword} {' '.join(user_defined_tags)}"
    await interaction.response.defer()
    results = fetch_booth_items(query)
    if not results:
        await interaction.followup.send("😢 見つかりませんでした。")
    else:
        text = "\n".join([f"[{title}]({url})" for title, url in results])
        await interaction.followup.send(f"🔍 検索結果:\n{text}")

# スラッシュコマンド: /boothtag
@tree.command(name="boothtag", description="通知対象タグを設定する")
@app_commands.describe(tags="スペース区切りでタグを入力（例: Live2D VRChat）")
async def boothtag(interaction: discord.Interaction, tags: str):
    global user_defined_tags
    user_defined_tags = tags.split()
    await interaction.response.send_message(f"✅ 通知タグを更新: {', '.join(user_defined_tags)}")

# スラッシュコマンド: /boothtags
@tree.command(name="boothtags", description="現在の通知タグを表示")
async def boothtags(interaction: discord.Interaction):
    await interaction.response.send_message(f"🔖 現在の通知タグ: {', '.join(user_defined_tags)}")

# スラッシュコマンド: /boothnow
@tree.command(name="boothnow", description="手動で通知チェックを実行")
async def boothnow(interaction: discord.Interaction):
    await interaction.response.defer()
    await notify_booth_items(interaction.channel)
    await interaction.followup.send("✅ 通知を確認しました。")

# 起動
client.run(TOKEN)
