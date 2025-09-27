import os
import json
import logging
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلّات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تحميل التوكن من البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على توكن البوت!")

# تحميل بيانات القرآن من JSON
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
response = requests.get(QURAN_URL)
if response.status_code != 200:
    raise ValueError("❌ فشل تحميل ملف القرآن من الرابط.")

quran_data = response.json()
logger.info(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# إنشاء تطبيق Flask
app = Flask(__name__)

# إنشاء تطبيق Telegram bot
application = Application.builder().token(BOT_TOKEN).build()


# === دوال البوت ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحباً بك في بوت آيات القرآن!\nاكتب اسم السورة ورقم الآية مثل:\nالبقرة 255")

def find_verse(surah_name, verse_number):
    for surah in quran_data:
        if surah["name"] == surah_name:
            for verse in surah["verses"]:
                if verse["id"] == int(verse_number):
                    return verse["text"]
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) != 2:
        await update.message.reply_text("❌ اكتب بصيغة صحيحة مثل: البقرة 255")
        return

    surah_name, verse_number = parts
    verse = find_verse(surah_name, verse_number)

    if verse:
        await update.message.reply_text(f"📖 {surah_name} - آية {verse_number}\n\n{verse}")
    else:
        await update.message.reply_text("❌ لم أجد السورة أو الآية. تأكد من الكتابة الصحيحة بالعربية.")


# === ربط الأوامر والمعالجات ===
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# === Flask Routes ===

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_update():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
    except Exception as e:
        print(f"❌ خطأ أثناء معالجة التحديث: {e}")
        return "Internal Server Error", 500
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "✅ البوت يعمل الآن ويستقبل الرسائل عبر Telegram!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))