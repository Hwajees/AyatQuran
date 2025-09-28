import os
import json
import httpx
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجل (Logs)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ayatquran-bot")

# تحميل التوكن من المتغير البيئي
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# إنشاء تطبيق Flask
app = Flask(__name__)

# تحميل ملف القرآن من الإنترنت
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"

try:
    response = httpx.get(QURAN_URL, timeout=30)
    response.raise_for_status()
    quran_data = response.json()
    logger.info(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")
except Exception as e:
    logger.error(f"❌ فشل تحميل القرآن: {e}")
    quran_data = []

# إنشاء تطبيق البوت
application = Application.builder().token(BOT_TOKEN).build()

# 🧩 معالجة الأمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم*.\n\n"
        "📖 يمكنك إرسال اسم السورة ورقم الآية مثل:\n"
        "`البقرة 255`\n\n"
        "وسأرسل لك الآية المطلوبة بإذن الله.\n\n"
        "🔎 مثال آخر:\n"
        "`الكهف 10`\n\n"
        "✨ فقط أرسل اسم السورة متبوعًا برقم الآية."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# 🔍 دالة البحث الذكي عن السورة
def find_surah_by_name(name):
    clean_name = name.strip().lower().replace("سورة", "").replace(" ", "")
    for surah in quran_data:
        if surah["name"].replace(" ", "").lower() == clean_name:
            return surah
    return None

# 📜 معالجة الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        parts = text.split()

        if len(parts) != 2:
            await update.message.reply_text(
                "⚠️ أرسل اسم السورة متبوعًا برقم الآية مثل:\n`البقرة 255`",
                parse_mode="Markdown"
            )
            return

        surah_name, ayah_number = parts[0], parts[1]

        if not ayah_number.isdigit():
            await update.message.reply_text("⚠️ رقم الآية يجب أن يكون عددًا صحيحًا.", parse_mode="Markdown")
            return

        surah = find_surah_by_name(surah_name)
        if not surah:
            await update.message.reply_text("❌ لم أجد هذه السورة. تأكد من كتابة الاسم بشكل صحيح.", parse_mode="Markdown")
            return

        ayah_number = int(ayah_number)
        ayat = surah["verses"]

        if ayah_number < 1 or ayah_number > len(ayat):
            await update.message.reply_text(f"⚠️ هذه السورة تحتوي على {len(ayat)} آيات فقط.", parse_mode="Markdown")
            return

        ayah_text = ayat[ayah_number - 1]["text"]
        response = f"📖 *سورة {surah['name']} - آية {ayah_number}:*\n\n{ayah_text}"
        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ خطأ أثناء المعالجة: {e}")
        await update.message.reply_text("حدث خطأ أثناء المعالجة، حاول مرة أخرى لاحقًا.")

# ✅ إضافة المعالجات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🌐 نقطة استقبال Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook_handler():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.create_task(application.process_update(update))
    except Exception as e:
        logger.exception(f"❌ خطأ أثناء المعالجة: {e}")
        return "error", 500
    return "ok", 200

# 🔹 صفحة فحص بسيطة
@app.route("/", methods=["GET"])
def home():
    return "✅ Quran Bot is running", 200

# 🚀 تشغيل التطبيق محليًا (في Render يتم استخدام gunicorn)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
