import os
import logging
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("quran-bot")

# تحميل بيانات السور والآيات
with open("quran.json", "r", encoding="utf-8") as f:
    quran_data = json.load(f)

# إنشاء تطبيق Flask
app = Flask(__name__)

# جلب التوكن من متغير البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")

# إنشاء تطبيق البوت
application = Application.builder().token(BOT_TOKEN).build()


# ======= دالة لجلب الآية =======
def get_ayah(surah_name, ayah_number):
    # البحث عن السورة
    surah = next((s for s in quran_data if s["name"].strip() == surah_name.strip()), None)
    if not surah:
        return None  # السورة غير موجودة

    ayahs = surah["ayahs"]

    # التأكد أن رقم الآية موجود فعلاً
    if 1 <= ayah_number <= len(ayahs):
        return ayahs[ayah_number - 1]["text"]

    # إذا كانت الآية خارج النطاق
    return None


# ======= دالة /start =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحبًا بك في بوت الآيات القرآنية.\nاكتب اسم السورة ورقم الآية مثل:\n\nالبقرة 255")


# ======= دالة استقبال الرسائل =======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"📩 تم استلام رسالة: {text}")

    # تقسيم النص إلى اسم السورة ورقم الآية
    parts = text.split()
    if len(parts) != 2:
        return  # 🚫 تجاهل أي رسالة غير منسقة بشكل صحيح

    surah_name = parts[0]
    try:
        ayah_number = int(parts[1])
    except ValueError:
        return  # 🚫 تجاهل إذا لم يكن الرقم صالحًا

    # جلب نص الآية
    ayah_text = get_ayah(surah_name, ayah_number)

    # ✅ الرد فقط إذا وُجدت الآية فعلاً
    if ayah_text:
        await update.message.reply_text(ayah_text)
    else:
        # 🚫 لا يرد إذا كانت السورة أو الآية غير موجودة
        return


# ======= إعداد المعالجات =======
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ======= Webhook =======
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    logger.info(f"📩 تم استلام تحديث جديد: {update.to_dict()}")
    application.update_queue.put_nowait(update)
    return "OK", 200


# ======= الصفحة الرئيسية =======
@app.route("/")
def home():
    return "✅ Quran Bot is running."


# ======= تشغيل البوت =======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
