# main.py V17 - FIXED MODELS 2026 + ANTI-DUPLICATE + ADMIN INFINITE
import os, json, logging, time, asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter
from groq import Groq

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API") or os.getenv("GROQ_KEY")
ADMIN_ID = str(os.getenv("ADMIN_ID") or "").strip()

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
USER_STATES = {}

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,"r",encoding="utf-8") as j: return json.load(j)
    except: return {}
def save_json(f,d):
    try:
        with open(f,"w",encoding="utf-8") as j: json.dump(d,j,ensure_ascii=False,indent=2)
    except: pass

def is_admin(uid):
    return ADMIN_ID and str(uid) == ADMIN_ID

def get_keyboard(uid):
    if is_admin(uid):
        return ReplyKeyboardMarkup([["اذاعة 📢","الاحصائيات 📊"],["🎁 هدية يومية","🔗 رابط دعوتي"],["💎 نقاطي","🗑️ حذف آخر إذاعة"],["إلغاء ❌"]], resize_keyboard=True)
    return ReplyKeyboardMarkup([["🎁 هدية يومية","🔗 رابط دعوتي"],["💎 نقاطي","🤖 بوتاتنا"]], resize_keyboard=True)

def save_memory(uid, role, content):
    all_mem=load_json("memory.json"); mem=all_mem.get(str(uid),[])
    mem=[m for m in mem if time.time()-m.get("time",0)<86400]
    mem.append({"role":role,"content":content,"time":time.time()})
    all_mem[str(uid)]=mem[-20:]; save_json("memory.json",all_mem)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id); points=load_json("points.json")
    args=context.args
    if args and args[0].startswith("ref_"):
        ref_id=args[0].replace("ref_","")
        if ref_id!=uid and uid not in points:
            r=points.get(ref_id,{"points":0}); r["points"]=r.get("points",0)+50; points[ref_id]=r
            try: await context.bot.send_message(int(ref_id), f"🎉 شخص دخل برابطك +50 نقطة! نقاطك: {r['points']}")
            except: pass
    if uid not in points: points[uid]={"points":10,"name":update.effective_user.first_name}
    save_json("points.json",points)
    bot_info=await context.bot.get_me(); link=f"https://t.me/{bot_info.username}?start=ref_{uid}"
    pts_text="♾️ لا نهائي 👑 (إدمن)" if is_admin(uid) else f"{points[uid]['points']} نقطة"
    await update.message.reply_text(f"أهلاً يا {update.effective_user.first_name} 👋\n\n🤖 أنا Gotchat الذكي\n💎 رصيدك: {pts_text}\n🔗 رابطك:\n`{link}`\n\nID الخاص بك: `{uid}`\nADMIN_ID في السيرفر: `{ADMIN_ID}`", parse_mode="Markdown", reply_markup=get_keyboard(uid))

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid=str(update.effective_user.id); text=update.message.text.strip()

    if text=="إلغاء ❌":
        USER_STATES.pop(uid,None)
        return await update.message.reply_text("❌ تم الإلغاء.", reply_markup=get_keyboard(uid))
    if USER_STATES.get(uid)=="WAITING_BROADCAST":
        if not is_admin(uid): return
        USER_STATES.pop(uid,None); points=load_json("points.json")
        sent_msg=await update.message.reply_text("📢 جاري الإذاعة..."); sent_list=[]; success=0; failed=0
        for user_id in points.keys():
            try:
                msg=await context.bot.copy_message(chat_id=int(user_id), from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
                sent_list.append({"chat_id":int(user_id),"message_id":msg.message_id}); success+=1; await asyncio.sleep(0.05)
            except RetryAfter as e: await asyncio.sleep(e.retry_after)
            except: failed+=1
        save_json("broadcasts.json",{"last_broadcast":sent_list})
        return await sent_msg.edit_text(f"✅ تم: {success} فشل: {failed}")

    if text=="اذاعة 📢" and is_admin(uid):
        USER_STATES[uid]="WAITING_BROADCAST"; return await update.message.reply_text("أرسل الإذاعة الآن:")
    if text=="🎁 هدية يومية":
        if is_admin(uid): return await update.message.reply_text("👑 انت إدمن - نقاطك لا نهائية أصلاً ♾️", reply_markup=get_keyboard(uid))
        daily=load_json("daily.json"); now=time.time()
        if now-daily.get(uid,0)<86400: return await update.message.reply_text("⏳ أخذت هديتك اليوم")
        pts=load_json("points.json"); pts.setdefault(uid,{"points":0})["points"]+=5; save_json("points.json",pts); daily[uid]=now; save_json("daily.json",daily)
        return await update.message.reply_text(f"🎁 +5 نقاط! رصيدك: {pts[uid]['points']}")
    if text=="🔗 رابط دعوتي":
        me=await context.bot.get_me(); return await update.message.reply_text(f"https://t.me/{me.username}?start=ref_{uid}")
    if text=="💎 نقاطي":
        if is_admin(uid): return await update.message.reply_text("💎 رصيدك: ♾️ لا نهائي 👑", reply_markup=get_keyboard(uid))
        return await update.message.reply_text(f"💎 نقاطك: {load_json('points.json').get(uid,{}).get('points',0)}")
    if text=="الاحصائيات 📊" and is_admin(uid):
        p=load_json("points.json"); return await update.message.reply_text(f"👥 المستخدمين: {len(p)}")
    if text=="🗑️ حذف آخر إذاعة" and is_admin(uid):
        bc=load_json("broadcasts.json").get("last_broadcast",[]); c=0
        for m in bc:
            try: await context.bot.delete_message(m["chat_id"],m["message_id"]); c+=1; await asyncio.sleep(0.02)
            except: pass
        save_json("broadcasts.json",{"last_broadcast":[]}); return await update.message.reply_text(f"🗑️ حذف {c}")

    if not client: return await update.message.reply_text("GROQ_KEY ناقص")
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        mem=load_json("memory.json").get(uid,[])
        msgs=[{"role":"system","content":"You are Gotchat, Arabic AI assistant. Reply in user's language, concise."}]
        for m in mem[-6:]: msgs.append({"role":m["role"],"content":m["content"]})
        msgs.append({"role":"user","content":text})
        # الموديل الجديد الشغال 2026
        comp=await asyncio.to_thread(lambda: client.chat.completions.create(model="openai/gpt-oss-20b", messages=msgs, temperature=0.7, max_tokens=800))
        reply=comp.choices[0].message.content
        save_memory(uid,"user",text); save_memory(uid,"assistant",reply)
        await update.message.reply_text(reply, reply_markup=get_keyboard(uid))
    except Exception as e:
        logging.error(f"Groq Error: {e}")
        await update.message.reply_text(f"⚠️ خطأ: {e}", reply_markup=get_keyboard(uid))

def main():
    if not BOT_TOKEN: print("BOT_TOKEN Missing!"); return
    print(f"ADMIN_ID loaded: {ADMIN_ID}")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    print("🚀 Bot V17 Running with gpt-oss-20b")
    # هذا يحل التكرار نهائياً
    app.run_polling(drop_pending_updates=True, close_loop=False, stop_signals=None, allowed_updates=Update.ALL_TYPES)

if __name__=="__main__": main()
