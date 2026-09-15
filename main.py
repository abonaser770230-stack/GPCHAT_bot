import os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import AsyncOpenAI

TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") or "gsk_Qoue63WyWGdyb3FYuXX1XPisy5IZnvUROfzp3Cyp"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

FINANCE_CHANNEL_URL = "https://t.me/SmartAI_Ar"
BOTS_CHANNEL_URL = "https://t.me/FFZZ5"
FINANCE_ACCOUNT = "@shph711"
BLOG_URL = "https://sohailaegency.blogspot.com/"

USERS_FILE = "users.json"
client = AsyncOpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")

def load():
    try:
        with open(USERS_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}
def save(data):
    with open(USERS_FILE,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False)

def get_user(uid):
    db=load()
    uid=str(uid)
    if uid not in db:
        db[uid]={"points":1, "q_left":25, "invited":0}
        save(db)
    return db[uid]

def is_admin(uid): return int(uid)==ADMIN_ID

def user_menu():
    return ReplyKeyboardMarkup([
        ["🚀 ستارت", "📝 المدونة"],
        ["💎 نقاطي", "💰 تمويل أعضاء"],
        ["🤖 بوتاتنا", "📢 قناة التمويل"]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup([
        ["بوتاتنا", "إذاعة"],
        ["➕ نقاط لعضو", "📊 الإحصائيات"],
        ["💎 نقاطي", "🚀 ستارت"]
    ], resize_keyboard=True)

async def setup_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "1- ستارت"),
        BotCommand("blog", "2- المدونة"),
        BotCommand("finance", "3- تمويل أعضاء"),
        BotCommand("bots", "4- بوتاتنا"),
        BotCommand("channel", "5- قناة التمويل"),
        BotCommand("points", "نقاطي"),
    ])

async def start(update, ctx):
    uid=update.effective_user.id
    args=ctx.args
    db=load()
    is_new=str(uid) not in db
    user_data=get_user(uid)

    # نظام الدعوة
    if args and args[0].startswith("ref_"):
        try:
            ref_id=args[0].split("_")[1]
            if ref_id!=str(uid) and is_new and ref_id in db:
                db[ref_id]["points"]+=1
                db[ref_id]["q_left"]+=25
                db[ref_id]["invited"]+=1
                save(db)
                try: await ctx.bot.send_message(int(ref_id), f"🎉 عضو جديد دخل برابطك!\n+1 نقطة = +25 سؤال\nنقاطك الآن: {db[ref_id]['points']}")
                except: pass
        except: pass

    if is_new and ADMIN_ID:
        try: await ctx.bot.send_message(ADMIN_ID, f"🔔 عضو جديد:\n👤 {update.effective_user.full_name}\n🆔 `{uid}`\n@{update.effective_user.username}\n🌍 {update.effective_user.language_code}", parse_mode="Markdown")
        except: pass

    if is_admin(uid):
        await update.message.reply_text(f"👑 أدمن - نقاطك ♾️ غير محدودة", reply_markup=admin_menu())
    else:
        bot_username=(await ctx.bot.get_me()).username
        ref_link=f"https://t.me/{bot_username}?start=ref_{uid}"
        await update.message.reply_text(
            f"✅ أهلاً {update.effective_user.first_name}\n\n💎 نقاطك: {user_data['points']}\n💬 أسئلة متبقية: {user_data['q_left']}\n\n🔗 رابط دعوتك:\n{ref_link}\nكل دعوة = +1 نقطة",
            reply_markup=user_menu()
        )

async def handler(update, ctx):
    txt=update.message.text; uid=update.effective_user.id
    db=load()
    user_data=get_user(uid)

    # أدمن - تحويل نقاط
    if is_admin(uid):
        if txt=="➕ نقاط لعضو":
            ctx.user_data["mode"]="add_points"
            await update.message.reply_text("أرسل بهذا الشكل:\n`123456789 5`\nيعني ايدي الشخص + عدد النقاط", parse_mode="Markdown"); return
        if ctx.user_data.get("mode")=="add_points":
            try:
                parts=txt.split()
                target_id=str(parts[0]); amount=int(parts[1])
                if target_id not in db: db[target_id]={"points":0,"q_left":0,"invited":0}
                db[target_id]["points"]+=amount
                db[target_id]["q_left"]+=amount*25
                save(db)
                ctx.user_data["mode"]=None
                await update.message.reply_text(f"✅ تم تحويل {amount} نقطة لـ {target_id}\nأسئلته الآن: {db[target_id]['q_left']}", reply_markup=admin_menu())
                try: await ctx.bot.send_message(int(target_id), f"🎁 الأدمن أضاف لك {amount} نقطة = {amount*25} سؤال!\nنقاطك: {db[target_id]['points']}")
                except: pass
            except: await update.message.reply_text("❌ خطأ، أرسل: ايدي + عدد\nمثال: 123456 2")
            return
        if txt=="📊 الإحصائيات":
            await update.message.reply_text(f"👥 المستخدمين: {len(db)}"); return
        if txt=="إذاعة":
            ctx.user_data["mode"]="broad"; await update.message.reply_text("أرسل رسالة الإذاعة"); return
        if ctx.user_data.get("mode")=="broad":
            c=0
            for tid in db:
                try: await ctx.bot.copy_message(int(tid), uid, update.message.message_id); c+=1
                except: pass
            ctx.user_data["mode"]=None
            await update.message.reply_text(f"✅ إذاعة لـ {c}", reply_markup=admin_menu()); return

    # قائمة المستخدمين
    if txt in ["🚀 ستارت","/start"]:
        await start(update, ctx); return
    if txt in ["📝 المدونة","/blog"]:
        await update.message.reply_text(f"📝 مدونة سهيل:\n{BLOG_URL}"); return
    if txt in ["💰 تمويل أعضاء","/finance"]:
        await update.message.reply_text(f"💰 تمويل أعضاء\nراسل {FINANCE_ACCOUNT}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 حساب التمويل", url=f"https://t.me/{FINANCE_ACCOUNT.replace('@','')}")],[InlineKeyboardButton("📢 قناة التمويل", url=FINANCE_CHANNEL_URL)]])); return
    if txt in ["🤖 بوتاتنا","/bots","بوتاتنا"]:
        await update.message.reply_text(f"🤖 بوتاتنا:\n{BOTS_CHANNEL_URL}"); return
    if txt in ["📢 قناة التمويل","/channel"]:
        await update.message.reply_text(f"📢 قناة التمويل:\n{FINANCE_CHANNEL_URL} (رسالة فقط)"); return
    if txt in ["💎 نقاطي","/points"]:
        if is_admin(uid):
            await update.message.reply_text("♾️ نقاطك غير محدودة كأدمن"); return
        bot_username=(await ctx.bot.get_me()).username
        ref_link=f"https://t.me/{bot_username}?start=ref_{uid}"
        await update.message.reply_text(
            f"💎 **نقاطك:** {user_data['points']}\n💬 **المتبقي:** {user_data['q_left']} سؤال\n👥 **دعوت:** {user_data['invited']} عضو\n\n🔗 **رابطك:**\n{ref_link}\n\nكل عضو = +1 نقطة (25 سؤال)\nخلصت نقاطك؟ راسل {FINANCE_ACCOUNT}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 طلب نقاط", url=f"https://t.me/{FINANCE_ACCOUNT.replace('@','')}")]]), parse_mode="Markdown"
        ); return

    # --- ذكاء اصطناعي + خصم نقاط ---
    if not is_admin(uid):
        if user_data["q_left"]<=0:
            bot_username=(await ctx.bot.get_me()).username
            ref_link=f"https://t.me/{bot_username}?start=ref_{uid}"
            await update.message.reply_text(
                f"❌ **انتهت أسئلتك!**\n\n💎 نقاطك: {user_data['points']}\n\nللحصول على نقاط:\n1️⃣ ادعو عضو: {ref_link}\n2️⃣ راسل {FINANCE_ACCOUNT}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 طلب نقاط", url=f"https://t.me/{FINANCE_ACCOUNT.replace('@','')}")]])
            ); return
        # خصم سؤال
        db[str(uid)]["q_left"]-=1
        save(db)

    await ctx.bot.send_chat_action(uid, "typing")
    r=await client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"Reply same language"},{"role":"user","content":txt}])
    await update.message.reply_text(r.choices[0].message.content + (f"\n\n💬 متبقي: {db[str(uid)]['q_left']} سؤال" if not is_admin(uid) else ""), reply_markup=admin_menu() if is_admin(uid) else user_menu())

def main():
    app=Application.builder().token(TOKEN).build()
    app.post_init=setup_commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handler))
    app.run_polling(drop_pending_updates=True)
if __name__=="__main__": main()
