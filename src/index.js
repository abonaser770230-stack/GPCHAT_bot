export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/webhook" && request.method === "POST") {
      const update = await request.json();
      if (update.message) {
        await handleMessage(update.message, env);
      }
      return new Response("ok");
    }
    return new Response("GPChat Bot Running ✅");
  }
}

async function handleMessage(msg, env) {
  const chatId = msg.chat.id;
  const text = msg.text || "";
  const userId = msg.from.id.toString();
  const BOT_TOKEN = env.BOT_TOKEN;
  const ADMIN_KEY = env.ADMIN_KEY;

  // /start
  if (text === "/start") {
    await sendMessage(BOT_TOKEN, chatId, `
مرحبا بك في GPChat Bot 🤖

الاوامر:
/blog - عرض اخر تدوينات
/subscribe - الاشتراك
/help - المساعدة
    `);
  }

  // /help
  else if (text === "/help") {
    await sendMessage(BOT_TOKEN, chatId, `
اوامر المستخدم:
/start - بدء
/blog - المدونة
/subscribe - اشتراك

اوامر الادمن:
/admin [الكود] - تسجيل ادمن
/post [العنوان | النص] - اضافة تدوينة
/users - عدد المستخدمين
    `);
  }

  // /admin
  else if (text.startsWith("/admin ")) {
    const key = text.split(" ")[1];
    if (key === ADMIN_KEY) {
      await env.DB.put(`admin:${userId}`, "true");
      await sendMessage(BOT_TOKEN, chatId, "✅ تم اضافتك كـ ادمن");
    } else {
      await sendMessage(BOT_TOKEN, chatId, "❌ الكود خطأ");
    }
  }

  // /subscribe
  else if (text === "/subscribe") {
    const isSub = await env.DB.get(`sub:${userId}`);
    if (isSub) {
      await sendMessage(BOT_TOKEN, chatId, "انت مشترك بالفعل ✅");
    } else {
      await env.DB.put(`sub:${userId}`, "active");
      await sendMessage(BOT_TOKEN, chatId, "✅ تم اشتراكك بنجاح!");
    }
  }

  // /blog
  else if (text === "/blog") {
    const posts = await env.DB.list({prefix: "post:"});
    if (posts.keys.length === 0) {
      await sendMessage(BOT_TOKEN, chatId, "لا توجد تدوينات بعد");
    } else {
      let msg = "📝 اخر التدوينات:\n\n";
      for (let key of posts.keys.slice(-5)) {
        const post = await env.DB.get(key.name);
        msg += post + "\n\n---\n\n";
      }
      await sendMessage(BOT_TOKEN, chatId, msg);
    }
  }

  // /post للادمن
  else if (text.startsWith("/post ")) {
    const isAdmin = await env.DB.get(`admin:${userId}`);
    if (!isAdmin) return await sendMessage(BOT_TOKEN, chatId, "❌ انت لست ادمن");

    const content = text.replace("/post ", "");
    const postId = Date.now();
    await env.DB.put(`post:${postId}`, content);
    await sendMessage(BOT_TOKEN, chatId, "✅ تم نشر التدوينة");
  }

  // /users للادمن
  else if (text === "/users") {
    const isAdmin = await env.DB.get(`admin:${userId}`);
    if (!isAdmin) return;
    const users = await env.DB.list({prefix: "sub:"});
    await sendMessage(BOT_TOKEN, chatId, `عدد المشتركين: ${users.keys.length}`);
  }
}

async function sendMessage(token, chatId, text) {
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({chat_id: chatId, text})
  });
}
