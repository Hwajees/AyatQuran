import logging
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# إعداد السجلّات لتتبع الأخطاء
logging.basicConfig(level=logging.INFO)

# ==========================
# إعدادات البوت
# ==========================
TOKEN = "7179731919:AAHxZw48ElCJSeCVZUpsG-Pe7Z686qTNV6E"
WEBHOOK_URL = "https://ayatquran.onrender.com/" + TOKEN

# ==========================
# تهيئة Flask
# ==========================
app = Flask(__name__)

# ==========================
# دالة لجلب الآية من API
# ==========================
def get_ayah(surah_number, ayah_number):
    try:
        url = f"https://api.alquran.cloud/v1/ayah/{surah_number}:{ayah_number}/ar.alafasy"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data["status"] == "OK":
            ayah_text = data["data"]["text"]
            surah_name = data["data"]["surah"]["name"]
            audio_url = data["data"]["audio"]
            return f"📖 {surah_name} - آية {ayah_number}\n\n{ayah_text}\n\n🎧 {audio_url}"
        else:
            return "⚠️ لم أجد آية بهذا الرقم في السورة."
    except Exception as e:
        logging.error(f"خطأ أثناء جلب الآية: {e}")
        return "❌ حدث خطأ أثناء محاولة جلب الآية."

# ==========================
# أوامر Telegram
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت القرآن الكريم.\n"
        "أرسل رقم السورة ورقم الآية بهذا الشكل:\n\n"
        "مثلاً: 2:255"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if ":" in text:
        try:
            surah, ayah = map(int, text.split(":"))
            result = get_ayah(surah, ayah)
            await update.message.reply_text(result)
        except ValueError:
            await update.message.reply_text("⚠️ الرجاء إدخال الأرقام بهذا الشكل: 2:255")
    else:
        await update.message.reply_text("📘 أرسل رقم السورة والآية بهذا الشكل: 2:255")

# ==========================
# إعداد التطبيق
# ==========================
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==========================
# Webhook
# ==========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put_nowait(update)
    except Exception as e:
        logging.error(f"❌ خطأ أثناء معالجة التحديث: {e}")
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "بوت القرآن يعمل ✅"

# ==========================
# التشغيل
# ==========================
if __name__ == "__main__":
    logging.info("🚀 بدء تشغيل البوت...")
    app.run(host="0.0.0.0", port=10000)