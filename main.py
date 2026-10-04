async def chat_handler(update: Update, context):
    if not update.message or not update.message.text: 
        return
    
    uid = str(update.effective_user.id)
    text = update.message.text.strip()

    # معالجة الأزرار العادية أولاً
    if text == "🎁 هدية يومية": return await daily_gift(update, context)
    if text == "🔗 رابط دعوتي": return await invite_link(update, context)
    if text == "💎 نقاطي": return await points_cmd(update, context)
    
    if text in ["بورانا", "بوتاتنا", "تلاقي 💙", "ميزات 🚀", "الاحصائيات 📊", "اذاعة", "🗑️ حذف آخر إذاعة"]:
        if text == "بوتاتنا": 
            return await update.message.reply_text("🤖 بوتاتنا:\nhttps://t.me/FFZZ5", reply_markup=get_keyboard(uid))
        return await update.message.reply_text("✅ تم", reply_markup=get_keyboard(uid))

    # التحقق من وجود مفتاح API
    if not client:
        return await update.message.reply_text("❌ لم يتم التعرف على مفتاح GROQ_API_KEY في السيرفر!", reply_markup=get_keyboard(uid))

    # إرسال جاري الكتابة
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    
    try:
        all_mem = load_json(MEMORY_FILE).get(uid, [])
        msgs = [{"role": "system", "content": "أنت Gotchat، مساعد ذكي يتكلم عربي. جاوب باختصار ومفيد."}]
        
        for m in all_mem[-6:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        msgs.append({"role": "user", "content": text})

        # تشغيل طلب Groq في thread منفصل لمنع تجميد البوت
        loop = asyncio.get_event_loop()
        comp = await loop.run_in_executor(
            None, 
            lambda: client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=msgs, 
                temperature=0.7
            )
        )
        
        reply = comp.choices[0].message.content

        save_memory(uid, "user", text)
        save_memory(uid, "assistant", reply)
        await update.message.reply_text(reply, reply_markup=get_keyboard(uid))

    except Exception as e:
        logging.error(f"Groq Error: {e}")
        # إرسال تفاصيل الخطأ لتدمير تعليق "يكتب..." ومعرفة الخلل فوراً
        await update.message.reply_text(f"⚠️ حصل خطأ أثناء الاتصال بالذكاء الاصطناعي:\n`{e}`", parse_mode="Markdown", reply_markup=get_keyboard(uid))
