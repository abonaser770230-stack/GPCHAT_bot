import express from 'express';
import TelegramBot from 'node-telegram-bot-api';
import { GoogleGenerativeAI } from '@google/generative-ai';
import axios from 'axios';
import xml2js from 'xml2js';
import fs from 'fs';

const app = express();
app.use(express.json());

const TOKEN = process.env.BOT_TOKEN;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const ADMIN_ID = 5529009159;
const CHANNEL_ID = -1002539926427;
const CHANNEL_LINK = "https://t.me/SmartAI_Ar";
const BLOG_URL = "https://sohailaegency.blogspot.com";
const SETTINGS_FILE = "/tmp/settings.json";

const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
const text_model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
const image_model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

const bot = new TelegramBot(TOKEN, { webHook: false });
let settings = loadSettings();
let user_step = {};

function loadSettings() {
    const defaultSettings = {"force_msg": "⚠️ **اشتراك اجباري**\n\nلازم تشترك في @SmartAI_Ar", "ad_text": "🔥 تابعونا @SmartAI_Ar", "bots_list": "🤖 *بوتاتنا:*\n@SmartAI_Ar", "ad_interval": 24};
    if (fs.existsSync(SETTINGS_FILE)) {
        return JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf-8'));
    }
    saveSettings(defaultSettings);
    return defaultSettings;
}
function saveSettings(s) { fs.writeFileSync(SETTINGS_FILE, JSON.stringify(s, null, 4), 'utf-8'); }

async function checkSub(uid) {
    try { const member = await bot.getChatMember(CHANNEL_ID, uid); return ['member', 'administrator', 'creator'].includes(member.status); }
    catch { return false; }
}
function sendJoin(cid) {
    const markup = { inline_keyboard: [[{text: "🔔 اشترك", url: CHANNEL_LINK}], [{text: "✅ تحقق", callback_data: "check_sub"}]] };
    bot.sendMessage(cid, settings.force_msg, { reply_markup: markup, parse_mode: "Markdown" });
}
function adminPanel() {
    return { inline_keyboard: [
        [{text: "✏️ رسالة الاشتراك", callback_data: "edit_force"}, {text: "📢 نشر اعلان", callback_data: "send_ad"}],
        [{text: "📝 تعديل الاعلان", callback_data: "edit_ad"}, {text: "🤖 قائمة البوتات", callback_data: "edit_bots"}],
        [{text: "⏰ وقت الاعلان", callback_data: "edit_time"}]
    ]};
}

// Webhook
app.post(`/${TOKEN}`, (req, res) => {
    bot.processUpdate(req.body);
    res.sendStatus(200);
});
app.get('/', (req, res) => res.send("Bot Running on Render"));

// Commands
bot.onText(/\/admin/, async (msg) => {
    if (msg.from.id !== ADMIN_ID) return;
    bot.sendMessage(msg.chat.id, "👑 *لوحة تحكم الادمن*", { reply_markup: adminPanel(), parse_mode: "Markdown" });
});

bot.on('callback_query', async (c) => {
    if (c.data === "check_sub") {
        if (await checkSub(c.from.id)) { bot.answerCallbackQuery(c.id, {text: "✅ تم"}); bot.deleteMessage(c.message.chat.id, c.message_id); bot.sendMessage(c.message.chat.id, "اهلا! ارسل سؤالك مباشرة"); }
        else { bot.answerCallbackQuery(c.id, {text: "❌ اشترك اول", show_alert: true}); }
        return;
    }
    if (c.from.id !== ADMIN_ID) return;
    const txt = {"edit_force": "ارسل رسالة الاشتراك", "send_ad": "ارسل الاعلان", "edit_ad": `الحالي:\n${settings.ad_text}`, "edit_bots": `الحالي:\n${settings.bots_list}`, "edit_time": `الحالي: ${settings.ad_interval} ساعة`};
    if (c.data === "send_ad") { bot.sendMessage(CHANNEL_ID, settings.ad_text); bot.answerCallbackQuery(c.id, "✅ تم"); }
    else if (txt[c.data]) { bot.sendMessage(c.message.chat.id, txt[c.data]); user_step[c.from.id] = c.data; }
});

bot.on('message', async (msg) => {
    if (msg.from.id in user_step && !msg.text.startsWith('/')) {
        const s = user_step[msg.from.id];
        if (s === "edit_force") settings.force_msg = msg.text;
        if (s === "edit_ad") settings.ad_text = msg.text;
        if (s === "edit_bots") settings.bots_list = msg.text;
        if (s === "edit_time") settings.ad_interval = parseInt(msg.text) || 24;
        saveSettings(settings); bot.reply(msg.chat.id, "✅ تم"); delete user_step[msg.from.id]; return;
    }
    if (msg.text === '/start') {
        if (!await checkSub(msg.from.id)) return sendJoin(msg.chat.id);
        bot.reply(msg.chat.id, "مرحبا 👋\nارسل سؤالك مباشرة\n/ai\n/image\n/blog\n/bots");
    }
    if (msg.text.startsWith('/ai ')) {
        if (!await checkSub(msg.from.id)) return sendJoin(msg.chat.id);
        askGemini(msg, msg.text.replace("/ai ", ""));
    }
    if (msg.text === '/blog') {
        if (!await checkSub(msg.from.id)) return sendJoin(msg.chat.id);
        try {
            const r = await axios.get(BLOG_URL + "/feeds/posts/default?max-results=3");
            const result = await xml2js.parseStringPromise(r.data);
            let t = "📰 *اخر 3 مقالات*\n\n";
            result.feed.entry.slice(0,3).forEach(x => t += `🔹 [${x.title[0]}](${x.link[0].$.href})\n\n`);
            bot.sendMessage(msg.chat.id, t, {parse_mode: "Markdown", disable_web_page_preview: true});
        } catch { bot.sendMessage(msg.chat.id, "❌ خطأ"); }
    }
    if (msg.text === '/bots') {
        if (!await checkSub(msg.from.id)) return sendJoin(msg.chat.id);
        bot.sendMessage(msg.chat.id, settings.bots_list, {parse_mode: "Markdown"});
    }
    if (!msg.text.startsWith('/') && !(msg.from.id in user_step)) {
        if (!await checkSub(msg.from.id)) return sendJoin(msg.chat.id);
        askGemini(msg, msg.text);
    }
});

async function askGemini(msg, question) {
    bot.sendChatAction(msg.chat.id, 'typing');
    const m = await bot.sendMessage(msg.chat.id, "🤖 جاري التفكير...");
    try {
        const response = await text_model.generateContent(`جاوب باختصار وبمباشرة: ${question}`);
        bot.editMessageText(response.response.text() + "\n\n@SmartAI_Ar", {chat_id: msg.chat.id, message_id: m.message_id});
    } catch(e) { bot.editMessageText(`❌ خطأ: ${e}`, {chat_id: msg.chat.id, message_id: m.message_id}); }
}

// الصور في Gemini API تحتاج دفع. خليتها نص مؤقت
bot.onText(/\/image (.+)/, async (msg, match) => {
    if (!await checkSub(msg.from.id)) return sendJoin(msg.chat.id);
    bot.reply(msg.chat.id, "❌ توليد الصور في Gemini يحتاج API مدفوع. استخدم نص بدلها");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on ${PORT}`));
