import os
import logging
import asyncio
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# جلب التوكن من متغير البيئة
TOKEN = os.getenv("BOT_TOKEN")

# إنشاء التطبيق
application = Application.builder().token(TOKEN).build()

# ========= دوال البوت =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك في بوت آيات القرآن الكريم.\nأرسل اسم السورة ورقم الآية مثل: البقرة 255")

async def get_ayah(surah: str, ayah: str) -> str:
    """جلب الآية من API"""
    try:
        url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar.alafasy"
        response = requests.get(url).json()
        if response["status"] == "OK":
            data = response["data"]
            text = data["text"]
            surah_name = data["surah"]["name"]
            number = data["numberInSurah"]
            return f"﴿{text}﴾\n\n📖 سورة {surah_name} - آية {number}"
        else:
            return "⚠️ لم يتم العثور على الآية. تحقق من السورة أو الرقم."
    except Exception as e:
        logger.error(e)
        return "حدث خطأ أثناء جلب الآية."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) == 2:
        surah, ayah = parts
        result = await get_ayah(surah, ayah)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ أرسل اسم السورة ورقم الآية مثل:\nالبقرة 255")

# إضافة الأوامر والمعالجات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ========= إعداد Flask =========
app = Flask(__name__)

# إنشاء event loop عالمي عند بدء التشغيل
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """نقطة استقبال التحديثات من Telegram"""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)

        async def process_update():
            if not application._initialized:
                await application.initialize()
            await application.process_update(update)

        # استخدام loop العالمي الدائم
        asyncio.run_coroutine_threadsafe(process_update(), loop)

    except Exception as e:
        logger.error(f"❌ خطأ أثناء معالجة التحديث: {e}")

    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "✅ Quran Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    from threading import Thread

    # تشغيل event loop في الخلفية
    def start_loop():
        logger.info("🔁 تشغيل الحدث الدائم asyncio loop ...")
        loop.run_forever()

    Thread(target=start_loop, daemon=True).start()

    logger.info(f"🚀 Running Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
