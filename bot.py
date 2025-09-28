import logging
import json
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ayatquran-bot")

# تحميل التوكن من البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على متغير BOT_TOKEN. أضفه في إعدادات Render.")

# تحميل بيانات القرآن من الملف المحلي
try:
    with open("surah_data.json", "r", encoding="utf-8") as f:
        quran_data = json.load(f)
    logger.info("✅ تم تحميل القرآن من الملف المحلي.")
except Exception as e:
    logger.error(f"❌ فشل تحميل ملف surah_data.json: {e}")
    quran_data = []

# إنشاء تطبيق Flask
app = Flask(__name__)

# إنشاء تطبيق Telegram
application = Application.builder().token(BOT_TOKEN).build()

# دالة بدء المحادثة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌸 مرحبًا! أرسل لي اسم سورة أو رقم آية لأعرضها لك من القرآن الكريم.\n\n"
        "مثال:\n- الفاتحة\n- البقرة 255\n- الناس"
    )

# دالة البحث عن الآية
async def get_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    logger.info(f"📩 المستخدم أرسل: {query}")

    found = False
    response = ""

    for surah in quran_data:
        surah_name = surah.get("name", "").replace("سورة ", "").strip()
        surah_id = str(surah.get("id", "")).strip()  # رقم السورة (id)

        # التحقق هل المستخدم كتب اسم السورة أو رقمها
        if query.startswith(surah_name) or query.startswith(surah_id):
            parts = query.split()
            if len(parts) > 1:  # المستخدم كتب رقم آية بعد السورة
                try:
                    ayah_number = int(parts[1])
                    verses = surah.get("verses", [])
                    for verse in verses:
                        if verse.get("id") == ayah_number:
                            response = f"📖 {surah['name']} - الآية {ayah_number}\n\n{verse['text']}"
                            found = True
                            break
                except ValueError:
                    pass
            else:  # المستخدم كتب فقط اسم السورة
                verses = surah.get("verses", [])
                response = f"📘 {surah['name']}\n\n" + "\n".join(
                    [f"{v['id']}. {v['text']}" for v in verses[:5]]
                )
                response += "\n\n... تم عرض أول 5 آيات فقط."
                found = True
            break

    if not found:
        response = "❌ لم أجد السورة أو الآية المطلوبة. حاول مثل:\n- البقرة 255\n- الكافرون\n- الفاتحة"

    await update.message.reply_text(response)

# تعريف الهاندلرز (Handlers)
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ayah))

# Webhook route لتحديثات Telegram
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok", 200

# الصفحة الرئيسية لاختبار السيرفر
@app.route("/", methods=["GET"])
def home():
    return "✅ Quran Bot is Running!"

# تشغيل التطبيق على Render
if __name__ == "__main__":
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
