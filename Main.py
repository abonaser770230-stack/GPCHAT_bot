import telebot
import requests
import threading
import json
import os
from flask import Flask

# ================== غير ال 3 دول بس ==================
BOT_TOKEN = "8086458846:AAFXtMvK1wV7x3n3gH7aHvXK5aJ9bK9bK9b"
GEMINI_API_KEY = "AQ.Ab8RN6IWuXyDLT99C6rGylP_wa_EHbCJIO7riHaBYE-Bdui9zg"
SECRET_KEY = "7713033"
BOT_NAME = "GPChat' شات جي بي تي"
# ======================================================

USERS_FILE = "users.json"
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

subscribed_users = load_users()

def check_subscription(user_id):
    return user_id in subscribed_users

# ==== الرابط اللي صفحة بلوجر هتستدعيه بعد الاعلان ====
@app.route('/activate/<int:user_id>/<key>')
def activate(user_id, key):
    if key == SECRET_KEY:
        subscribed_users.add(user_id)
        save_users(subscribed_users)
        return "OK"
    return "ERROR", 403

@app.route('/')
def home():
    return "GPChat Bot is Running"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        bot.send_message(user_id, f"مرحبا بيك في {BOT_NAME} 😎\nاسألني اي شي")
    else:
       # غير رابط مدونتك هنا
        blog_link = f"https://sohailaegency.blogspot.com/2026/08/blog-post_12.html}"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("تفعيل البوت من المدونة", url=blog_link))
        bot.send_message(user_id,
            f"اهلا في {BOT_NAME}\n\n"
            f"عشان تستخدم البوت لازم تدخل المدونة وتشاهد الاعلان الاول 👇",
            reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        bot.reply_to(message, "لازم تفعل من المدونة الاول")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    reply = ask_gemini(message.text)
    bot.reply_to(message, reply)

def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, json=data, timeout=30)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "حصل خطأ. حاول تاني"

def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8080)
