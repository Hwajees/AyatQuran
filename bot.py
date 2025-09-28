import json
import re
import logging
import asyncio
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


# إعداد السجل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quran-bot")

# قراءة التوكن
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم تعيين متغير BOT_TOKEN في Render.")

# إنشاء التطبيق
application = Application.builder().token(BOT_TOKEN).build()

# إنشاء تطبيق Flask
app = Flask(__name__)


# تحميل بيانات السور
def load_surah_data():
    try:
        with open("surah_data.JSON", "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("✅ تم تحميل surah_data.JSON بنجاح.")
        return data
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل surah_data.JSON: {e}")
        return []

surah_data = load_surah_data()

# 🔹 دالة لتبسيط الاسم (للتعامل مع اختلافات الكتابة)
def normalize_name(name):
    name = name.strip().lower()
    name = re.sub(r'[اأإآ]', 'ا', name)  # توحيد الألف
    name = name.replace('ة', 'ه')        # توحيد التاء المربوطة
    name = re.sub(r'^ال', '', name)      # حذف "ال" من البداية
    return name

# 🔹 البحث عن السورة بناءً على الاسم (غير دقيق)
def find_surah(user_input):
    normalized_query = normalize_name(user_input)
    for surah in surah_data:
        normalized_name = normalize_name(surah["name"])
        if normalized_query == normalized_name:
            return surah
    return None

# 🔹 /start — رسالة ترحيبية فقط
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🌿 مرحبًا بك في *بوت آيات القرآن الكريم*.\n\n"
        "📘 للاستخدام:\n"
        "أرسل اسم السورة متبوعًا برقم الآية.\n\n"
        "🕋 أمثلة:\n"
        "- البقرة 2\n"
        "- بقرة 2\n"
        "- الفاتحه 7\n\n"
        "⚠️ ملاحظة: لا يهم دقة التشكيل أو كتابة (ال)."
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# 🔹 التعامل مع الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    # التحقق من الصيغة الصحيحة (سورة + رقم آية)
    parts = user_input.split()
    if len(parts) < 2:
        await update.message.reply_text("⚠️ أرسل اسم السورة متبوعًا برقم الآية، مثل:\nالبقرة 2")
        return

    surah_name = " ".join(parts[:-1])
    try:
        ayah_number = int(parts[-1])
    except ValueError:
        await update.message.reply_text("⚠️ رقم الآية يجب أن يكون رقمًا صحيحًا.")
        return

    surah = find_surah(surah_name)
    if not surah:
        await update.message.reply_text("❌ لم أجد السورة المطلوبة. تأكد من كتابة الاسم بشكل قريب من الصحيح.")
        return

    # البحث عن الآية المطلوبة
    for verse in surah["verses"]:
        if verse["id"] == ayah_number:
            await update.message.reply_text(
                f"📖 سورة {surah['name']} ({surah['no']})\n"
                f"آية {verse['id']}:\n\n{verse['text']}"
            )
            return

    await update.message.reply_text("⚠️ لم أجد هذه الآية في السورة.")

# 🔹 إضافة الهاندلرز
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔹 المسار الرئيسي لـ Render
@app.route("/")
def home():
    return "✅ Quran bot is running!"

# 🔹 Webhook لمعالجة التحديثات
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)

    async def process():
        try:
            await application.initialize()
            await application.process_update(update)
        except Exception as e:
            logging.error(f"❌ خطأ أثناء معالجة التحديث: {e}")

    # تشغيل المعالجة في الخلفية دون إغلاق الحلقة
    loop = asyncio.get_event_loop()
    loop.create_task(process())

    return "OK", 200

# 🔹 بدء التشغيل
if __name__ == "__main__":
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
