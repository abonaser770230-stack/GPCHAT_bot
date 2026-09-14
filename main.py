import os, sqlite3, feedparser
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5529009159"))
CHANNELS = ["T5llT", "SmartAI_Ar"]
BLOG_RSS = "https://sohailaegency.blogspot.com/feeds/posts/default"

con = sqlite3.connect("bot.db", check_same_thread=False)
con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")

async def is_sub(bot, uid):
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{ch}", uid)
            if m.status in ['left','kicked']: return False
        except: continue
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con.execute("INSERT OR IGNORE INTO users VALUES (?)", (update.effective_user.id,))
    con.commit()
    if not await is_sub(context.bot, update.effective_user.id):
        kb = [
            [InlineKeyboardButton("اشترك @T5llT 📢", url="https://t.me/T5llT")],
            [InlineKeyboardButton("اشترك @SmartAI_Ar 🤖", url="https://t.me/SmartAI_Ar")],
            [InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check")]
        ]
        await update.message.reply_text("⚠️ يجب الاشتراك في قنوات سهيل أولاً:", reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = [[InlineKeyboardButton("📰 مدونة سهيل", callback_data="blog")]]
    await update.message.reply_text(f"أهلاً {update.effective_user.first_name} 🤖\nبوت سهيل أجينسي شغال\n\n/blog - المقالات", reply_markup=InlineKeyboardMarkup(kb))

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "check":
        if await is_sub(context.bot, q.from_user.id):
            await q.edit_message_text("✅ تم التفعيل! ارسل /start")
        else:
            await q.answer("❌ اشترك في القناتين أولاً", show_alert=True)
    elif q.data == "blog":
        feed = feedparser.parse(BLOG_RSS)
        if not feed.entries:
            await q.edit_message_text("📭 لا يوجد مقالات بعد")
            return
        text = "📰 آخر مقالات سهيل أجينسي:\n\n"
        for e in feed.entries[:3]:
            text += f"🔹 {e.title}\n{e.link}\n\n"
        await q.edit_message_text(text, disable_web_page_preview=True)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_sub(context.bot, update.effective_user.id):
        return await start(update, context)
    await update.message.reply_text(f"سؤالك: {update.message.text}\n\nشوف مدونة سهيل: sohailaegency.blogspot.com")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    c = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await update.message.reply_text(f"👑 ادمن سهيل\n👥 {c} مستخدم\n/broadcast رسالة")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        msg = update.message.text.split(' ',1)[1]
        for (uid,) in con.execute("SELECT id FROM users").fetchall():
            try: await context.bot.send_message(uid, f"📢 {msg}\n\nsohailaegency.blogspot.com")
            except: pass
        await update.message.reply_text("✅ تم")
    except:
        await update.message.reply_text("/broadcast النص")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Bot Running")
    app.run_polling()

if __name__ == "__main__":
    main()
