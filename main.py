import os
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("❌ Variables ناقصة! ضيف API_ID و API_HASH و BOT_TOKEN في Railway")
    exit(1)

app = Client(
    "GPCHAT_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "✅ البوت شغال تمام!\n\n"
        "أهلاً بك في GPCHAT_bot 🚀\n"
        "أرسل /help للمساعدة"
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    await message.reply_text("🆘 هذا البوت شغال على Railway\nالكود جاهز للتطوير")

print("🚀 Bot is starting...")
app.run()
