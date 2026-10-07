# main.py V18 - LATEST GROQ 2026 - FINAL
import os, json, logging, time, asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter
from groq import Groq

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API") or os.getenv("GROQ_KEY") or "").strip()
ADMIN_ID = str(os.getenv("ADMIN_ID") or "").strip()

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
USER_STATES = {}

MODELS = ["openai/gpt-oss-20b", "llama-4-scout-17b-16e-instruct", "openai/gpt-oss-120b"]

def load_json(f):
    if not os.path.exists(f): return {}
    try: return json.load(open(f,"r",encoding="utf-8"))
    except: return {}
def save_json(f,d):
    try: json.dump(d, open(f,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except: pass

def is_admin(uid): return ADMIN_ID and str(uid)==str(ADMIN_ID)
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
            r=points.get(ref_id,{"points":0}); r["points"]+=50; points[ref_id]=r
            try: await context.bot.send_message(int(ref_id), f"🎉 +50 نقطة! شخص دخل برابطك")
            except: pass
    if uid not in points: points[uid]={"points":10,"name":update.effective_user.first_name}
    save_json("points.json",points)
    me=await context.bot.get_me(); link=f"https://t.me/{me.username}?start=ref_{uid}"
    pts="♾️ لا نهائي 👑" if is_admin(uid) else f"{points[uid]['points']}"
    await update.message.reply_text(f"أهلاً {update.effective_user.first_name} 👋\n💎 رصيدك: {pts}\n🔗 رابطك: `{link}`", parse_mode="Markdown", reply_markup=get_keyboard(uid))

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid=str(update.effective_user.id); text=update.message.text.strip()

    if text=="إلغاء ❌":
        USER_STATES.pop(uid,None)
        return await update.message.reply_text("تم الإلغاء ❌", reply_markup=get_keyboard(uid))
    if USER_STATES.get(uid)=="WAITING_BROADCAST" and is_admin(uid):
        USER_STATES.pop(uid,None); pts=load_json("points.json")
        m=await update.message.reply_text("📢 جاري الإرسال..."); lst=[]; ok=0; fail=0
        for u in pts:
            try:
                msg=await context.bot.copy_message(int(u), update.effective_chat.id, update.message.message_id)
                lst.append({"chat_id":int(u),"message_id":msg.message_id}); ok+=1; await asyncio.sleep(0.05)
            except RetryAfter as e: await asyncio.sleep(e.retry_after)
            except: fail+=1
        save_json("broadcasts.json",{"last_broadcast":lst})
        return await m.edit_text(f"✅ تم {ok} فشل {fail}")

    if text=="اذاعة 📢" and is_admin(uid): USER_STATES[uid]="WAITING_BROADCAST"; return await update.message.reply_text("أرسل الإذاعة:")
    if text=="🎁 هدية يومية":
        if is_admin(uid): return await update.message.reply_text("👑 نقاطك لا نهائية ♾️", reply_markup=get_keyboard(uid))
        daily=load_json("daily.json")
        if time.time()-daily.get(uid,0)<86400: return await update.message.reply_text("⏳ أخذتها اليوم")
        p=load_json("points.json"); p.setdefault(uid,{"points":0})["points"]+=5; save_json("points.json",p); daily[uid]=time.time(); save_json("daily.json",daily)
        return await update.message.reply_text(f"🎁 +5! رصيدك {p[uid]['points']}")
    if text=="🔗 رابط دعوتي": me=await context.bot.get_me(); return await update.message.reply_text(f"https://t.me/{me.username}?start=ref_{uid}")
    if text=="💎 نقاطي": return await update.message.reply_text(f"💎 رصيدك: {'♾️ لا نهائي 👑' if is_admin(uid) else load_json('points.json').get(uid,{}).get('points',0)}", reply_markup=get_keyboard(uid))
    if text=="الاحصائيات 📊" and is_admin(uid): return await update.message.reply_text(f"👥 {len(load_json('points.json'))} مستخدم")
    if text=="🗑️ حذف آخر إذاعة" and is_admin(uid):
        bc=load_json("broadcasts.json").get("last_broadcast",[]); c=0
        for x in bc:
            try: await context.bot.delete_message(x["chat_id"],x["message_id"]); c+=1
            except: pass
        save_json("broadcasts.json",{"last_broadcast":[]}); return await update.message.reply_text(f"🗑️ حذف {c}")

    if not client: return await update.message.reply_text("GROQ_KEY ناقص")
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    mem=load_json("memory.json").get(uid,[])
    msgs=[{"role":"system","content":"You are Gotchat, helpful Arabic AI. Reply in user's language."}]
    for m in mem[-6:]: msgs.append({"role":m["role"],"content":m["content"]})
    msgs.append({"role":"user","content":text})

    last_err=""
    for model in MODELS:
        try:
            comp=await asyncio.to_thread(lambda m=model: client.chat.completions.create(model=m, messages=msgs, temperature=0.7, max_tokens=800))
            reply=comp.choices[0].message.content
            save_memory(uid,"user",text); save_memory(uid,"assistant",reply)
            return await update.message.reply_text(reply, reply_markup=get_keyboard(uid))
        except Exception as e:
            last_err=str(e); logging.warning(f"Model {model} failed: {e}"); continue

    await update.message.reply_text(f"⚠️ كل الموديلات فشلت:\n{last_err}")

def main():
    if not BOT_TOKEN: print("BOT_TOKEN Missing"); return
    print(f"ADMIN_ID={ADMIN_ID} MODELS={MODELS}")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    print("🚀 V18 Running")
    app.run_polling(drop_pending_updates=True, close_loop=False, stop_signals=None)

if __name__=="__main__": main()
