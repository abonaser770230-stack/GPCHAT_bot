import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI", "feedparser", "flask", "requests", "google-generativeai", "pillow"])

import telebot, threading, time, requests, xml.etree.ElementTree as ET, json, os, io
import google.generativeai as genai
from flask import Flask
from threading import Thread
from PIL import Image

# ========= الاعدادات - كله من المتغيرات =========
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # بنجيبه من Railway
ADMIN_ID = 5529009159
CHANNEL_ID = -1002539926427
CHANNEL_LINK = "https://t.me/SmartAI_Ar"
BLOG_URL = "https://sohailaegency.blogspot.com"
SETTINGS_FILE = "settings.json"

# فعل Gemini
genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel('gemini-1.5-flash')
image_model = genai.GenerativeModel('imagen-3.0-generate-001')

app = Flask('')
@app.route('/')
def home(): return "Bot Running"
def run_server(): app.run(host='0.0.0.0', port=8080)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"force_msg": "⚠️ **اشتراك اجباري**\n\nلازم تشترك في قناة SmartAI_Ar\nبعد الاشتراك اضغط تحقق", "ad_text": "🔥 تابعونا @SmartAI_Ar 🔥\nhttps://t.me/SmartAI_Ar", "bots_list": "🤖 *بوتاتنا:*\n@SmartAI_Ar", "ad_interval": 24, "last_ad_time": 0}

def save_settings(s):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(s, f, ensure_ascii=False, indent=4)

settings = load_settings()
bot = telebot.TeleBot(TOKEN)
user_step = {}

def check_sub(uid):
    try: return bot.get_chat_member(CHANNEL_ID, uid).status in ['member', 'administrator', 'creator']
    except: return False

def send_join(cid):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔔 اشترك", url=CHANNEL_LINK))
    markup.add(telebot.types.InlineKeyboardButton("✅ تحقق", callback_data="check_sub"))
    bot.send_message(cid, settings["force_msg"], reply_markup=markup, parse_mode="Markdown")

def admin_panel():
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    m.add(telebot.types.InlineKeyboardButton("✏️ رسالة الاشتراك", callback_data="edit_force"), telebot.types.InlineKeyboardButton("📢 نشر اعلان", callback_data="send_ad"), telebot.types.InlineKeyboardButton("📝 تعديل الاعلان", callback_data="edit_ad"), telebot.types.InlineKeyboardButton("🤖 قائمة البوتات", callback_data="edit_bots"), telebot.types.InlineKeyboardButton("⏰ وقت الاعلان", callback_data="edit_time"))
    return m

@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id!= ADMIN_ID: return
    bot.send_message(m.chat.id, "👑 لوحة التحكم", reply_markup=admin_panel(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    global settings
    if c.data == "check_sub":
        if check_sub(c.from_user.id): bot.answer_callback_query(c.id, "✅ تم"); bot.send_message(c.message.chat.id, "الاوامر:\n/ai السؤال\n/image الوصف\n/blog - مقالات\n/bots - بوتات")
        else: bot.answer_callback_query(c.id, "❌ اشترك اول", show_alert=True)
        return
    if c.from_user.id!= ADMIN_ID: return
    txt = {"edit_force": "ارسل رسالة الاشتراك", "send_ad": "ارسل الاعلان", "edit_ad": f"الحالي:\n{settings['ad_text']}\nارسل الجديد", "edit_bots": f"الحالي:\n{settings['bots_list']}\nارسل الجديد", "edit_time": f"الحالي: {settings['ad_interval']} ساعة"}
    if c.data in txt: bot.send_message(c.message.chat.id, txt[c.data]); user_step[c.from_user.id] = c.data

@bot.message_handler(func=lambda m: m.from_user.id in user_step)
def input_admin(m):
    global settings
    s = user_step[m.from_user.id]
    if s == "edit_force": settings["force_msg"] = m.text
    elif s == "send_ad": bot.send_message(CHANNEL_ID, m.text); bot.reply_to(m, "✅ تم"); del user_step[m.from_user.id]; return
    elif s == "edit_ad": settings["ad_text"] = m.text
    elif s == "edit_bots": settings["bots_list"] = m.text
    elif s == "edit_time": settings["ad_interval"] = int(m.text)
    save_settings(settings); bot.reply_to(m, "✅ تم"); del user_step[m.from_user.id]

@bot.message_handler(commands=['start'])
def start(m):
    if not check_sub(m.from_user.id): send_join(m.chat.id); bot.send_message(ADMIN_ID, f"🆕 جديد: {m.from_user.first_name} | @{m.from_user.username} | {m.from_user.id}"); return
    bot.reply_to(m, "مرحبا 👋\n/ai السؤال\n/image الوصف\n/blog - مقالات\n/bots - بوتات")

@bot.message_handler(commands=['ai'])
def cmd_ai(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    question = m.text.replace("/ai ", "").strip()
    if not question: return bot.reply_to(m, "مثال: `/ai اشرحلي الربح من تلجرام`", parse_mode="Markdown")
    msg = bot.reply_to(m, "🤖 بفكر...")
    try:
        response = text_model.generate_content(question)
        full_answer = f"{response.text}\n\n---\n🔥 تابعنا: @SmartAI_Ar"
        bot.edit_message_text(full_answer, m.chat.id, msg.message_id)
    except: bot.edit_message_text("❌ خطأ. جرب تاني", m.chat.id, msg.message_id)

@bot.message_handler(commands=['image'])
def cmd_image(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    prompt = m.text.replace("/image ", "").strip()
    if not prompt: return bot.reply_to(m, "مثال: `/image لوجو AI`", parse_mode="Markdown")
    msg = bot.reply_to(m, "🎨 برسم... انتظر 15 ثانية")
    try:
        response = image_model.generate_content(prompt)
        image = response.images[0]
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        caption = f"✅ تم\nالوصف: {prompt}\n\n@SmartAI_Ar"
        bot.send_photo(m.chat.id, img_bytes, caption=caption)
        bot.delete_message(m.chat.id, msg.message_id)
    except: bot.edit_message_text("❌ فشل الرسم. غير الوصف", m.chat.id, msg.message_id)

@bot.message_handler(commands=['blog'])
def blog(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    try:
        r = requests.get(BLOG_URL + "/feeds/posts/default?max-results=3", timeout=15); root = ET.fromstring(r.content); ns = {'atom': 'http://www.w3.org/2005/Atom'}; e = root.findall('atom:entry', ns)
        t = "📰 *اخر 3 مقالات*\n\n"
        for x in e[:3]: t += f"🔹 [{x.find('atom:title', ns).text}]({x.find('atom:link[@rel=\"alternate\"]', ns).get('href')})\n\n"
        bot.send_message(m.chat.id, t, parse_mode="Markdown", disable_web_page_preview=True)
    except: bot.send_message(m.chat.id, "❌ خطأ")

@bot.message_handler(commands=['bots'])
def bots(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    bot.send_message(m.chat.id, settings["bots_list"], parse_mode="Markdown")

def ad():
    try: bot.send_message(CHANNEL_ID, settings["ad_text"])
    except Exception as e: print("Ad Error:", e)

def ad_scheduler():
    global settings
    while True:
        now = time.time()
        if now - settings.get("last_ad_time", 0) >= settings["ad_interval"]
