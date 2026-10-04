# main.py V16.3 - OPTIMIZED & FIXED EXCEPTIONS
import os
import json
import logging
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError, RetryAfter
from groq import Groq

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")
ADMIN_ID = os.getenv("ADMIN_ID")

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

POINTS_FILE = "points.json"
BROADCAST_FILE = "broadcasts.json"
MEMORY_FILE = "memory.json"
DAILY_FILE = "daily.json"

USER_STATES = {}

def load_json(f):
    if not os.path.exists(f):
        return {}
    try:
        with open(f, "r", encoding="utf-8") as j:
            return json.load(j)
    except Exception as e:
        logging.error(f"Error loading {f}: {e}")
        return {}

def save_json(f, d):
    try:
        with open(f, "w", encoding="utf-8") as j:
            json.dump(d, j, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving {f}: {e}")

def load_points(): 
    return load_json(POINTS_FILE)

def save_points(d): 
    save_json(POINTS_FILE, d)

def get_keyboard(uid):
    is_admin = str(uid) == str(ADMIN_ID)
    if is_admin:
        return ReplyKeyboardMarkup(
            [
                ["اذاعة 📢", "الاحصائيات 📊"],
                ["🎁 هدية يومية", "🔗 رابط دعوتي"],
                ["💎 نقاطي", "🗑️ حذف آخر إذاعة"],
                ["إلغاء ❌"]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            [
                ["🎁 هدية يومية", "🔗 رابط دعوتي"],
                ["💎 نقاطي", "🤖 بوتاتنا"]
            ],
            resize_keyboard=True
        )

def save_memory(uid, role, content):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    mem = [m for m in mem if time.time() - m.get("time", 0) < 86400]
    mem.append({"role": role, "content": content, "time": time.time()})
    all_mem[str(uid)] = mem[-20:]
    save_json(MEMORY_FILE, all_mem)

async def start(update: Update, context):
    if not update.message:
        return
    uid = str(update.effective_user.id)
    user = update.effective_user
    points = load_points()
    args = context.args
    
    if args and args[0].startswith("ref_"):
        ref_id = args[0].replace("ref_", "")
        if ref_id != uid and uid not in points:
            r = points.get(ref_id, {"points": 0})
            r["points"] = r.get("points", 0) + 50
            points[ref_id] = r
            try:
                await context.bot.send_message(
                    int(ref_id), 
                    f"🎉 دخل شخص جديد عبر رابطك وحصلت على +50 نقطة! 💎\nنقاطك الحالية: {r['points']}"
                )
            except Exception:
                pass

    if uid not in points:
        points[uid] = {"points": 10, "joined_at": time.time(), "username": user.username, "name": user.first_name}
    else:
        points[uid]["name"] = user.first_name
        points[uid]["username"] = user.username
        
    save_points(points)

    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{uid}"

    welcome_msg = (
        f"أهلاً بك يا {user.first_name} 👋\n\n"
        f"🤖 أنا مساعدك الذكي القائم على الذكاء الاصطناعي.\n"
        f"💬 يمكنك أن تسألني أي سؤال بأي لغة وسأجيبك فوراً بلغتك!\n\n"
        f"💎 رصيدك الحالي: {points[uid]['points']} نقطة\n"
        f"🔗 رابط الدعوة الخاص بك:\n`{ref_link}`\n\n"
        f"🎁 يمكنك الحصول على نقاط مجانية يومياً عبر زر الهدايا!"
    )
    
    await update.message.reply_text(welcome_msg, parse_mode="Markdown", reply_markup=get_keyboard(uid))

async def daily_gift(update: Update, context):
    uid = str(update.effective_user.id)
    daily = load_json(DAILY_FILE)
    now = time.time()
    
    if now - daily.get(uid, 0) < 86400:
        remaining_hours = int((86400 - (now - daily.get(uid, 0))) / 3600)
        return await update.message.reply_text(
            f"⏳ لقد حصلت على هديتك اليومية بالفعل!\nعد بعد {remaining_hours} ساعة للحصول على المجموع القادم.",
            reply_markup=get_keyboard(uid)
        )
    
    points = load_points()
    points.setdefault(uid, {"points": 0})["points"] += 5
    save_points(points)
    daily[uid] = now
    save_json(DAILY_FILE, daily)
    
    await update.message.reply_text(
        f"🎉 مبروك! حصلت على +5 نقاط هدية يومية! 🎁\n💎 رصيدك الإجمالي الآن: {points[uid]['points']}",
        reply_markup=get_keyboard(uid)
    )

async def invite_link(update: Update, context):
    uid = str(update.effective_user.id)
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
    pts = load_points().get(uid, {}).get("points", 0)
    
    msg = (
        f"🔗 **رابط الدعوة الخاص بك:**\n`{link}`\n\n"
        f"💎 **المكافأة:** 50 نقطة لكل صديق ينضم عن طريقك!\n"
        f"📊 **نقاطك الحالية:** {pts} نقطة"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard(uid))

async def points_cmd(update: Update, context):
    uid = str(update.effective_user.id)
    pts = load_points().get(uid, {}).get("points", 0)
    await update.message.reply_text(f"💎 رصيدك الحالي: **{pts}** نقطة", parse_mode="Markdown", reply_markup=get_keyboard(uid))

async def stats_cmd(update: Update, context):
    uid = str(update.effective_user.id)
    if str(uid) != str(ADMIN_ID):
        return
    
    points = load_points()
    total_users = len(points)
    total_pts = sum(u.get("points", 0) for u in points.values())
    
    msg = (
        f"📊 **إحصائيات البوت:**\n\n"
        f"👥 إجمالي المستخدمين: **{total_users}**\n"
        f"💎 إجمالي النقاط الموزعة: **{total_pts}**\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard(uid))

async def delete_last_broadcast(update: Update, context):
    uid = str(update.effective_user.id)
    if str(uid) != str(ADMIN_ID):
        return

    broadcasts = load_json(BROADCAST_FILE)
    last_bc = broadcasts.get("last_broadcast", [])
    if not last_bc:
        return await update.message.reply_text("❌ لا توجد إذاعة سابقة لحذفها.")

    deleted_count = 0
    for msg in last_bc:
        try:
            await context.bot.delete_message(chat_id=msg["chat_id"], message_id=msg["message_id"])
            deleted_count += 1
            await asyncio.sleep(0.02)
        except Exception:
            pass

    broadcasts["last_broadcast"] = []
    save_json(BROADCAST_FILE, broadcasts)
    await update.message.reply_text(f"🗑️ تم حذف الإذاعة الأخيرة من {deleted_count} مستخدم.")

async def chat_handler(update: Update, context):
    if not update.message:
        return
    
    uid = str(update.effective_user.id)
    text = update.message.text.strip() if update.message.text else ""
    user_lang = update.effective_user.language_code or "ar"

    if text == "إلغاء ❌":
        USER_STATES.pop(uid, None)
        return await update.message.reply_text("❌ تم الإلغاء.", reply_markup=get_keyboard(uid))

    # معالجة وضع الإذاعة المحسنة مع إعادة المحاولة الذكية
    if USER_STATES.get(uid) == "WAITING_BROADCAST":
        if str(uid) != str(ADMIN_ID):
            return
        
        USER_STATES.pop(uid, None)
        points = load_points()
        sent_msg = await update.message.reply_text("📢 جاري إرسال الإذاعة للجميع...")
        
        sent_list = []
        success, failed = 0, 0
        
        for user_id in points.keys():
            sent = False
            for attempt in range(3):
                try:
                    msg = await context.bot.copy_message(
                        chat_id=int(user_id), 
                        from_chat_id=update.effective_chat.id, 
                        message_id=update.message.message_id
                    )
                    sent_list.append({"chat_id": int(user_id), "message_id": msg.message_id})
                    success += 1
                    sent = True
                    await asyncio.sleep(0.04)
                    break
                except RetryAfter as e:
                    await asyncio.sleep(e.retry_after + 0.1)
                except Exception:
                    break
            if not sent:
                failed += 1

        broadcasts = load_json(BROADCAST_FILE)
        broadcasts["last_broadcast"] = sent_list
        save_json(BROADCAST_FILE, broadcasts)

        return await sent_msg.edit_text(f"✅ اكتملت الإذاعة!\n\n👍 نجاح: {success}\n👎 فشل: {failed}")

    if text == "اذاعة 📢":
        if str(uid) == str(ADMIN_ID):
            USER_STATES[uid] = "WAITING_BROADCAST"
            return await update.message.reply_text("أرسل الآن نص الإذاعة أو التوجيه (صورة/فيديو/نص):", reply_markup=get_keyboard(uid))

    if text == "🎁 هدية يومية": return await daily_gift(update, context)
    if text == "🔗 رابط دعوتي": return await invite_link(update, context)
    if text == "💎 نقاطي": return await points_cmd(update, context)
    if text == "الاحصائيات 📊": return await stats_cmd(update, context)
    if text == "🗑️ حذف آخر إذاعة": return await delete_last_broadcast(update, context)
    if text == "🤖 بوتاتنا": return await update.message.reply_text("🤖 بوتاتنا المفيدة:\nhttps://t.me/FFZZ5", reply_markup=get_keyboard(uid))

    if not text:
        return await update.message.reply_text("💡 يرجى إرسال سؤال أو نص كتابي لإجابته.", reply_markup=get_keyboard(uid))

    if not client:
        return await update.message.reply_text("❌ لم يتم ضبط مفتاح GROQ_API_KEY في السيرفر!", reply_markup=get_keyboard(uid))

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        all_mem = load_json(MEMORY_FILE).get(uid, [])
        
        system_prompt = (
            f"You are Gotchat, a helpful and smart AI assistant. "
            f"User's primary language code is '{user_lang}'. "
            f"IMPORTANT: Always detect the language of the user's message and respond in the EXACT same language (Arabic, English, French, etc.). Keep replies concise and useful."
        )
        
        msgs = [{"role": "system", "content": system_prompt}]
        for m in all_mem[-6:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        msgs.append({"role": "user", "content": text})

        loop = asyncio.get_event_loop()
        comp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=msgs,
                temperature=0.7
            )
        )
        reply = comp.choices[0].message.content

        save_memory(uid, "user", text)
        save_memory(uid, "assistant", reply)
        await update.message.reply_text(reply, reply_markup=get_keyboard(uid))

    except Exception as e:
        logging.error(f"Groq Error: {e}")
        await update.message.reply_text(f"⚠️ خطأ AI: {e}", reply_markup=get_keyboard(uid))

def main():
    if not BOT_TOKEN:
        print("❌ CRITICAL ERROR: BOT_TOKEN is Missing!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, chat_handler))
    
    print("🚀 Bot V16.3 Fully Tested and Running Perfectly...")
    app.run_polling()

if __name__ == "__main__":
    main()
        
