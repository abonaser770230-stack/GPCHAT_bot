import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI", "feedparser", "flask", "requests", "google-generativeai", "pillow", "schedule"])

import telebot, threading, time, requests, xml.etree.ElementTree as ET, json, os, io
import google.generativeai as genai
from flask import Flask
from threading import Thread
from PIL import Image
import schedule

# ========= الاعدادات - من المتغيرات =========
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = 5529009159
CHANNEL_ID = -1002539926427
CHANNEL_LINK = "https://t.me/SmartAI_Ar"
BLOG_URL = "https://sohailaegency.blogspot.com"
SETTINGS_FILE = "settings.json"

# فعل Gemini
genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel('gemini-1.5-flash')
image_model = genai.GenerativeModel('imagen-3.0-generate-001')

# ========= سيرفر Flask عشان 24/7 =========
app = Flask('')
@app.route('/')
def home(): return "Bot Running 24/7"
def run_server(): app.run(host='0.0.0.0', port=8080)

# ========= تحميل وحفظ الاعدادات =========
def load_settings():
    default = {
        "force_msg": "⚠️ **اشتراك اجباري**\n\nلازم تشترك في قناة SmartAI_Ar عشان تستخدم البوت\nبعد الاشتراك اضغط تحقق",
        "ad_text": "🔥 جديد: اهم شروحات الذكاء الاصطناعي والربح\n@SmartAI_Ar\nhttps://t.me/SmartAI_Ar",
        "bots_list": "🤖 *بوتاتنا:*\n1. @SmartAI_Ar - بوت الذكاء الاصطناعي",
        "ad_interval": 24,
        "last_ad_time": 0
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    save_settings(default)
    return default

def save_settings(s):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(s, f, ensure_ascii=False, indent=4)

settings = load_settings()
bot = telebot.TeleBot(TOKEN)
user_step = {}

# ========= دوال مساعدة =========
def check_sub(uid):
    try: return bot.get_chat_member(CHANNEL_ID, uid).status in ['member', 'administrator', 'creator']
    except: return False

def send_join(cid):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔔 اشترك في القناة", url=CHANNEL_LINK))
    markup.add(telebot.types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
    bot.send_message(cid, settings["force_msg"], reply_markup=markup, parse_mode="Markdown")

def admin_panel():
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    m.add(
        telebot.types.InlineKeyboardButton("✏️ رسالة الاشتراك", callback_data="edit_force"),
        telebot.types.InlineKeyboardButton("📢 نشر اعلان الان", callback_data="send_ad"),
        telebot.types.InlineKeyboardButton("📝 تعديل نص الاعلان", callback_data="edit_ad"),
        telebot.types.InlineKeyboardButton("🤖 قائمة البوتات", callback_data="edit_bots"),
        telebot.types.InlineKeyboardButton("⏰ وقت الاعلان بالساعات", callback_data="edit_time")
    )
    return m

# ========= اوامر الادمن =========
@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id!= ADMIN_ID: return
    bot.send_message(m.chat.id, "👑 *لوحة تحكم الادمن*", reply_markup=admin_panel(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    global settings
    if c.data == "check_sub":
        if check_sub(c.from_user.id):
            bot.answer_callback_query(c.id, "✅ تم التحقق")
            bot.delete_message(c.message.chat.id, c.message_id)
            bot.send_message(c.message.chat.id, "اهلا بيك!\n\n/ai السؤال\n/image الوصف\n/blog - مقالات\n/bots - بوتات")
        else:
            bot.answer_callback_query(c.id, "❌ لسه مش مشترك", show_alert=True)
        return

    if c.from_user.id!= ADMIN_ID: return
    txt = {
        "edit_force": "ارسل رسالة الاشتراك الجديدة",
        "send_ad": "جاري ارسال الاعلان للقناة...",
        "edit_ad": f"النص الحالي:\n{settings['ad_text']}\n\nارسل النص الجديد",
        "edit_bots": f"القائمة الحالية:\n{settings['bots_list']}\n\nارسل القائمة الجديدة",
        "edit_time": f"الوقت الحالي: {settings['ad_interval']} ساعة\nارسل الرقم الجديد"
    }
    if c.data == "send_ad":
        bot.send_message(CHANNEL_ID, settings["ad_text"])
        bot.answer_callback_query(c.id, "✅ تم الارسال")
        return
    if c.data in txt:
        bot.send_message(c.message.chat.id, txt[c.data])
        user_step[c.from_user.id] = c.data

@bot.message_handler(func=lambda m: m.from_user.id in user_step)
def input_admin(m):
    global settings
    s = user_step[m.from_user.id]
    if s == "edit_force": settings["force_msg"] = m.text
    elif s == "edit_ad": settings["ad_text"] = m.text
    elif s == "edit_bots": settings["bots_list"] = m.text
    elif s == "edit_time":
        try: settings["ad_interval"] = int(m.text)
        except: bot.reply_to(m, "❌ ارسل رقم فقط"); return
    save_settings(settings); bot.reply_to(m, "✅ تم الحفظ بنجاح"); del user_step[m.from_user.id]

# ========= اوامر المستخدم =========
@bot.message_handler(commands=['start'])
def start(m):
    if not check_sub(m.from_user.id):
        send_join(m.chat.id)
        bot.send_message(ADMIN_ID, f"🆕 مشترك جديد:\nالاسم: {m.from_user.first_name}\nاليوزر: @{m.from_user.username}\nالايدي: {m.from_user.id}")
        return
    bot.reply_to(m, """مرحبا بيك في بوت SmartAI 🤖

`/ai السؤال` - اسأل الذكاء الاصطناعي
`/image الوصف` - ارسم صورة بالذكاء
`/blog` - اخر 3 مقالات من المدونة
`/bots` - قائمة بوتاتنا
""", parse_mode="Markdown")

@bot.message_handler(commands=['ai'])
def cmd_ai(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    question = m.text.replace("/ai ", "").strip()
    if not question: return bot.reply_to(m, "مثال: `/ai اكتبلي منشور عن الذكاء الاصطناعي`", parse_mode="Markdown")
    msg = bot.reply_to(m, "🤖 بفكر في سؤالك...")
    try:
        response = text_model.generate_content(question)
        full_answer = f"{response.text}\n\n---\n🔥 تابع شروحات AI يومياً: @SmartAI_Ar"
        bot.edit_message_text(full_answer, m.chat.id, msg.message_id)
    except: bot.edit_message_text("❌ حصل خطأ. جرب سؤال ثاني", m.chat.id, msg.message_id)

@bot.message_handler(commands=['image'])
def cmd_image(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    prompt = m.text.replace("/image ", "").strip()
    if not prompt: return bot.reply_to(m, "مثال: `/image تصميم لوجو AI باللون البنفسجي`", parse_mode="Markdown")
    msg = bot.reply_to(m, "🎨 برسم الصورة... انتظر 15 ثانية")
    try:
        response = image_model.generate_content(prompt)
        image = response.images[0]
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        caption = f"✅ تم انشاء الصورة\nالوصف: {prompt}\n\nتابع @SmartAI_Ar"
        bot.send_photo(m.chat.id, img_bytes, caption=caption)
        bot.delete_message(m.chat.id, msg.message_id)
    except: bot.edit_message_text("❌ مقدرتش ارسم. جرب وصف ثاني", m.chat.id, msg.message_id)

@bot.message_handler(commands=['blog'])
def blog(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    try:
        r = requests.get(BLOG_URL + "/feeds/posts/default?max-results=3", timeout=15)
        root = ET.fromstring(r.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        e = root.findall('atom:entry', ns)
        if not e: return bot.send_message(m.chat.id, "مفيش مقالات حاليا")
        t = "📰 *اخر 3 مقالات من المدونة*\n\n"
        for x in e[:3]:
            title = x.find('atom:title', ns).text
            link = x.find('atom:link[@rel="alternate"]', ns).get('href')
            t += f"🔹 [{title}]({link})\n\n"
        bot.send_message(m.chat.id, t, parse_mode="Markdown", disable_web_page_preview=True)
    except: bot.send_message(m.chat.id, "❌ خطأ في جلب المقالات")

@bot.message_handler(commands=['bots'])
def bots(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    bot.send_message(m.chat.id, settings["bots_list"], parse_mode="Markdown")

# ========= الاعلانات التلقائية =========
def ad():
    try: bot.send_message(CHANNEL_ID, settings["ad_text"])
    except Exception as e: print("Ad Error:", e)

def ad_scheduler():
    global settings
    while True:
        now = time.time()
        if now - settings.get("last_ad_time", 0) >= settings["ad_interval"] * 3600:
            ad()
            settings["last_ad_time"] = now
            save_settings(settings)
        time.sleep(60)

# ========= تشغيل البوت =========
if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    # ========= الرد على اي رسالة نصية =========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not check_sub(message.from_user.id): return send_join(message.chat.id)
    
    # لو الادمن بيعدل حاجة نتجاهل
    if message.from_user.id in user_step: return
    
    # اي رسالة عادية هنعتبرها سؤال للذكاء
    question = message.text
    msg = bot.reply_to(message, "🤖 بفكر في سؤالك...")
    try:
        response = text_model.generate_content(question)
        full_answer = f"{response.text}\n\n---\n🔥 تابع شروحات AI يومياً: @SmartAI_Ar"
        bot.edit_message_text(full_answer, message.chat.id, msg.message_id)
    except: 
        bot.edit_message_text("❌ حصل خطأ. جرب سؤال ثاني", message.chat.id, msg.message_id)
    Thread(target=ad_scheduler, daemon=True).start()
    print("البوت شغال...")
    while True:
        try:
            bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("Polling Error:", e)
            time.sleep(5)
