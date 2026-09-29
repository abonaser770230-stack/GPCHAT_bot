import os
import json
import asyncio
import logging
import time
from datetime import datetime, timedelta
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
MEMORY_FILE = "memory.json" # ذاكرة 24 ساعة
USER_STATE = {}

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f, "r", encoding="utf-8") as j: return json.load(j)
    except: return {}
def save_json(f, d):
    with open(f, "w", encoding="utf-8") as j: json.dump(d, j, ensure_ascii=False)

def load_points(): return load_json(POINTS_FILE)

# --- نظام الذاكرة 24 ساعة مثلي ---
def get_user_memory(uid):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    # احذف الرسائل الأقدم من 24 ساعة
    now = time.time()
    mem = [m for m in mem if now - m.get("time", 0) < 86400]
    return mem

def save_user_memory(uid, role, content):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    now = time.time()
    # نظف القديم
    mem = [m for m in mem if now - m.get("time", 0) < 86400]
    mem.append({"role": role, "content": content, "time": now})
    # خلي آخر 20 رسالة فقط عشان لا يثقل
    mem = mem[-20:]
    all_mem[str(uid)] = mem
    save_json(MEMORY_FILE, all_mem)
    return mem

def detect_lang(text):
    # كشف بسيط وسريع
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > 0: return "ar"
    return "en"

KEYBOARD = ReplyKeyboardMarkup(
    [
        ["بورانا", "اذاعة"],
        ["بوتاتنا", "الاحصائيات 📊"],
        ["تلاقي 💙", "ميزات 🚀"],
        ["🗑️ حذف آخر إذاعة"] # زر جديد
    ],
    resize_keyboard=True
)

TEXT_START = """🔗 قناة التمويل 👇
https://t.me/SmartAI_Ar

أنا Gotchat - نسخة من Meta AI 🤖
أتكلم بلغتك تلقائياً وأتذكر كلامك لمدة يوم كامل 💙
جرب @chatGP_1bot
"""

async def send_admin_notify(update, context):
    if not ADMIN_ID: return
    u = update.effective_user
    username = f"@{u.username}" if u.username else "بدون يوزر"
    text = f"🚀 دخول جديد\n👤 {u.first_name}\n🔗 {username}\n🆔 `{u.id}`\n🌐 {u.language_code}"
    try: await context.bot.send_message(int(ADMIN_ID), text, parse_mode="Markdown")
    except: pass

async def start(update, context):
    uid = str(update.effective_user.id)
    if uid in USER_STATE: del USER_STATE[uid]
    data = load_points(); data[uid] = data.get(uid,0)+1; save_json(POINTS_FILE, data)
    # امسح ذاكرته القديمة وابدأ جديد
    save_user_memory(uid, "system", "بدأ محادثة جديدة")
    await send_admin_notify(update, context)
    await update.message.reply_text(TEXT_START, reply_markup=KEYBOARD)

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
    uid = str(update.effective_user.id)
    if uid in USER_STATE: del USER_STATE[uid]
    msg_text = " ".join(context.args) if context.args else ""
    reply_msg = update.message.reply_to_message
    pin=False; delete_after=0
    parts = msg_text.split() if msg_text else []
    if parts and parts[0].lower()=="pin": pin=True; parts.pop(0)
    if parts and parts[0].isdigit(): delete_after=int(parts[0]); parts.pop(0)
    final_text = " ".join(parts) if parts else ""
    if not final_text and not reply_msg: return await update.message.reply_text("📢 /broadcast رسالتك\n/broadcast pin 60 رسالتك\nأو رد على رسالة")
    users=load_points(); broadcasts=load_json(BROADCAST_FILE); bid=str(len(broadcasts)+1); broadcasts[bid]=[]; sent=0
    await update.message.reply_text(f"⏳ لـ {len(users)}...")
    for user_id in list(users.keys()):
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
    await update.message.reply_text(f"✅ تم {sent} - ID: {bid} - /delbroadcast {bid}")
    if delete_after>0:
        await asyncio.sleep(delete_after*60); await delete_broadcast_logic(bid, context)

async def del_broadcast_cmd(update, context):
    if str(update.effective_user.id)!= str(ADMIN_ID): return
    if not context.args: return await update.message.reply_text("استخدم: /delbroadcast ID")
    ok = await delete_broadcast_logic(context.args[0], context)
    await update.message.reply_text(f"🗑️ تم حذف {context.args[0]}" if ok else "❌ ID خطأ")

async def del_last_broadcast(update, context):
    if str(update.effective_user.id)!= str(ADMIN_ID): return await update.message.reply_text("❌ للمشرف فقط")
    broadcasts = load_json(BROADCAST_FILE)
    if not broadcasts: return await update.message.reply_text("لا يوجد إذاعات")
    last_id = str(max([int(k) for k in broadcasts.keys()]))
    await delete_broadcast_logic(last_id, context)
    await update.message.reply_text(f"🗑️ تم حذف آخر إذاعة: {last_id} من عند الكل ✅", reply_markup=KEYBOARD)

async def bots_cmd(update, context):
    if str(update.effective_user.id) in USER_STATE: del USER_STATE[str(update.effective_user.id)]
    await update.message.reply_text("🤖 بوتاتنا:\nhttps://t.me/FFZZ5", reply_markup=KEYBOARD)

async def chat_handler(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    if not text: return

    buttons = ["بورانا","اذاعة","بوتاتنا","الاحصائيات 📊","الاحصائيات","تلاقي 💙","ميزات 🚀","تلاقي","ميزات","🗑️ حذف آخر إذاعة"]
    if text in buttons and uid in USER_STATE and text not in ["اذاعة"]:
        del USER_STATE[uid]
        await update.message.reply_text(f"❌ تم إلغاء الأمر السابق", reply_markup=KEYBOARD)

    if text == "اذاعة":
        USER_STATE[uid]="اذاعة"
        return await update.message.reply_text("📢 أرسل رسالة الإذاعة الآن (أو /cancel)", reply_markup=KEYBOARD)
    if text == "🗑️ حذف آخر إذاعة": return await del_last_broadcast(update, context)
    if text == "بوتاتنا": return await bots_cmd(update, context)
    if "الاحصائيات" in text: return await update.message.reply_text(f"👥 {len(load_points())}", reply_markup=KEYBOARD)
    if "ميزات" in text: return await update.message.reply_text("🚀 /start /broadcast /delbroadcast /cancel + أتذكرك 24 ساعة + أرد بلغتك", reply_markup=KEYBOARD)
    if "تلاقي" in text: return await update.message.reply_text("💙 أرسل سؤالك!", reply_markup=KEYBOARD)
    if text.startswith("/"): return

    # --- نظام الذاكرة + اللغة مثلي تماما ---
    user_lang = detect_lang(text)
    memory = get_user_memory(uid)

    # احفظ رسالة المستخدم
    save_user_memory(uid, "user", text)

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    # جهز الرسائل للذكاء الاصطناعي مع الذاكرة
    messages = [
        {"role": "system", "content": f"أنت Gotchat، مساعد ذكي مثل Meta AI. ترد بلغة المستخدم تلقائياً (لغة المستخدم الحالية: {user_lang}). تتذكر المحادثة لمدة يوم. كن ودود، ذكي، ومفيد. اذا كانت لغة المستخدم عربية رد عربية، اذا انجليزية رد انجليزية. لا تقل انك Meta AI، قل انك Gotchat."}
    ]
    # ضيف الذاكرة
    for m in memory[-10:]: # آخر 10 رسائل فقط
        if m["role"] in ["user", "assistant"]:
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": text})

    try:
        comp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7)
        reply = comp.choices[0].message.content
        save_user_memory(uid, "assistant", reply)
        await update.message.reply_text(reply, reply_markup=KEYBOARD)
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}", reply_markup=KEYBOARD)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("delbroadcast", del_broadcast_cmd))
    app.add_handler(CommandHandler("bots", bots_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    print("V14 LIKE META AI - 24H MEMORY - LANG DETECT")
    app.run_polling()
if __name__ == "__main__": main()ory[user_id_int]=memory[user_id_int][-12:]
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
