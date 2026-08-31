import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI", "feedparser", "flask", "requests", "google-generativeai", "pillow"])

import telebot, threading, time, requests, xml.etree.ElementTree as ET, json, os, io
import google.generativeai as genai
from flask import Flask
from threading import Thread
from PIL import Image

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = 5529009159
CHANNEL_ID = -1002539926427
CHANNEL_LINK = "https://t.me/SmartAI_Ar"
BLOG_URL = "https://sohailaegency.blogspot.com"
SETTINGS_FILE = "settings.json"

genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel('gemini-3.6-flash') # <-- اخر اصدار
image_model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')

app = Flask('')
@app.route('/')
def home(): return "Bot Running"
def run_server(): app.run(host='0.0.0.0', port=8080)

def load_settings():
    default = {"force_msg": "⚠️ اشتراك اجباري في @SmartAI_Ar", "ad_text": "🔥 @SmartAI_Ar", "bots_list": "🤖 @SmartAI_Ar", "ad_interval": 24, "last_ad_time": 0}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    save_settings(default)
    return default

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
    bot.send_message(cid, settings["force_msg"], reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    bot.reply_to(m, "مرحبا 👋\nارسل سؤالك مباشرة\n/ai\n/image\n/blog\n/bots")

@bot.message_handler(commands=['ai'])
def cmd_ai(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    question = m.text.replace("/ai ", "").strip()
    if not question: return bot.reply_to(m, "مثال: `/ai اشرحلي`", parse_mode="Markdown")
    ask_gemini(m, question)

@bot.message_handler(content_types=['text'])
def handle_text(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    if m.from_user.id in user_step: return
    if m.text.startswith('/'): return
    ask_gemini(m, m.text)

def ask_gemini(m, question):
    msg = bot.reply_to(m, "🤖 بفكر...")
    try:
        response = text_model.generate_content(question)
        bot.edit_message_text(response.text + "\n\n@SmartAI_Ar", m.chat.id, msg.message_id)
    except Exception as e:
        print("GEMINI ERROR:", e)
        bot.edit_message_text(f"❌ خطأ: {e}", m.chat.id, msg.message_id)

@bot.message_handler(commands=['image'])
def cmd_image(m):
    if not check_sub(m.from_user.id): return send_join(m.chat.id)
    prompt = m.text.replace("/image ", "").strip()
    if not prompt: return bot.reply_to(m, "مثال: `/image لوجو`", parse_mode="Markdown")
    msg = bot.reply_to(m, "🎨 برسم...")
    try:
        response = image_model.generate_content(prompt)
        for part in response.parts:
            if part.inline_data:
                image = Image.open(io.BytesIO(part.inline_data.data))
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                bot.send_photo(m.chat.id, img_bytes, caption=prompt)
                bot.delete_message(m.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ فشل الرسم: {e}", m.chat.id, msg.message_id)

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

if __name__ == '__main__':
    Thread(target=run_server, daemon=True).start()
    bot.infinity_polling()
