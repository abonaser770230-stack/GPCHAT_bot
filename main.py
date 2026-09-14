import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("T5llT", url="https://t.me/T5llT")],
        [InlineKeyboardButton("SmartAI_Ar", url="https://t.me/SmartAI_Ar")]
    ]
    await update.message.reply_text("أهلا بك في بوت سهيل 🤖\nاشترك بالقنوات:", reply_markup=InlineKeyboardMarkup(keyboard))

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"وصلت: {update.message.text}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()

if __name__ == "__main__":
    main()
