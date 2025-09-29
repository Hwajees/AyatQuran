import json
import logging
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تحميل ملف القرآن الكريم
QURAN_FILE = "surah_data.JSON"  # ✅ تأكد أن الملف بنفس الاسم تمامًا
try:
    with open(QURAN_FILE, "r", encoding="utf-8") as f:
        quran_data = json.load(f)
    logger.info(f"✅ تم تحميل {QURAN_FILE} بنجاح.")
except Exception as e:
    logger.error(f"❌ فشل تحميل ملف {QURAN_FILE}: {e}")
    quran_data = []

# إعداد Flask
app = Flask(__name__)

# استيراد التوكن من متغير البيئة
import os
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ لم يتم العثور على متغير البيئة BOT_TOKEN. أضفه في إعدادات Render.")

# إنشاء تطبيق التلغرام
application = Application.builder().token(TOKEN).build()

# حلقة asyncio ثابتة لتفادي الخطأ RuntimeError('Event loop is closed')
loop = asyncio.get_event_loop()

# دالة البحث عن الآية
def find_ayah(surah_name, ayah_id):
    surah_name = surah_name.strip().replace("ال", "").replace("أ", "ا").replace("ة", "ه")

    for surah in quran_data:
        name_clean = surah["name"].replace("ال", "").replace("أ", "ا").replace("ة", "ه")
        if surah_name in name_clean or name_clean in surah_name:
            for verse in surah["verses"]:
                if str(verse["id"]) == str(ayah_id):
                    return f"﴿{verse['text']}﴾\n\n📖 سورة {surah['name']} - آية {verse['id']}"
    return None

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم*\n\n"
        "📖 لاستخدام البوت، أرسل اسم السورة متبوعًا برقم الآية، مثل:\n"
        "▪️ البقرة 255\n"
        "▪️ آل عمران 8\n\n"
        "سيقوم البوت بإرسال الآية المطلوبة بإذن الله 🌿"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# معالجة الرسائل
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.match(r"([\u0621-\u064A\s]+)\s+(\d+)", text)
    if not match:
        await update.message.reply_text("❗ أرسل اسم السورة متبوعًا برقم الآية، مثل: البقرة 255")
        return

    surah_name, ayah_id = match.groups()
    result = find_ayah(surah_name, ayah_id)

    if result:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("❌ لم أجد هذه الآية، تحقق من اسم السورة ورقم الآية.")

# ربط الأوامر والمعالجات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# مسار webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)

        async def process_update():
            # تأكد من تهيئة التطبيق مرة واحدة فقط
            if not application._initialized:
                await application.initialize()
            await application.process_update(update)

        # استخدم حلقة asyncio ثابتة
        asyncio.run_coroutine_threadsafe(process_update(), loop)

    except Exception as e:
        logger.error(f"❌ خطأ أثناء معالجة التحديث: {e}")

    return "OK", 200

# المسار الرئيسي
@app.route("/")
def index():
    return "بوت القرآن الكريم يعمل بنجاح 🌙"

# تشغيل السيرفر
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
