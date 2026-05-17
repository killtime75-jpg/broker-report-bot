import discord
import os
import re
import json
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash-8b")
    GEMINI_OK = True
except Exception as e:
    print(f"Gemini init error: {e}")
    GEMINI_OK = False

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

reports_db = {}

def analyze_report(text):
    if not GEMINI_OK:
        return "Gemini API 未初始化"
    prompt = f"""你是專業的台股券商報告分析師。分析以下報告並用繁體中文回覆：

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

STOCK_CODE:XXXX

報告內容：
{text[:3000]}"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"分析失敗：{str(e)}"

def extract_stock_code(text):
    match = re.search(r'STOCK_CODE:(\d{4,6})', text)
    if match:
        return match.group(1)
    match = re.search(r'\b(\d{4})\b', text)
    if match:
        return match.group(1)
    return None

@client.event
async def on_ready():
    print(f"Bot 上線：{client.user} (ID: {client.user.id})")
    print("------")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    
    if not content:
        return

    if content.startswith("查詢") or content.startswith("/查詢"):
        stock_code = content.replace("查詢", "").replace("/查詢", "").strip()
        if stock_code and stock_code in reports_db:
            reports = reports_db[stock_code]
            await message.channel.send(f"📁 **{stock_code}** 共 {len(reports)} 份報告：")
            for i, r in enumerate(reports[-5:], 1):
                summary = r['summary'][:400] + "..." if len(r['summary']) > 400 else r['summary']
                await message.channel.send(f"**第{i}份** ({r['date']})\n{summary}")
        else:
            await message.channel.send(f"❌ 找不到股號 **{stock_code}** 的報告")
        return

    if content in ["!help", "幫助", "/幫助", "help"]:
        await message.channel.send("""**📖 使用說明**

**新增報告**：直接貼上券商報告文字（超過50字會自動分析）

**查詢報告**：輸入 `查詢 2330` 查詢所有相關報告""")
        return

    if len(content) > 50:
        thinking_msg = await message.channel.send("🔍 分析中，請稍候...")
        try:
            summary = analyze_report(content)
            stock_code = extract_stock_code(summary)
            
            clean_summary = summary.replace("STOCK_CODE:" + (stock_code or ""), "").strip()

            if stock_code:
                if stock_code not in reports_db:
                    reports_db[stock_code] = []
                reports_db[stock_code].append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "summary": clean_summary,
                    "author": str(message.author)
                })

            await thinking_msg.delete()
            
            if len(clean_summary) > 1900:
                parts = [clean_summary[i:i+1900] for i in range(0, len(clean_summary), 1900)]
                for part in parts:
                    await message.channel.send(part)
            else:
                await message.channel.send(clean_summary)

            if stock_code:
                count = len(reports_db[stock_code])
                await message.channel.send(f"✅ 已儲存！輸入 `查詢 {stock_code}` 可查看全部 {count} 份報告")

        except Exception as e:
            await thinking_msg.delete()
            await message.channel.send(f"❌ 發生錯誤：{str(e)}")

if not DISCORD_TOKEN:
    print("錯誤：找不到 DISCORD_TOKEN")
else:
    client.run(DISCORD_TOKEN)
