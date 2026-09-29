# main.py - V15 - ADMIN HIDDEN + POINTS + DAILY 5 + REFERRAL 50
import os, json, logging, time, asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API") or os.getenv("GROQ_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
client = Groq(api_key=GROQ_API_KEY)

POINTS_FILE = "points.json"
BROADCAST_FILE = "broadcasts.json"
MEMORY_FILE = "memory.json"
DAILY_FILE = "daily.json"
USER_STATE = {}

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f, "r", encoding="utf-8") as j: return json.load(j)
    except: return {}
def save_json(f,d):
    with open(f,"w",encoding="utf-8") as j: json.dump(d,j,ensure_ascii=False)

def load_points(): return load_json(POINTS_FILE)
def save_points(d): save_json(POINTS_FILE,d)

def get_keyboard(uid):
    is_admin = str(uid) == str(ADMIN_ID)
    if is_admin:
        return ReplyKeyboardMarkup([
            ["بورانا", "اذاعة"],
            ["بوتاتنا", "الاحصائيات 📊"],
            ["تلاقي 💙", "ميزات 🚀"],
            ["🎁 هدية يومية", "🔗 رابط دعوتي"],
            ["💎 نقاطي", "🗑️ حذف آخر إذاعة"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["بورانا", "بوتاتنا"],
            ["تلاقي 💙", "ميزات 🚀"],
            ["🎁 هدية يومية", "🔗 رابط دعوتي"],
            ["💎 نقاطي"]
        ], resize_keyboard=True)

def detect_lang(text):
    return "ar" if any('\u0600' <= c <= '\u06FF' for c in text) else "en"

def get_user_memory(uid):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    now=time.time()
    return [m for m in mem if now - m.get("time",0) < 86400]

def save_user_memory(uid, role, content):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    now=time.time()
    mem = [m for m in mem if now - m.get("time",0) < 86400]
    mem.append({"role":role,"content":content,"time":now})
    all_mem[str(uid)] = mem[-20:]
    save_json(MEMORY_FILE, all_mem)

TEXT_START = """🔗 قناة التمويل 👇
https://t.me/SmartAI_Ar

أنا Gotchat 🤖
أتكلم بلغتك وأتذكرك يوم كامل 💙
@chatGP_1bot
"""

async def send_admin_notify(update, context):
    if not ADMIN_ID: return
    u=update.effective_user
    txt=f"🚀 دخول جديد\n👤 {u.first_name}\n🔗 @{u.username or 'بدون'}\n🆔 `{u.id}`\n🌐 {u.language_code}"
    try: await context.bot.send_message(int(ADMIN_ID), txt, parse_mode="Markdown")
    except: pass

async def start(update, context):
    uid = str(update.effective_user.id)
    if uid in USER_STATE: del USER_STATE[uid]
    points = load_points()
    args = context.args
    if args and args[0].startswith("ref_"):
        ref_id = args[0].replace("ref_", "")
        if ref_id!= uid and uid not in points:
            ref_data = points.get(ref_id, {"points":0})
            ref_data["points"] = ref_data.get("points",0) + 50
            points[ref_id] = ref_data
            save_points(points)
            try: await context.bot.send_message(int(ref_id), f"🎉 شخص انضم عن طريق رابطك! +50 نقطة 💎\nنقاطك: {ref_data['points']}")
            except: pass
    if uid not in points: points[uid] = {"points": 10}
    save_points(points)
    save_user_memory(uid, "user", "بدأ /start")
    await send_admin_notify(update, context)
    await update.message.reply_text(TEXT_START + f"\n💎 نقاطك: {points[uid]['points']}", reply_markup=get_keyboard(uid))

async def points_cmd(update, context):
    uid = str(update.effective_user.id)
    pts = load_points().get(uid, {}).get("points",0)
    await update.message.reply_text(f"💎 نقاطك: {pts}\n\n🎁 يومية: 5\n🔗 دعوة: 50", reply_markup=get_keyboard(uid))

async def daily_gift(update, context):
    uid = str(update.effective_user.id)
    daily = load_json(DAILY_FILE)
    now = time.time()
    last = daily.get(uid, 0)
    if now - last < 86400:
        remain = 86400 - (now - last)
        hours = int(remain//3600)
        return await update.message.reply_text(f"⏳ أخذت هديتك!\nتعال بعد {hours} ساعة", reply_markup=get_keyboard(uid))
    points = load_points()
    if uid not in points: points[uid] = {"points":0}
    points[uid]["points"] = points[uid].get("points",0) + 5
    save_points(points)
    daily[uid] = now
    save_json(DAILY_FILE, daily)
    await update.message.reply_text(f"🎁 +5 نقاط\n💎 نقاطك: {points[uid]['points']}", reply_markup=get_keyboard(uid))

async def invite_link(update, context):
    uid = str(update.effective_user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{uid}"
    pts = load_points().get(uid, {}).get("points",0)
    await update.message.reply_text(f"🔗 رابطك:\n{link}\n\nكل شخص يدخل = 50 نقطة 💎\nنقاطك: {pts}", reply_markup=get_keyboard(uid))

async def delete_broadcast_logic(bid, context):
    broadcasts = load_json(BROADCAST_FILE)
    if bid not in broadcasts: return False
    for chat_id, msg_id in broadcasts[bid]:
        try: await context.bot.delete_message(int(chat_id), int(msg_id))
        except: pass
    del broadcasts[bid]; save_json(BROADCAST_FILE, broadcasts)
    return True

async def broadcast_cmd(update, context):
    if str(update.effective_user.id)!= str(ADMIN_ID): return await update.message.reply_text("❌ للمشرف فقط")
    msg_text = " ".join(context.args) if context.args else ""
    reply_msg = update.message.reply_to_message
    pin=False; delete_after=0
    parts = msg_text.split()
    if parts and parts[0].lower()=="pin": pin=True; parts.pop(0)
    if parts and parts[0].isdigit(): delete_after=int(parts[0]); parts.pop(0)
    final_text = " ".join(parts)
    if not final_text and not reply_msg: return await update.message.reply_text("📢 /broadcast رسالتك")
    users = load_points(); broadcasts = load_json(BROADCAST_FILE); bid=str(len(broadcasts)+1); broadcasts[bid]=[]; sent=0
    await update.message.reply_text(f"⏳ لـ {len(users)}...")
    for user_id in users:
        try:
            if reply_msg: m = await context.bot.copy_message(int(user_id), update.effective_chat.id, reply_msg.message_id)
            else: m = await context.bot.send_message(int(user_id), final_text)
            broadcasts[bid].append([user_id, m.message_id])
            if pin:
                try: await context.bot.pin_chat_message(int(user_id), m.message_id, disable_notification=True)
                except: pass
            sent+=1; await asyncio.sleep(0.04)
        except: pass
    save_json(BROADCAST_FILE, broadcasts)
    await update.message.reply_text(f"✅ تم {sent} - ID {bid}", reply_markup=get_keyboard(update.effective_user.id))
    if delete_after>0:
        await asyncio.sleep(delete_after*60); await delete_broadcast_logic(bid, context)

async def del_broadcast_cmd(update, context):
    if str(update.effective_user.id)!= str(ADMIN_ID): return
    if not context.args: return await update.message.reply_text("استخدم: /delbroadcast ID")
    ok = await delete_broadcast_logic(context.args[0], context)
    await update.message.reply_text("🗑️ تم الحذف" if ok else "❌ ID خطأ", reply_markup=get_keyboard(update.effective_user.id))

async def del_last_broadcast(update, context):
    if str(update.effective_user.id)!= str(ADMIN_ID): return
    broadcasts = load_json(BROADCAST_FILE)
    if not broadcasts: return await update.message.reply_text("لا يوجد", reply_markup=get_keyboard(update.effective_user.id))
    last_id = str(max([int(k) for k in broadcasts.keys()]))
    await delete_broadcast_logic(last_id, context)
    await update.message.reply_text(f"🗑️ تم حذف آخر إذاعة {last_id}", reply_markup=get_keyboard(update.effective_user.id))

async def bots_cmd(update, context):
    await update.message.reply_text("🤖 بوتاتنا:\nhttps://t.me/FFZZ5", reply_markup=get_keyboard(update.effective_user.id))

async def chat_handler(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    if not text: return
    if text in ["بورانا","اذاعة","بوتاتنا","الاحصائيات 📊","تلاقي 💙","ميزات 🚀","🎁 هدية يومية","🔗 رابط دعوتي","💎 نقاطي","🗑️ حذف آخر إذاعة"] and uid in USER_STATE and text!="اذاعة":
        del USER_STATE[uid]
    if text == "اذاعة":
        if str(uid)!= str(ADMIN_ID): return await update.message.reply_text("❌ للمشرف فقط", reply_markup=get_keyboard(uid))
        USER_STATE[uid]="اذاعة"
        return await update.message.reply_text("📢 أرسل رسالة الإذاعة", reply_markup=get_keyboard(uid))
    if text == "🗑️ حذف آخر إذاعة": return await del_last_broadcast(update, context)
    if text == "بوتاتنا": return await bots_cmd(update, context)
    if "الاحصائيات" in text:
        if str(uid)!= str(ADMIN_ID): return await update.message.reply_text("❌ للمشرف فقط", reply_markup=get_keyboard(uid))
        return await update.message.reply_text(f"👥 {len(load_points())}", reply_markup=get_keyboard(uid))
    if text == "🎁 هدية يومية": return await daily_gift(update, context)
    if text == "🔗 رابط دعوتي": return await invite_link(update, context)
    if text == "💎 نقاطي": return await points_cmd(update, context)
    if "ميزات" in text: return await update.message.reply_text("🚀 /start - 🎁 هدية - 🔗 دعوة - 💎 نقاط", reply_markup=get_keyboard(uid))
    if text.startswith("/"): return
    if USER_STATE.get(uid) == "اذاعة":
        del USER_STATE[uid]
        context.args = text.split()
        return await broadcast_cmd(update, context)
    user_lang = detect_lang(text)
    memory = get_user_memory(uid)
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    messages=[{"role":"system","content":f"أنت Gotchat مثل Meta AI. ترد بلغة المستخدم ({user_lang}). تتذكر يوم. ودود."}]
    for m in memory[-8:]:
        if m["role"] in ["user","assistant"]: messages.append({"role":m["role"],"content":m["content"]})
    messages.append({"role":"user","content":text})
    try:
        comp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7)
        reply = comp.choices[0].message.content
        save_user_memory(uid,"user",text); save_user_memory(uid,"assistant",reply)
        await update.message.reply_text(reply, reply_markup=get_keyboard(uid))
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}", reply_markup=get_keyboard(uid))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("delbroadcast", del_broadcast_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    print("main.py V15 - READY")
    app.run_polling()

if __name__ == "__main__": main())
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
