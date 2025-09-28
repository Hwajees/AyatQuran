import os
import json
import httpx
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ayatquran-bot")

# إعداد المتغيرات
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# تحميل القرآن
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
logger.info(f"⏳ تحميل بيانات القرآن من: {QURAN_URL}")
quran_data = httpx.get(QURAN_URL).json()
logger.info(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# إنشاء تطبيق Telegram
application = Application.builder().token(BOT_TOKEN).build()

# تخزين event loop الرئيسي
telegram_loop = asyncio.get_event_loop()

# Flask app
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot is running."

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook_handler():
    """استقبال التحديثات من Telegram"""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        # تنفيذ التحديث داخل الحدث الرئيسي بأمان
        asyncio.run_coroutine_threadsafe(application.process_update(update), telegram_loop)
    except Exception as e:
        logger.error(f"❌ خطأ في المعالجة: {e}")
        return "error", 500
    return "ok", 200

# أوامر البوت
async def start(update, context):
    text = (
        "👋 *مرحبًا بك في بوت آيات القرآن الكريم*\n\n"
        "📖 اكتب اسم السورة ورقم الآية مثل:\n"
        "`البقرة 255`\n\n"
        "وسيعرض لك البوت الآية المطلوبة بإذن الله.\n\n"
        "✳️ مثال آخر:\n"
        "`الكهف 10`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update, context):
    msg = update.message.text.strip()
    parts = msg.split()

    if len(parts) != 2:
        await update.message.reply_text("❌ يرجى كتابة اسم السورة ورقم الآية فقط مثل:\n`الكهف 10`", parse_mode="Markdown")
        return

    surah_name, verse_str = parts
    surah_name = surah_name.replace("سورة", "").strip().lower()

    # البحث عن السورة في ملف JSON
    surah = next((s for s in quran_data if s["name"].replace("سورة", "").strip().lower() == surah_name), None)
    if not surah:
        await update.message.reply_text("⚠️ لم أتعرف على اسم السورة.")
        return

    try:
        verse_number = int(verse_str)
        verse = next((v for v in surah["verses"] if v["id"] == verse_number), None)
        if not verse:
            await update.message.reply_text("⚠️ لم أجد هذه الآية في السورة.")
            return

        await update.message.reply_text(f"📖 {surah['name']} - آية {verse_number}:\n\n{verse['text']}")
    except ValueError:
        await update.message.reply_text("❌ رقم الآية غير صحيح.")

# إضافة المعالجات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# تعيين الـ Webhook
async def set_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

if __name__ == "__main__":
    telegram_loop.run_until_complete(set_webhook())
    logger.info("✅ Telegram Application initialized and webhook set.")
    app.run(host="0.0.0.0", port=10000)
