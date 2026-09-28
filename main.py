import os, json, asyncio, requests
from datetime import datetime, date
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus

# جلب المتغيرات من البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API = os.getenv("GROQ_API")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
BOT_CHANNEL_URL = os.getenv("BOT_CHANNEL_URL", "https://t.me")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Gotchat_bot") 

# تهيئة عميل Groq
client = Groq(api_key=GROQ_API) if GROQ_API else None
DB_FILE = "database.json"

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except:
        return {"users": {}, "points": {}, "banned": [], "lang": {}, "daily": {}, "referrals": {}, "invited_by": {}}

def save_db(d):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)

db = load_db()
memory = {}  # لحفظ سياق المحادثة لكل مستخدم
SYSTEM_PROMPT = "You are Gotchat Bot. Creator Abu Naser. Bilingual AR/EN. Helpful like Meta AI."

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

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_ID: return True
    try:
        m = await context.bot.get_chat_member(CHANNEL_ID, update.effective_user.id)
        return m.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        print(f"Error checking sub: {e}")
        return True

async def notify_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    if "users" not in db: db["users"] = {}
    is_new = uid not in db["users"]
    if is_new:
        lang = get_user_lang(update)
        username = f"@{user.username}" if user.username else "بدون يوزر"
        db["users"][uid] = {"name": user.first_name, "username": username, "joined": str(datetime.now()), "lang": lang}
        if "points" not in db: db["points"] = {}
        db["points"][uid] = float('inf') if user.id == ADMIN_ID else 30
        if "lang" not in db: db["lang"] = {}
        db["lang"][uid] = lang

        # نظام الدعوة عبر الرابط
        if context.args and len(context.args) > 0:
            ref_arg = context.args[0]
            if ref_arg.startswith("ref_"):
                inviter_id = ref_arg.replace("ref_", "")
                if inviter_id != uid and inviter_id in db["users"] and uid not in db.get("invited_by", {}):
                    if "invited_by" not in db: db["invited_by"] = {}
                    if "referrals" not in db: db["referrals"] = {}
                    db["invited_by"][uid] = inviter_id
                    db["referrals"][inviter_id] = db["referrals"].get(inviter_id, 0) + 1
                    
                    if db["points"].get(inviter_id, 0) != float('inf'):
                        db["points"][inviter_id] = db["points"].get(inviter_id, 0) + 50
                    save_db(db)
                    try:
                        await context.bot.send_message(int(inviter_id), f"🎉 صديق جديد دخل من رابطك!\n👤 {user.first_name}\n💰 ربحت 50 نقطة! رصيدك الآن: {db['points'][inviter_id] if db['points'][inviter_id]!=float('inf') else '∞'}")
                    except: pass

        save_db(db)
        if ADMIN_ID and user.id != ADMIN_ID:
            pts = "∞" if db["points"][uid] == float('inf') else f"{db['points'][uid]}"
            msg = f"🔔 عضو جديد:\n👤 {user.first_name}\n🆔 `{uid}`\n{username}\n🌍 {lang}\n💰 {pts}"
            try: await context.bot.send_message(ADMIN_ID, msg, parse_mode=ParseMode.MARKDOWN)
            except: pass
    return is_new

async def handle_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member: return
    status = update.my_chat_member.new_chat_member.status
    user = update.my_chat_member.from_user
    if status in [ChatMemberStatus.BANNED, ChatMemberStatus.KICKED] and ADMIN_ID:
        try: await context.bot.send_message(ADMIN_ID, f"⛔ حظر البوت!\n👤 {user.first_name}\n🆔 `{user.id}`")
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_new_user(update, context)
    if not await check_sub(update, context):
        kb = [[InlineKeyboardButton("اشترك 🔔", url=f"https://t.me{CHANNEL_ID.replace('@','')}")],
              [InlineKeyboardButton("✅ تحققت", callback_data="check_sub")]]
        await update.message.reply_text(f"اشترك في {CHANNEL_ID} أولاً", reply_markup=InlineKeyboardMarkup(kb))
        return
    lang = get_user_lang(update)
    uid = str(update.effective_user.id)
    pts = db.get("points", {}).get(uid, 0)
    if lang=="en":
        txt = f"Hello {update.effective_user.first_name}! 🚀\nBalance: {'∞ Unlimited 👑' if pts==float('inf') else f'{pts} pts'}"
    else:
        txt = f"هلا {update.effective_user.first_name}! 🚀\n{'👑 أدمن - نقاطك ∞' if pts==float('inf') else f'رصيدك: {pts} نقطة'}"
    await update.message.reply_text(txt, reply_markup=get_keyboard(update.effective_user.id, lang))

async def daily_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(update)
    today = str(date.today())
    last = db.get("daily", {}).get(uid, "")

    if last == today:
        await update.message.reply_text("❌ استلمت هديتك اليوم! تعال بكرة 🎁" if lang=="ar" else "❌ You already claimed today! Come back tomorrow 🎁")
        return

    if "daily" not in db: db["daily"] = {}
    db["daily"][uid] = today
    if db["points"].get(uid, 0) != float('inf'):
        db["points"][uid] = db["points"].get(uid, 0) + 5
    save_db(db)
    await update.message.reply_text(f"🎁 مبروك! استلمت 5 نقاط هدية يومية!\n💰 رصيدك الآن: {db['points'][uid] if db['points'][uid]!=float('inf') else '∞'}" if lang=="ar" else f"🎁 You got 5 daily points!\n💰 Balance: {db['points'][uid]}")

async def invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(update)
    link = f"https://t.me{BOT_USERNAME}?start=ref_{uid}"
    refs = db.get("referrals", {}).get(uid, 0)

    if lang=="ar":
        txt = f"🔗 **رابط الدعوة الخاص بك:**\n`{link}`\n\n👥 دعوت: {refs} شخص\n💰 تربح 50 نقطة عن كل صديق يدخل من رابطك!\n\nشارك الرابط الآن 👇"
    else:
        txt = f"🔗 **Your invite link:**\n`{link}`\n\n👥 Invited: {refs}\n💰 Earn 50 points per friend!"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📤 مشاركة الرابط" if lang=="ar" else "📤 Share Link", switch_inline_query=f"جرب هذا البوت الرهيب! {link}")]])
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# === ميزات لوحة تحكم الأدمن (قيمة مضافة) ===
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    if uid != ADMIN_ID: return False

    if text in ["الإحصائيات 📊", "Stats 📊"]:
        total_users = len(db.get("users", {}))
        await update.message.reply_text(f"📊 إحصائيات البوت:\n👥 إجمالي المستخدمين: {total_users}")
        return True

    elif text in ["إذاعة 📢", "Broadcast 📢"]:
        context.user_data["action"] = "broadcast"
        await update.message.reply_text("📢 أرسل الآن الرسالة (نص فقط) التي تريد إذاعتها لجميع الأعضاء:")
        return True

    elif text in ["نقاط لعضو ➕", "Add Points ➕"]:
        context.user_data["action"] = "add_points"
        await update.message.reply_text("➕ أرسل آيدي العضو والشرطة ثم عدد النقاط.\nمثال: `12345678-100`", parse_mode=ParseMode.MARKDOWN)
        return True

    return False

# === معالجة الرسائل العادية والذكاء الاصطناعي مع Groq ===
async def handle_buttons_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)
    lang = get_user_lang(update)
    
    # 1. التحقق أولاً من أوامر الأدمن
    if update.effective_user.id == ADMIN_ID and await handle_admin(update, context):
        return

    # 2. متابعة خطوات مدخلات الأدمن (إذاعة أو إضافة نقاط)
    current_action = context.user_data.get("action")
    if current_action == "broadcast" and update.effective_user.id == ADMIN_ID:
        context.user_data["action"] = None
        users = list(db.get("users", {}).keys())
        await update.message.reply_text(f"🔄 جاري الإذاعة لـ {len(users)} عضو...")
        success = 0
        for u in users:
            try:
                await context.bot.send_message(int(u), text)
                success += 1
                                                              
