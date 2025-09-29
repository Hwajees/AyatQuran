import os
import json
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# 🔹 إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 قراءة التوكن و المنفذ
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

# 🔹 تحويل الأرقام العربية إلى إنجليزية
def convert_arabic_numbers(text):
    arabic_to_english = {
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
    }
    for ar, en in arabic_to_english.items():
        text = text.replace(ar, en)
    return text

# 🔹 دالة إيجاد الآية
def find_ayah(surah_name, ayah_id):
    surah_name = surah_name.strip().replace("ال", "").replace("أ", "ا").replace("ة", "ه")
    for surah in quran_data:
        name_clean = surah["name"].replace("ال", "").replace("أ", "ا").replace("ة", "ه")
        if surah_name in name_clean or name_clean in surah_name:
            for verse in surah["verses"]:
                if str(verse["id"]) == str(ayah_id):
                    return f"﴿{verse['text']}﴾\n\n📖 سورة {surah['name']} - آية {verse['id']}"
    return None

# 🔹 أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في بوت آيات القرآن الكريم!\n\n"
        "أرسل اسم السورة متبوعًا برقم الآية مثل:\n"
        "📖 البقرة 255\n📖 الكهف ١٠ (يمكن استخدام الأرقام العربية أيضًا)"
    )

# 🔹 معالجة الرسائل
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # 🟢 تحويل الأرقام العربية إلى إنجليزية
    text = convert_arabic_numbers(text)
    
    # 🧩 استخراج السورة والآية
    match = re.match(r"([\u0621-\u064A\s]+)\s+(\d+)", text)
    if not match:
        return  # ❌ لا يرد إذا لم يطابق النمط
    
    surah_name, ayah_id = match.groups()
    result = find_ayah(surah_name, ayah_id)

    if result:
        await update.message.reply_text(result)
    # ⚠️ إذا لم يجد الآية، لا يرد إطلاقًا

# 🔹 إنشاء التطبيق
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔹 التشغيل عبر Webhook
if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل البوت على Render باستخدام Webhook ...")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )
