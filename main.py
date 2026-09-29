import os, json, asyncio
from datetime import datetime, date
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API = os.getenv("GROQ_API")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@SmartAI_Ar")
BOT_CHANNEL_URL = os.getenv("BOT_CHANNEL_URL", "https://t.me/SmartAI_Ar")
BOT_USERNAME = os.getenv("BOT_USERNAME", "chatGP_1bot")

client = Groq(api_key=GROQ_API)

# بدون Volume - يحفظ بجانب البوت
DB_FILE = "database.json"
UNLIMITED = 999999

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}, "points": {}, "banned": [], "lang": {}, "daily": {}, "referrals": {}, "invited_by": {}}

def save_db(d):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

db = load_db()
memory = {}
SYSTEM_PROMPT = "You are Gotchat Bot. Creator Abu Naser. Bilingual AR/EN. Helpful."

def get_user_lang(update: Update):
    uid = str(update.effective_user.id)
    if uid in db.get("lang", {}): return db["lang"][uid]
    tg_lang = update.effective_user.language_code or "ar"
    return "en" if tg_lang.startswith("en") else "ar"

def get_keyboard(user_id, lang="ar"):
    is_admin = user_id == ADMIN_ID
    if lang == "en":
        user_buttons = [["Our Bots 🤖", "My Points 💎"], ["Daily Gift 🎁", "Invite Link 🔗"], ["Start 🚀"]]
        admin_buttons = [["Broadcast 📢", "Stats 📊"], ["Add Points ➕", "Our Bots 🤖"], ["My Points 💎", "Start 🚀"]]
    else:
        user_buttons = [["بوتاتنا 🤖", "نقاطي 💎"], ["هدية يومية 🎁", "رابط الدعوة 🔗"], ["ستارت 🚀"]]
        admin_buttons = [["إذاعة 📢", "الإحصائيات 📊"], ["نقاط لعضو ➕", "بوتاتنا 🤖"], ["نقاطي 💎", "ستارت 🚀"]]
    buttons = admin_buttons if is_admin else user_buttons
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, is_persistent=True)

def get_channel_inline(lang="ar"):
    text = "📢 قناة البوت - افتح مباشرة 🚀" if lang=="ar" else "📢 Bot Channel - Open 🚀"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, url=BOT_CHANNEL_URL)]])

async def check_sub(update: Update):
    if not CHANNEL_ID: return True
    try:
        m = await update.get_bot().get_chat_member(CHANNEL_ID, update.effective_user.id)
        return m.status in ["member", "administrator", "creator"]
    except: return True

async def notify_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    is_new = uid not in db["users"]
    if is_new:
        lang = get_user_lang(update)
        username = f"@{user.username}" if user.username else "بدون يوزر"
        db["users"][uid] = {"name": user.first_name, "username": username, "joined": str(datetime.now()), "lang": lang}
        db["points"][uid] = UNLIMITED if user.id == ADMIN_ID else 30
        if "lang" not in db: db["lang"] = {}
        db["lang"][uid] = lang
        if context.args and len(context.args) > 0:
            ref_arg = context.args[0]
            if ref_arg.startswith("ref_"):
                inviter_id = ref_arg.replace("ref_", "")
                if inviter_id!= uid and inviter_id in db["users"] and uid not in db.get("invited_by", {}):
                    if "invited_by" not in db: db["invited_by"] = {}
                    if "referrals" not in db: db["referrals"] = {}
                    db["invited_by"][uid] = inviter_id
                    db["referrals"][inviter_id] = db["referrals"].get(inviter_id, 0) + 1
                    if db["points"].get(inviter_id, 0)!= UNLIMITED:
                        db["points"][inviter_id] = db["points"].get(inviter_id, 0) + 50
                    save_db(db)
                    try:
                        await context.bot.send_message(int(inviter_id), f"🎉 صديق جديد دخل من رابطك!\n👤 {user.first_name}\n💰 ربحت 50 نقطة!")
                    except: pass
        save_db(db)
        if ADMIN_ID and user.id!= ADMIN_ID:
            try: await context.bot.send_message(ADMIN_ID, f"🔔 عضو جديد: {user.first_name}\n🆔 {uid}\n{username}")
            except: pass
    return is_new

async def handle_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.my_chat_member.new_chat_member.status
    user = update.my_chat_member.from_user
    if status in [ChatMemberStatus.BANNED, ChatMemberStatus.KICKED] and ADMIN_ID:
        try: await context.bot.send_message(ADMIN_ID, f"⛔ حظر البوت: {user.first_name} {user.id}")
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_new_user(update, context)
    if not await check_sub(update):
        kb = [[InlineKeyboardButton("اشترك 🔔", url=BOT_CHANNEL_URL)],
              [InlineKeyboardButton("✅ تحققت", callback_data="check_sub")]]
        await update.message.reply_text(f"اشترك في {CHANNEL_ID} أولاً", reply_markup=InlineKeyboardMarkup(kb))
        return
    lang = get_user_lang(update)
    uid = str(update.effective_user.id)
    pts = db["points"].get(uid, 0)
    if lang=="en":
        txt = f"Hello {update.effective_user.first_name}! 🚀\nBalance: {'∞ Unlimited 👑' if pts==UNLIMITED else f'{pts} pts'}"
    else:
        txt = f"هلا {update.effective_user.first_name}! 🚀\n{'👑 أدمن - نقاطك ∞' if pts==UNLIMITED else f'رصيدك: {pts} نقطة'}"
    await update.message.reply_text(txt, reply_markup=get_keyboard(update.effective_user.id, lang))
    await update.message.reply_text("👇", reply_markup=get_channel_inline(lang))

async def daily_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(update)
    today = str(date.today())
    last = db.get("daily", {}).get(uid, "")
    if last == today:
        await update.message.reply_text("❌ استلمت هديتك اليوم! تعال بكرة 🎁" if lang=="ar" else "❌ You already claimed today!")
        return
    if "daily" not in db: db["daily"] = {}
    db["daily"][uid] = today
    if db["points"].get(uid, 0)!= UNLIMITED:
        db["points"][uid] = db["points"].get(uid, 0) + 5
    save_db(db)
    await update.message.reply_text(f"🎁 مبروك! 5 نقاط هدية!\n💰 رصيدك: {'∞' if db['points'][uid]==UNLIMITED else db['points'][uid]}")

async def invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(update)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    refs = db.get("referrals", {}).get(uid, 0)
    if lang=="ar":
        txt = f"🔗 **رابط الدعوة الخاص بك:**\n`{link}`\n\n👥 دعوت: {refs} شخص\n💰 تربح 50 نقطة عن كل صديق!"
    else:
        txt = f"🔗 **Your invite link:**\n`{link}`\n\n👥 Invited: {refs}\n💰 Earn 50 points per friend!"
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def handle_buttons_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    lang = get_user_lang(update)
    is_admin = uid == ADMIN_ID
    if text in ["بوتاتنا 🤖", "Our Bots 🤖"]:
        await update.message.reply_text("🤖 بوتاتنا:\n@chatGP_1bot"); return
    elif text in ["نقاطي 💎", "My Points 💎"]:
        pts = db["points"].get(str(uid), 0)
        msg = "💎 ∞ غير محدودة 👑" if pts==UNLIMITED else f"💎 {pts} نقطة"
        await update.message.reply_text(msg); return
    elif text in ["ستارت 🚀", "Start 🚀"]:
        await start(update, context); return
    elif text in ["هدية يومية 🎁", "Daily Gift 🎁"]:
        await daily_gift(update, context); return
    elif text in ["رابط الدعوة 🔗", "Invite Link 🔗"]:
        await invite_link(update, context); return
    if text in ["إذاعة 📢", "Broadcast 📢"]:
        if not is_admin: return
        await update.message.reply_text("/broadcast رسالتك"); return
    elif text in ["الإحصائيات 📊", "Stats 📊"]:
        if not is_admin: return
        total_refs = sum(db.get("referrals", {}).values())
        await update.message.reply_text(f"📊 المستخدمين: {len(db['users'])}\n🔗 الدعوات: {total_refs}"); return
    elif text in ["نقاط لعضو ➕", "Add Points ➕"]:
        if not is_admin: return
        await update.message.reply_text("استخدم:\n/addpoints 123456 100"); return
    await handle_chat(update, context)

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        tid = context.args[0]; amt = int(context.args[1])
        db["points"][tid] = db["points"].get(tid, 0) + amt
        if db["points"][tid] >= UNLIMITED: db["points"][tid] = UNLIMITED
        save_db(db)
        await update.message.reply_text(f"تم ✅ إضافة {amt} لـ {tid}")
    except:
        await update.message.reply_text("الصح:\n/addpoints 6430848933 50")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if not context.args: await update.message.reply_text("/broadcast رسالتك"); return
    msg = " ".join(context.args); c=0
    for uid in db["users"]:
        try: await context.bot.send_message(int(uid), f"📢 {msg}"); c+=1; await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"تم الإرسال لـ {c} ✅")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id)
    if uid in db["banned"]: return
    pts=db["points"].get(uid,0)
    if pts!= UNLIMITED and pts <= 0:
        await update.message.reply_text("رصيدك خلص! 🎁 اطلب هدية يومية أو ادعُ صديق 🔗"); return
    user_id_int=update.effective_user.id
    if user_id_int not in memory: memory[user_id_int]=[]
    memory[user_id_int].append({"role":"user","content":update.message.text})
    if len(memory[user_id_int])>12: memory[user_id_int]=memory[user_id_int][-12:]
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        comp=client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":SYSTEM_PROMPT}]+memory[user_id_int], temperature=0.8, max_tokens=2000)
        reply=comp.choices[0].message.content
        memory[user_id_int].append({"role":"assistant","content":reply})
        if pts!= UNLIMITED: db["points"][uid]-=1; save_db(db)
        try: await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text(reply)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if q.data=="check_sub":
        if await check_sub(update): await q.message.delete(); await start(update, context)
        else: await q.answer("اشترك أولاً!", show_alert=True)

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addpoints", addpoints))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("daily", daily_gift))
    app.add_handler(CommandHandler("invite", invite_link))
    app.add_handler(ChatMemberHandler(handle_block, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons_text))
    print("V9.1 Railway No-Volume Running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__": main()
