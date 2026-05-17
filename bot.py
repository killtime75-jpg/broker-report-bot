import discord
import google.generativeai as genai
import os
import json
import re
from datetime import datetime

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

reports_db = {}

def analyze_report(text):
    prompt = f"""你是專業的台股券商報告分析師。分析以下報告並用繁體中文回覆，格式如下：

📊 **股票**：股號 股名
🏦 **券商**：券商名稱
⭐ **評等**：買進/中立/賣出
🎯 **目標價**：NT$XXXX
📅 **日期**：報告日期

📋 **重點摘要**
（3-5句重點）

🔑 **投資亮點**
1. 
2. 
3. 

⚠️ **主要風險**
（一句話）

---
股號（只回覆數字，例如2330）：{{stock_code}}

報告內容：
{text}

注意：最後一行請單獨只寫股號數字，格式為「股號：XXXX」"""

    response = model.generate_content(prompt)
    return response.text

def extract_stock_code(text):
    match = re.search(r'股號[：:]\s*(\d{4,6})', text)
    if match:
        return match.group(1)
    match = re.search(r'\b(\d{4})\b', text)
    if match:
        return match.group(1)
    return None

@client.event
async def on_ready():
    print(f"Bot 已上線：{client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    # 查詢指令
    if content.startswith("查詢") or content.startswith("/查詢"):
        stock_code = content.replace("查詢", "").replace("/查詢", "").strip()
        if stock_code in reports_db:
            reports = reports_db[stock_code]
            await message.channel.send(f"📁 找到 **{stock_code}** 共 {len(reports)} 份報告：")
            for i, r in enumerate(reports[-5:], 1):
                await message.channel.send(f"**第{i}份** ({r['date']})\n{r['summary'][:500]}...")
        else:
            await message.channel.send(f"❌ 找不到股號 **{stock_code}** 的報告，請先貼上報告讓我分析！")
        return

    # 幫助指令
    if content in ["!help", "幫助", "/幫助"]:
        help_text = """**📖 使用說明**
        
**新增報告**：直接貼上券商報告文字，我會自動分析摘要

**查詢報告**：輸入 `查詢 2330` 查詢台積電所有報告

**支援格式**：純文字報告內容"""
        await message.channel.send(help_text)
        return

    # 自動分析報告（超過100字才分析）
    if len(content) > 100:
        thinking_msg = await message.channel.send("🔍 正在分析券商報告，請稍候...")
        try:
            summary = analyze_report(content)
            stock_code = extract_stock_code(summary)

            if stock_code:
                if stock_code not in reports_db:
                    reports_db[stock_code] = []
                reports_db[stock_code].append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "summary": summary,
                    "author": str(message.author)
                })

            await thinking_msg.delete()
            await message.channel.send(summary)

            if stock_code:
                count = len(reports_db[stock_code])
                await message.channel.send(f"✅ 已儲存！輸入 `查詢 {stock_code}` 可查看全部 {count} 份報告")

        except Exception as e:
            await thinking_msg.delete()
            await message.channel.send(f"❌ 分析失敗，請重試。錯誤：{str(e)}")

client.run(DISCORD_TOKEN)
