import os
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
    ContextTypes,
    filters
)

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quran-bot")

# تحميل ملف السور
try:
    with open("surah_data.JSON", "r", encoding="utf-8") as f:
        quran_data = json.load(f)
        logger.info("✅ تم تحميل بيانات السور")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل ملف السور: {e}")
    quran_data = []

# إنشاء Flask
app = Flask(__name__)

# قراءة التوكن من البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في متغيرات البيئة")

# إنشاء تطبيق التيليجرام
application = Application.builder().token(BOT_TOKEN).build()

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في بوت آيات القرآن الكريم!\n\n"
        "أرسل اسم السورة متبوعًا برقم الآية مثل:\n\n"
        "📖 البقرة 255\n📖 الكهف 10"
    )

def find_ayah(surah_name, ayah_id):
    surah_name = surah_name.strip().replace("ال", "").replace("أ", "ا").replace("ة", "ه")
    for surah in quran_data:
        name_clean = surah["name"].replace("ال", "").replace("أ", "ا").replace("ة", "ه")
        if surah_name in name_clean or name_clean in surah_name:
            for verse in surah["verses"]:
                if str(verse["id"]) == str(ayah_id):
                    return f"﴿{verse['text']}﴾\n\n📖 سورة {surah['name']} - آية {verse['id']}"
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        match = re.match(r"([\u0621-\u064A\s]+)\s+(\d+)", text)
        if not match:
            await update.message.reply_text("❗ أرسل اسم السورة متبوعًا برقم الآية مثل: البقرة 255")
            return

        surah_name, ayah_id = match.groups()
        result = find_ayah(surah_name, ayah_id)

        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("❌ لم أجد هذه الآية. تأكد من الاسم والرقم.")
    except Exception as e:
        logger.error(f"⚠️ خطأ أثناء معالجة الرسالة: {e}")
        await update.message.reply_text("حدث خطأ غير متوقع 😔")

# ربط الأوامر
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Event loop ثابت
loop = asyncio.get_event_loop()

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        logger.info(f"📩 تم استلام تحديث جديد: {data}")
        asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    except Exception as e:
        logger.error(f"❌ خطأ في المعالجة: {e}")
    return "OK", 200

@app.route("/")
def home():
    return "✅ بوت آيات القرآن الكريم يعمل على Render بنجاح!"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🚀 بدء السيرفر على المنفذ {port}")
    app.run(host="0.0.0.0", port=port)
