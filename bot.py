import logging
import json
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ayatquran-bot")

# جلب التوكن من البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على متغير BOT_TOKEN في بيئة Render.")

# تحميل بيانات القرآن
try:
    with open("surah_data.json", "r", encoding="utf-8") as f:
        quran_data = json.load(f)
    logger.info("✅ تم تحميل ملف surah_data.json بنجاح.")
except Exception as e:
    logger.error(f"❌ فشل تحميل surah_data.json: {e}")
    quran_data = []

# إنشاء Flask app
app = Flask(__name__)

# إنشاء Telegram app
application = Application.builder().token(BOT_TOKEN).build()

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌸 مرحبًا بك في بوت القرآن الكريم!\n"
        "أرسل اسم سورة أو رقم آية لعرضها.\n\n"
        "مثال:\n- الفاتحة\n- البقرة 255\n- الكوثر"
    )

# البحث عن السورة أو الآية
async def get_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    logger.info(f"📩 المستخدم أرسل: {query}")

    found = False
    response = ""

    for surah in quran_data:
        surah_name = surah.get("name", "").replace("سورة ", "").strip()
        surah_id = str(surah.get("id", "")).strip()

        # تطابق اسم أو رقم السورة
        if query.startswith(surah_name) or query.startswith(surah_id):
            parts = query.split()
            if len(parts) > 1:  # رقم آية
                try:
                    ayah_number = int(parts[1])
                    for verse in surah.get("verses", []):
                        if verse.get("id") == ayah_number:
                            response = f"📖 {surah['name']} - الآية {ayah_number}\n\n{verse['text']}"
                            found = True
                            break
                except ValueError:
                    pass
            else:  # فقط السورة
                verses = surah.get("verses", [])
                response = f"📘 {surah['name']}\n\n" + "\n".join(
                    [f"{v['id']}. {v['text']}" for v in verses[:5]]
                )
                response += "\n\n... تم عرض أول 5 آيات فقط."
                found = True
            break

    if not found:
        response = "❌ لم أجد السورة أو الآية المطلوبة. حاول مثل:\n- البقرة 255\n- الكافرون\n- الفاتحة"

    await update.message.reply_text(response)

# إضافة Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ayah))

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok", 200

# الصفحة الرئيسية
@app.route("/", methods=["GET"])
def home():
    return "✅ Quran Bot is Live!"

# التشغيل على Render
if __name__ == "__main__":
    async def main():
        WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
        await application.initialize()
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"🌍 Webhook تم تعيينه على: {WEBHOOK_URL}")
        await application.start()
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    asyncio.run(main())
