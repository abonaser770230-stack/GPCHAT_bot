# main.py V16 - FINAL FIX Conflict + AI
import os, json, logging, time, asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API") or os.getenv("GROQ")
ADMIN_ID = str(os.getenv("ADMIN_ID") or "8885536751").strip()

print(f"--- STARTING V16 ---")
print(f"BOT_TOKEN OK: {bool(BOT_TOKEN)}")
print(f"GROQ_KEY OK: {bool(GROQ_KEY)}")
print(f"ADMIN_ID: {ADMIN_ID}")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN ناقص في Railway Variables")

client = None
if GROQ_KEY:
    try:
        client = Groq(api_key=GROQ_KEY)
        print("Groq Client OK")
    except Exception as e:
        print(f"Groq init error: {e}")
else:
    print("تحذير: GROQ_KEY غير موجود!")

# ملفات
POINTS_FILE, BROADCAST_FILE, MEMORY_FILE, DAILY_FILE = "points.json","broadcasts.json","memory.json","daily.json"

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,"r",encoding="utf-8") as j: return json.load(j)
    except: return {}
def save_json(f,d):
    try:
        with open(f,"w",encoding="utf-8") as j: json.dump(d,j,ensure_ascii=False)
    except Exception as e: print(f"save error {f}: {e}")

def load_points(): return load_json(POINTS_FILE)
def save_points(d): save_json(POINTS_FILE,d)

def get_keyboard(uid):
    is_admin = str(uid) == ADMIN_ID
    if is_admin:
        return ReplyKeyboardMarkup([
            ["بورانا","اذاعة"],
            ["بوتاتنا","الاحصائيات 📊"],
            ["تلاقي 💙","ميزات 🚀"],
            ["🎁 هدية يومية","🔗 رابط دعوتي"],
            ["💎 نقاطي","🗑️ حذف آخر إذاعة"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["بورانا","بوتاتنا"],
            ["تلاقي 💙","ميزات 🚀"],
            ["🎁 هدية يومية","🔗 رابط دعوتي"],
            ["💎 نقاطي"]
        ], resize_keyboard=True)

def save_memory(uid, role, content):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    mem = [m for m in mem if time.time() - m.get("time",0) < 86400]
    mem.append({"role":role,"content":content,"time":time.time()})
    all_mem[str(uid)] = mem[-20:]
    save_json(MEMORY_FILE, all_mem)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    points = load_points()
    args = context.args
    if args and args[0].startswith("ref_"):
        ref_id = args[0].replace("ref_","")
        if ref_id!= uid and uid not in points:
            r = points.get(ref_id, {"points":0})
            r["points"] = r.get("points",0) + 50
            points[ref_id] = r
            try: await context.bot.send_message(int(ref_id), f"🎉 شخص دخل برابطك +50 نقطة! الآن نقاطك: {r['points']}")
            except: pass
    if uid not in points: points[uid] = {"points":10}
    save_points(points)
    await update.message.reply_text(
        f"أهلا {update.effective_user.first_name} ✅\n\n"
        f"💎 نقاطك: {points[uid]['points']}\n"
        f"💬 اسألني أي شيء، أنا Gotchat الذكي!",
        reply_markup=get_keyboard(uid)
    )

async def daily_gift(update, context):
    uid=str(update.effective_user.id)
    daily=load_json(DAILY_FILE)
    if time.time() - daily.get(uid,0) < 86400:
        return await update.message.reply_text("⏳ أخذت هديتك اليوم، تعال بكرة!", reply_markup=get_keyboard(uid))
    points=load_points()
    points.setdefault(uid,{"points":0})["points"]+=5
    save_points(points); daily[uid]=time.time(); save_json(DAILY_FILE,daily)
    await update.message.reply_text(f"🎁 تم! +5 نقاط\n💎 نقاطك الآن: {points[uid]['points']}", reply_markup=get_keyboard(uid))

async def invite_link(update, context):
    uid=str(update.effective_user.id)
    bot=(await context.bot.get_me()).username
    link=f"https://t.me/{bot}?start=ref_{uid}"
    pts=load_points().get(uid,{}).get("points",0)
    await update.message.reply_text(f"🔗 رابط دعوتك:\n{link}\n\nكل صديق = 50 نقطة 💎\nنقاطك: {pts}", reply_markup=get_keyboard(uid))

async def points_cmd(update, context):
    pts=load_points().get(str(update.effective_user.id),{}).get("points",0)
    await update.message.reply_text(f"💎 نقاطك: {pts}", reply_markup=get_keyboard(update.effective_user.id))

async def stats_cmd(update, context):
    if str(update.effective_user.id)!= ADMIN_ID: return
    pts=load_points()
    await update.message.reply_text(f"📊 عدد المستخدمين: {len(pts)}\nإجمالي النقاط: {sum(v.get('points',0) for v in pts.values())}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id)
    text=(update.message.text or "").strip()
    if not text: return

    # أزرار
    if text=="🎁 هدية يومية": return await daily_gift(update,context)
    if text=="🔗 رابط دعوتي": return await invite_link(update,context)
    if text=="💎 نقاطي" or text=="نقاطي 💎": return await points_cmd(update,context)
    if text=="الاحصائيات 📊": return await stats_cmd(update,context)
    if text=="بوتاتنا": return await update.message.reply_text("🤖 بوتاتنا:\nhttps://t.me/FFZZ5", reply_markup=get_keyboard(uid))
    if text=="بورانا": return await update.message.reply_text("✨ بورانا:\nhttps://t.me/BoranaAiBot", reply_markup=get_keyboard(uid))
    if text in ["تلاقي 💙","ميزات 🚀","ستارت","المدونة","تمويل أعضاء","قناة التمويل"]:
        return await update.message.reply_text("🚀 قريبا!", reply_markup=get_keyboard(uid))

    # فلتر نقاط - كل رسالة ب 1 نقطة (اختياري)
    points=load_points()
    if uid not in points: points[uid]={"points":10}
    save_points(points)

    # ذكاء اصطناعي
    if not client:
        return await update.message.reply_text("❌ خطأ: GROQ_API_KEY غير مضبوط في Railway Variables", reply_markup=get_keyboard(uid))

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        all_mem=load_json(MEMORY_FILE).get(uid,[])
        msgs=[{"role":"system","content":"أنت Gotchat بوت ذكاء اصطناعي عربي ذكي، سريع، تجاوب باختصار مفيد. عاصمة اليمن صنعاء."}]
        for m in all_mem[-6:]:
            msgs.append({"role":m["role"],"content":m["content"]})
        msgs.append({"role":"user","content":text})

        comp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=msgs,
            temperature=0.7,
            max_tokens=800
        )
        reply = comp.choices[0].message.content
        save_memory(uid,"user",text)
        save_memory(uid,"assistant",reply)
        await update.message.reply_text(reply, reply_markup=get_keyboard(uid))
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await update.message.reply_text(f"⚠️ خطأ مؤقت: {e}", reply_markup=get_keyboard(uid))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    # هذا السطر يحل مشكلة Conflict نهائيا
    print("Bot V16 Started - Polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
