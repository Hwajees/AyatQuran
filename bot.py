import os
import json
import logging
import asyncio
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجل (Logs)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("ayatquran-bot")

# قراءة التوكن من البيئة
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على توكن البوت في المتغيرات البيئية!")

# تحميل ملف القرآن الكريم
QURAN_FILE = "quran.json"
try:
    with open(QURAN_FILE, "r", encoding="utf-8") as f:
        quran_data = json.load(f)
        logger.info("✅ تم تحميل القرآن من الملف المحلي.")
except Exception as e:
    logger.error(f"❌ فشل تحميل ملف {QURAN_FILE}: {e}")
    quran_data = []

# إنشاء تطبيق Flask
app = Flask(__name__)

# إنشاء تطبيق Telegram
application = Application.builder().token(BOT_TOKEN).build()


# 🧩 البحث في السور والآيات
def search_quran(query):
    results = []
    query = query.strip().replace("سورة ", "")

    for surah in quran_data:
        surah_name = surah.get("name", "")
        surah_id = surah.get("id", "")
        verses = surah.get("verses", [])

        # 🔹 إذا كانت الكلمة المدخلة هي اسم السورة
        if query == surah_name or query == surah_name.replace("سورة ", ""):
            text = f"📖 *سورة {surah_name}* (رقمها {surah_id})\n\n"
            for verse in verses:
                verse_id = verse.get("id", "")
                verse_text = verse.get("text", "")
                text += f"{verse_id}. {verse_text}\n"
            results.append(text)
            break  # توقف لأن السورة وجدت

        # 🔹 البحث داخل الآيات
        for verse in verses:
            verse_text = verse.get("text", "")
            verse_id = verse.get("id", "")
            if query in verse_text:
                results.append(f"📖 *سورة {surah_name}* — آية {verse_id}:\n{verse_text}")

    return results


# 🚀 الأوامر
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم*.\n"
        "أرسل اسم السورة أو جزءًا من آية للبحث عنها.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    results = search_quran(query)

    if not results:
        await update.message.reply_text("❌ لم يتم العثور على نتائج. حاول بكتابة اسم السورة أو جزء من آية.")
        return

    # إرسال أول 5 نتائج فقط لتجنب السبام
    for result in results[:5]:
        await update.message.reply_text(result, parse_mode="Markdown")


# ✅ Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# 🌐 إعداد Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "✅ Quran Bot is Running!"


# ⚙️ التشغيل على Render
if __name__ == "__main__":
    async def setup_webhook():
        WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

    asyncio.get_event_loop().run_until_complete(setup_webhook())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
