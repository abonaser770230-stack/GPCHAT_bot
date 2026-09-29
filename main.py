# main.py V15.1 - FIX AI REPLY
import os, json, logging, time, asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from groq import Groq

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")
ADMIN_ID = os.getenv("ADMIN_ID")

print(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
print(f"GROQ_KEY exists: {bool(GROQ_KEY)}")
print(f"ADMIN_ID: {ADMIN_ID}")

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

POINTS_FILE, BROADCAST_FILE, MEMORY_FILE, DAILY_FILE = "points.json","broadcasts.json","memory.json","daily.json"
USER_STATE = {}

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,"r",encoding="utf-8") as j: return json.load(j)
    except: return {}
def save_json(f,d):
    with open(f,"w",encoding="utf-8") as j: json.dump(d,j,ensure_ascii=False)
def load_points(): return load_json(POINTS_FILE)
def save_points(d): save_json(POINTS_FILE,d)

def get_keyboard(uid):
    is_admin = str(uid) == str(ADMIN_ID)
    if is_admin:
        return ReplyKeyboardMarkup([["بورانا","اذاعة"],["بوتاتنا","الاحصائيات 📊"],["تلاقي 💙","ميزات 🚀"],["🎁 هدية يومية","🔗 رابط دعوتي"],["💎 نقاطي","🗑️ حذف آخر إذاعة"]], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["بورانا","بوتاتنا"],["تلاقي 💙","ميزات 🚀"],["🎁 هدية يومية","🔗 رابط دعوتي"],["💎 نقاطي"]], resize_keyboard=True)

def save_memory(uid, role, content):
    all_mem = load_json(MEMORY_FILE)
    mem = all_mem.get(str(uid), [])
    mem = [m for m in mem if time.time() - m.get("time",0) < 86400]
    mem.append({"role":role,"content":content,"time":time.time()})
    all_mem[str(uid)] = mem[-20:]
    save_json(MEMORY_FILE, all_mem)

async def start(update, context):
    uid = str(update.effective_user.id)
    points = load_points()
    args = context.args
    if args and args[0].startswith("ref_"):
        ref_id = args[0].replace("ref_","")
        if ref_id!= uid and uid not in points:
            r = points.get(ref_id, {"points":0})
            r["points"] = r.get("points",0) + 50
            points[ref_id] = r
            try: await context.bot.send_message(int(ref_id), f"🎉 شخص دخل برابطك +50 نقطة! نقاطك: {r['points']}")
            except: pass
    if uid not in points: points[uid] = {"points":10}
    save_points(points)
    await update.message.reply_text(f"أهلا {update.effective_user.first_name} ✅\n\n💎 نقاطك: {points[uid]['points']}\n💬 اسألني أي شي!", reply_markup=get_keyboard(uid))

async def daily_gift(update, context):
    uid=str(update.effective_user.id)
    daily=load_json(DAILY_FILE)
    if time.time() - daily.get(uid,0) < 86400:
        return await update.message.reply_text("⏳ أخذت هديتك اليوم، تعال بكرة!", reply_markup=get_keyboard(uid))
    points=load_points()
    points.setdefault(uid,{"points":0})["points"]+=5
    save_points(points); daily[uid]=time.time(); save_json(DAILY_FILE,daily)
    await update.message.reply_text(f"🎁 +5 نقاط!\n💎 نقاطك: {points[uid]['points']}", reply_markup=get_keyboard(uid))

async def invite_link(update, context):
    uid=str(update.effective_user.id)
    bot=(await context.bot.get_me()).username
    link=f"https://t.me/{bot}?start=ref_{uid}"
    pts=load_points().get(uid,{}).get("points",0)
    await update.message.reply_text(f"🔗 رابطك:\n{link}\n\n50 نقطة لكل دعوة 💎\nنقاطك: {pts}", reply_markup=get_keyboard(uid))

async def points_cmd(update, context):
    uid=str(update.effective_user.id)
    pts=load_points().get(uid,{}).get("points",0)
    await update.message.reply_text(f"💎 نقاطك: {pts}", reply_markup=get_keyboard(uid))

async def chat_handler(update, context):
    uid=str(update.effective_user.id)
    text=update.message.text
    if not text: return
    if text=="🎁 هدية يومية": return await daily_gift(update,context)
    if text=="🔗 رابط دعوتي": return await invite_link(update,context)
    if text=="💎 نقاطي": return await points_cmd(update,context)
    if text in ["بورانا","بوتاتنا","تلاقي 💙","ميزات 🚀","الاحصائيات 📊","اذاعة","🗑️ حذف آخر إذاعة","ستارت","المدونة","نقاطي","تمويل أعضاء","بوتاتنا","قناة التمويل"]:
        if "بوتاتنا" in text: return await update.message.reply_text("🤖 بوتاتنا:\nhttps://t.me/FFZZ5", reply_markup=get_keyboard(uid))
        return await update.message.reply_text("✅ تم", reply_markup=get_keyboard(uid))

    # --- هنا الذكاء الاصطناعي ---
    if not client:
        return await update.message.reply_text("❌ مفتاح Groq غير موجود في Railway! ضيف GROQ_API_KEY", reply_markup=get_keyboard(uid))

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        all_mem=load_json(MEMORY_FILE).get(uid,[])
        msgs=[{"role":"system","content":"أنت Gotchat، مساعد ذكي يتكلم عربي. جاوب باختصار ومفيد."}]
        for m in all_mem[-6:]:
            msgs.append({"role":m["role"],"content":m["content"]})
        msgs.append({"role":"user","content":text})

        comp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=msgs, temperature=0.7)
        reply = comp.choices[0].message.content

        save_memory(uid,"user",text)
        save_memory(uid,"assistant",reply)
        await update.message.reply_text(reply, reply_markup=get_keyboard(uid))
    except Exception as e:
        logging.error(f"Groq Error: {e}")
        await update.message.reply_text(f"⚠️ خطأ AI: {e}\n\nتأكد من GROQ_API_KEY صحيح", reply_markup=get_keyboard(uid))

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    print("main.py V15.1 READY - AI FIXED")
    app.run_polling()

if __name__=="__main__": main()
