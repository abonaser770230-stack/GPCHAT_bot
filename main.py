import os, logging, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from groq import Groq

logging.basicConfig(level=logging.INFO)

# جلب المفاتيح من متغيرات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

async def reply_ai(update: Update, context):
    if not update.message or not update.message.text: return
    text = update.message.text.strip()

    if not client:
        return await update.message.reply_text("❌ مفتاح GROQ_API_KEY غير موجود في متغيرات البيئة!")

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        # استخدام موديل Groq المعتمد
        loop = asyncio.get_event_loop()
        comp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي تجيب باختصار وباللغة العربية."},
                    {"role": "user", "content": text}
                ],
                temperature=0.7
            )
        )
        reply = comp.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Error: {e}")
        # إرسال نص الخطأ بالتفصيل للدردشة لتحديد المشكلة فوراً
        await update.message.reply_text(f"❌ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي:\n\n`{str(e)}`", parse_mode="Markdown")

def main():
    if not BOT_TOKEN:
        print("❌ لم يتم العثور على BOT_TOKEN!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_ai))
    print("🤖 البوت التجريبي يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
