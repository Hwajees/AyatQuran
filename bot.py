import os
import json
import logging
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# إعداد السجلّات (Logs)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ayatquran-bot")

# تحميل بيانات القرآن من ملف JSON أو من الإنترنت
QURAN_DATA = None
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"

def load_quran_data():
    global QURAN_DATA
    try:
        if os.path.exists("surah_data.json"):
            with open("surah_data.json", "r", encoding="utf-8") as f:
                QURAN_DATA = json.load(f)
                logger.info("✅ تم تحميل القرآن من الملف المحلي.")
        else:
            logger.info(f"⏳ تحميل بيانات القرآن من: {QURAN_URL}")
            response = requests.get(QURAN_URL)
            QURAN_DATA = response.json()
            logger.info("✅ تم تحميل القرآن من الإنترنت.")
    except Exception as e:
        logger.error(f"❌ فشل تحميل بيانات القرآن: {e}")
        QURAN_DATA = []

load_quran_data()

# إعداد بوت التلغرام
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على متغير BOT_TOKEN في البيئة.")

application = Application.builder().token(BOT_TOKEN).build()

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌸 مرحبًا! أرسل لي اسم سورة أو رقم آية لأعرضها لك من القرآن الكريم.")

async def get_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    result = None

    # البحث بالاسم أو الرقم
    for surah in QURAN_DATA:
        if surah["name"].replace("سورة ", "") == query or surah["name"] == query or str(surah["number"]) == query:
            result = f"📖 {surah['name']}\n\n"
            for ayah in surah["ayahs"][:5]:  # عرض أول 5 آيات فقط
                result += f"{ayah['number']}. {ayah['text']}\n"
            break

    if result:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ لم أجد السورة أو الآية المطلوبة. حاول مرة أخرى.")

# إضافة المعالجات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ayah))

# إنشاء Flask للتعامل مع Webhook
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ البوت يعمل على Render!", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook_handler():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)

        # تهيئة التطبيق قبل المعالجة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.initialize())  # ✅ الحل هنا
        loop.run_until_complete(application.process_update(update))
        return "ok", 200

    except Exception as e:
        logger.error(f"❌ خطأ أثناء المعالجة: {e}", exc_info=True)
        return "error", 500


if __name__ == "__main__":
    # تعيين Webhook عند التشغيل المحلي
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
