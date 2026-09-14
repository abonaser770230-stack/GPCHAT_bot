import os, json, sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) # ايدي حسابك من @userinfobot
CHANNEL = os.getenv("CHANNEL", "") # مثال @gpchat_channel بدون @

# قاعدة بيانات بسيطة
con = sqlite3.connect("bot.db", check_same_thread=False)
con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, joined TEXT)")
con.execute("CREATE TABLE IF NOT EXISTS blogs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, date TEXT)")

async def check_sub(update: Update):
    if not CHANNEL: return True
    try:
        member = await update.effective_user.get_chat_member(f"@{CHANNEL}" if not CHANNEL.startswith('@') else CHANNEL) if False else await update.get_bot().get_chat_member(f"@{CHANNEL}", update.effective_user.id)
        return member.status not in ['left', 'kicked']
    except:
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    con.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, datetime.now().isoformat()))
    con.commit()

    # فحص الاشتراك
    if CHANNEL:
        try:
            m = await context.bot.get_chat_member(f"@{CHANNEL}", uid)
            if m.status in ['left', 'kicked']:
                kb = [[InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{CHANNEL}")],
                      [InlineKeyboardButton("✅ تأكدت من الاشتراك", callback_data="check_sub")]]
                await update.message.reply_text(f"👋 اهلاً {update.effective_user.first_name}\n\nيجب الاشتراك في قناتنا أولاً لاستخدام البوت:", reply_markup=InlineKeyboardMarkup(kb))
                return
        except: pass

    kb = [[InlineKeyboardButton("📝 المدونة", callback_data="blogs"), InlineKeyboardButton("👤 حسابي", callback_data="me")]]
    await update.message.reply_text(f"🤖 أهلاً {update.effective_user.first_name}!\n\nأنا بوت ذكي سريع مثل ChatGPT\n\n/bot - تحدث معي\n/blog - المدونة\n/help - المساعدة", reply_markup=InlineKeyboardMarkup(kb))

async def handle_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "check_sub":
        try:
            m = await context.bot.get_chat_member(f"@{CHANNEL}", q.from_user.id)
            if m.status not in ['left', 'kicked']:
                await q.edit_message_text("✅ تم تأكيد اشتراكك! ارسل /start")
            else:
                await q.answer("❌ لم تشترك بعد", show_alert=True)
        except:
            await q.edit_message_text("✅ اهلاً بك! ارسل /start")
    elif q.data == "blogs":
        cur = con.execute("SELECT id, title FROM blogs ORDER BY id DESC LIMIT 10").fetchall()
        if not cur:
            await q.edit_message_text("📭 لا يوجد مقالات بعد")
        else:
            text = "📝 **آخر المقالات:**\n\n"
            for i, t in cur: text += f"{i}. {t}\n"
            text += "\nارسل رقم المقال لقراءته"
            await q.edit_message_text(text)
    elif q.data == "me":
        count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        await q.edit_message_text(f"👤 ايديك: {q.from_user.id}\n👥 عدد المستخدمين: {count}")

async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # رد ذكي سريع يشبهني
    text = update.message.text
    if text.startswith('/'): return
    reply = f"💡 فهمت سؤالك: \"{text}\"\n\nهذا رد ذكي وسريع من البوت المطور بأحدث اصدار. يمكنك تطويره لربطه بـ OpenAI API لاحقاً.\n\nاكتب /blog لرؤية المدونة."
    await update.message.reply_text(reply)

async def blog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = con.execute("SELECT title, content FROM blogs ORDER BY id DESC").fetchall()
    if not cur:
        await update.message.reply_text("📭 المدونة فاضية، الادمن يقدر يضيف مقال بـ /addblog عنوان | محتوى")
    else:
        for t, c in cur[:5]:
            await update.message.reply_text(f"📰 **{t}**\n\n{c}\n\n— {datetime.now().date()}")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية ادمن")
        return
    count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await update.message.reply_text(f"👑 **لوحة الادمن**\n\n👥 المستخدمين: {count}\n\n/addblog عنوان | محتوى - اضافة مقال\n/broadcast رسالة - اذاعة للكل\n/stats - الاحصائيات")

async def addblog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        _, data = update.message.text.split(' ', 1)
        title, content = data.split('|', 1)
        con.execute("INSERT INTO blogs (title, content, date) VALUES (?,?,?)", (title.strip(), content.strip(), datetime.now().isoformat()))
        con.commit()
        await update.message.reply_text(f"✅ تم نشر: {title}")
    except:
        await update.message.reply_text("❌ الصيغة: /addblog العنوان | المحتوى")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        msg = update.message.text.split(' ', 1)[1]
        users = con.execute("SELECT id FROM users").fetchall()
        sent = 0
        for (uid,) in users:
            try:
                await context.bot.send_message(uid, f"📢 **اذاعة:**\n\n{msg}")
                sent+=1
            except: pass
        await update.message.reply_text(f"✅ تم الارسال لـ {sent}")
    except:
        await update.message.reply_text("❌ /broadcast نص الرسالة")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addblog", addblog))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("blog", blog_cmd))
    app.add_handler(CommandHandler("stats", admin))
    app.add_handler(CallbackQueryHandler(handle_check))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))
    print("🚀 Bot Started Ultra Fast")
    app.run_polling()

if __name__ == "__main__":
    main()
