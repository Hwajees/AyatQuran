import logging
import json
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

# 📘 تحميل ملف surah_data.JSON فقط
try:
    with open("surah_data.JSON", "r", encoding="utf-8") as f:
        surahs = json.load(f)
    logging.info("✅ تم تحميل surah_data.JSON بنجاح.")
except FileNotFoundError:
    logging.error("❌ لم يتم العثور على surah_data.JSON. تأكد من رفعه إلى الجذر.")
    raise SystemExit("ملف surah_data.JSON مفقود")
except json.JSONDecodeError as e:
    logging.error(f"❌ خطأ في تنسيق surah_data.JSON: {e}")
    raise SystemExit("خطأ في surah_data.JSON")

# 🔑 إعداد التوكن
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ لم يتم العثور على التوكن في متغيرات البيئة.")

# إعداد السجلّات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quran-bot")

# 🕌 تطبيع الأسماء لتسهيل البحث
def normalize_name(name: str) -> str:
    name = name.strip().replace("ة", "ه")
    name = re.sub(r"[اأإآ]", "ا", name)
    name = name.replace("ال", "")
    return name

# 🔍 البحث عن السورة
def find_surah(user_input: str):
    normalized_query = normalize_name(user_input)
    for surah in surahs:
        surah_name = normalize_name(surah["name"])
        if surah_name == normalized_query:
            return surah
    return None

# 📖 استخراج الآية
def get_ayah_text(surah, ayah_number):
    for verse in surah["verses"]:
        if verse["id"] == ayah_number:
            return verse["text"]
    return None

# 🎯 أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم*.\n\n"
        "📖 لاستخدام البوت:\n"
        "أرسل اسم السورة ثم رقم الآية، مثلًا:\n"
        "`البقرة 2`\n"
        "`ق 5`\n\n"
        "سيقوم البوت بعرض الآية المطلوبة بإذن الله 🌿"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# 💬 عند استقبال رسالة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        await update.message.reply_text("❌ أرسل اسم السورة ثم رقم الآية، مثل: `البقرة 2`", parse_mode="Markdown")
        return

    surah_name, ayah_number = parts[0], int(parts[1])
    surah = find_surah(surah_name)

    if not surah:
        await update.message.reply_text("⚠️ لم أجد هذه السورة. تأكد من الاسم.")
        return

    ayah_text = get_ayah_text(surah, ayah_number)

    if not ayah_text:
        await update.message.reply_text(f"⚠️ لا توجد آية رقم {ayah_number} في سورة {surah['name']}.")
        return

    response = f"📖 *سورة {surah['name']} - آية {ayah_number}:*\n\n{ayah_text}"
    await update.message.reply_text(response, parse_mode="Markdown")

# ⚙️ إعداد التطبيق
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 📡 Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)

        # ✅ التهيئة قبل المعالجة (هنا كان الخطأ)
        asyncio.run(application.initialize())
        asyncio.run(application.process_update(update))
    except Exception as e:
        logger.exception(e)
    return "OK", 200

@app.route("/")
def home():
    return "✅ البوت يعمل بنجاح على Render."

if __name__ == "__main__":
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
