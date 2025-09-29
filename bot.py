import json
import logging
import re
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- إعداد السجل ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ---------------- إعداد البوت ---------------- #
TOKEN = os.getenv("BOT_TOKEN", "7179731919:AAHxZw48ElCJSeCVZUpsG-Pe7Z686qTNV6E")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"https://ayatquran.onrender.com/{TOKEN}"

app = Flask(__name__)

# ---------------- تحميل ملف JSON ---------------- #
DATA_FILE = "surah_data.JSON"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        surah_data = json.load(f)
    logger.info(f"✅ تم تحميل {DATA_FILE} بنجاح.")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل {DATA_FILE}: {e}")
    surah_data = []

# ---------------- دوال مساعدة ---------------- #
def normalize_name(name):
    name = name.strip().lower()
    name = re.sub(r'[اأإآ]', 'ا', name)
    name = name.replace('ة', 'ه')
    name = name.replace('ال', '')
    return name

def find_surah(user_input):
    normalized_query = normalize_name(user_input)
    for surah in surah_data:
        if normalize_name(surah["name"]) == normalized_query or normalize_name(surah["name"]).startswith(normalized_query):
            return surah
    return None

# ---------------- معالجات الرسائل ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *مرحبًا بك في بوت آيات القرآن الكريم*\n\n"
        "🔹 أرسل اسم السورة ثم رقم الآية للحصول على نصها.\n"
        "مثال:\n"
        "`البقره 2`\n"
        "`بقره 2`\n"
        "`القرة 2`\n\n"
        "⚠️ لا يهم إن كتبتها بألف أو همزة أو تاء مربوطة."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text("❌ أرسل اسم السورة ثم رقم الآية، مثل:\n`البقره 2`", parse_mode="Markdown")
        return

    surah_name, ayah_number = parts
    surah = find_surah(surah_name)

    if not surah:
        await update.message.reply_text("⚠️ لم أجد سورة بهذا الاسم، تأكد من الكتابة الصحيحة.")
        return

    try:
        ayah_number = int(ayah_number)
    except ValueError:
        await update.message.reply_text("⚠️ رقم الآية يجب أن يكون رقمًا صحيحًا.")
        return

    ayahs = surah.get("ayahs", [])
    for ayah in ayahs:
        if ayah.get("id") == ayah_number:
            await update.message.reply_text(f"📖 *{surah['name']} - آية {ayah_number}:*\n\n{ayah['text']}", parse_mode="Markdown")
            return

    await update.message.reply_text("⚠️ لم أجد آية بهذا الرقم في السورة.")

# ---------------- إنشاء التطبيق ---------------- #
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ---------------- Flask Routes ---------------- #
@app.route("/")
def home():
    return "بوت القرآن يعمل ✅"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    try:
        asyncio.run(application.process_update(update))
    except Exception as e:
        logger.error(f"❌ خطأ أثناء معالجة التحديث: {e}")
    return "OK", 200

# ---------------- التشغيل ---------------- #
if __name__ == "__main__":
    # تهيئة التطبيق قبل التشغيل
    asyncio.run(application.initialize())
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"✅ تم إعداد Webhook على: {WEBHOOK_URL}")

    app.run(host="0.0.0.0", port=PORT)
