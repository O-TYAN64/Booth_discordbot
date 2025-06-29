# 🛍️ Discord BOOTH 通知BOT

このBOTは、BOOTHで新着された商品を定期的に検索し、Discordに自動通知するBOTです。  
キーワード検索、タグ変更、除外済みアイテムの記録機能に対応。手動通知や現在の通知タグ確認も可能です。

---

## ✨ 機能概要

| 機能      | コマンド                            | 説明                        |
| ------- | ------------------------------- | ------------------------- |
| 🔍 検索   | `/booth keyword: ネコミミ`          | 通知タグを付加してBOOTH検索（除外タグも適用） |
| 🔁 手動通知 | `/boothnow`                     | 現時点の新着商品（通知タグ）を今すぐ通知      |
| ✅ タグ設定  | `/boothtag tags: Live2D VRChat` | 検索・通知に含めるタグを設定（スペース区切り）   |
| 📋 タグ確認 | `/boothtags`                    | 現在の通知タグを表示                |
| 🚫 除外設定 | `/boothignoretag tags: R-18`    | タイトルに含むと通知・検索から除外するワードを設定 |
| 📋 除外確認 | `/boothignoretags`              | 現在の除外ワードを表示               |


---

## 🔧 インストール方法

### 1. 必要ライブラリをインストール

```bash
pip install discord.py requests beautifulsoup4 pyyaml
