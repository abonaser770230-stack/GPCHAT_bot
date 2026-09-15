import os
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import AsyncOpenAI

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL_USERNAME", "@botchat_ar")
BLOG_URL = os.getenv("BLOG_URL", "https://t.me/")
GROQ_KEY = os.getenv("GROQ_API_KEY")

client = AsyncOpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_KEY else None

async def is_subscribed(user_id, context):
    try:
        m = await context.bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member","administrator","creator"]
    except: return True

def kb():
    b=[]
    b.append([InlineKeyboardButton("📢 اشترك", url=f"https://t.me/{CHANNEL.replace('@','')}")])
    b.append([InlineKeyboardButton("✅ تحقق", callback_data="check")])
    b.append([InlineKeyboardButton("📝 المدونة", url=BLOG_URL)])
    return InlineKeyboardMarkup(b)

async def start(update, context):
    if not await is_subscribed(update.effective_user.id, context):
        await update.message.reply_text("⚠️ اشترك أولاً لاستخدام البوت", reply_markup=kb())
        return
    await update.message.reply_text("✅ البوت شغال بكل اللغات 🌍\nارسل أي شيء!")

async def btn(update, context):
    q=update.callback_query; await q.answer()
    if await is_subscribed(q.from_user.id, context):
        await q.edit_message_text("✅ تم التحقق! ارسل سؤالك الآن")
    else:
        await q.answer("❌ ما اشتركت", show_alert=True)

async def chat(update, context):
    if not await is_subscribed(update.effective_user.id, context):
        await update.message.reply_text("⚠️ اشترك أولاً", reply_markup=kb()); return
    txt=update.message.text
    if "ساعة" in txt or "صنعاء" in txt:
        now=datetime.now(pytz.timezone('Asia/Aden'))
        await update.message.reply_text(f"🕒 صنعاء: {now.strftime('%I:%M %p')}")
        return
    if client:
        await context.bot.send_chat_action(update.effective_chat.id, "typing")
        r=await client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"Reply in same language as user"},{"role":"user","content":txt}])
        await update.message.reply_text(r.choices[0].message.content)
    else:
        await update.message.reply_text("ضيف GROQ_API_KEY ليرد ذكاء اصطناعي")

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling(drop_pending_updates=True)
if __name__=="__main__": main()
