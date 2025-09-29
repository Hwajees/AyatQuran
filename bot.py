import os
import json
import logging
import re
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# 🔹 إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 إعداد صفحة Flask للرئيسية حتى يبقى البوت شغال ويعمل مع UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Quran Bot is running!"

def run_flask():
    # تشغيل السيرفر البسيط في خيط منفصل
    app.run(host="0.0.0.0", port=8080)

# تشغيل Flask في خيط مستقل حتى لا يعطل البوت
threading.Thread(target=run_flask).start()

# 🔹 قراءة التوكن والمنفذ
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"

if not BOT_TOKEN:
    raise ValueError("❌ لم يتم تحديد BOT_TOKEN في متغيرات البيئة")

# 🔹 تحميل ملف السور
try:
    with open("surah_data.JSON", "r", encoding="utf-8") as f:
        quran_data = json.load(f)
        logger.info("✅ تم تحميل بيانات السور")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل ملف السور: {e}")
    quran_data = []

# 🔹 دالة إيجاد الآية
def find_ayah(surah_name, ayah_id):
    # تحويل الأرقام العربية إلى إنجليزية
    arabic_to_english = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    ayah_id = str(ayah_id).translate(arabic_to_english)

    surah_name = surah_name.strip().replace("ال", "").replace("أ", "ا").replace("ة", "ه")
    for surah in quran_data:
        name_clean = surah["name"].replace("ال", "").replace("أ", "ا").replace("ة", "ه")
        if surah_name in name_clean or name_clean in surah_name:
            for verse in surah["verses"]:
                if str(verse["id"]) == str(ayah_id):
                    return f"﴿{verse['text']}﴾\n\n📖 سورة {surah['name']} - آية {verse['id']}"
    return None

# 🔹 أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في بوت آيات القرآن الكريم!\n\n"
        "أرسل اسم السورة متبوعًا برقم الآية مثل:\n"
        "📖 البقرة 255\n📖 الكهف 10"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.match(r"([\u0621-\u064A\s]+)\s+([\d٠-٩]+)", text)  # يدعم الأرقام العربية والإنجليزية
    if not match:
        return  # تجاهل أي رسالة لا تطابق النمط

    surah_name, ayah_id = match.groups()
    result = find_ayah(surah_name, ayah_id)

    if result:
        await update.message.reply_text(result)
    # ملاحظة: إذا لم يجد الآية → لا يرد إطلاقًا ✅

# 🔹 إنشاء التطبيق
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔹 التشغيل عبر Webhook مباشرة
if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل البوت على Render باستخدام Webhook ...")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )
