import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5529009159"))

CHANNELS = ["@T5llT", "@SmartAI_Ar"]
BLOG_LINK = "https://sohailaegency.blogspot.com"

logging.basicConfig(level=logging.INFO)

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_sub(update, context):
        keyboard = [
            [InlineKeyboardButton("اشترك في T5llT", url="https://t.me/T5llT")],
            [InlineKeyboardButton("اشترك في SmartAI_Ar", url="https://t.me/SmartAI_Ar")],
            [InlineKeyboardButton("تأكيد الاشتراك ✅", callback_data="check")]
        ]
        await update.message.reply_text(
            f"⚠️ يجب الاشتراك في القنوات أولاً للدردشة مع سهيل\n\n📚 مدونة سهيل: {BLOG_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    await update.message.reply_text(f"أهلاً بك في بوت سهيل 🤖\n📚 {BLOG_LINK}\nارسل رسالتك الآن!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_sub(update, context):
        await start(update, context)
        return
    text = update.message.text
    await update.message.reply_text(f"رسالتك: {text}\n\nرد سهيل قريباً... 🚀\n{BLOG_LINK}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
