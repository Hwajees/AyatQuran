import os
import json
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= إعدادات التسجيل =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ayatquran-bot")

# ================= إعداد البوت =================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "ضع_توكن_البوت_هنا"
app = Flask(__name__)

# تحميل بيانات القرآن من JSON
try:
    with open("surah_data.json", "r", encoding="utf-8") as f:
        quran_data = json.load(f)
    logger.info("✅ تم تحميل ملف surah_data.json بنجاح.")
except Exception as e:
    logger.error(f"❌ فشل تحميل ملف surah_data.json: {e}")
    quran_data = []

# بناء التطبيق
application = Application.builder().token(BOT_TOKEN).build()

# ================= دوال البحث =================
def find_surah_by_name(name):
    for surah in quran_data:
        if surah["name"] == name.strip():
            return surah
    return None

def get_ayah_text(surah, ayah_number):
    for ayah in surah["verses"]:
        if ayah["id"] == ayah_number:
            return ayah["text"]
    return None

# ================= الأوامر =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا 👋 أرسل اسم السورة أو رقمها أو السورة مع رقم الآية.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # إذا كان المستخدم كتب فقط رقم السورة
    if text.isdigit():
        surah_id = int(text)
        surah = next((s for s in quran_data if s["id"] == surah_id), None)
        if surah:
            await update.message.reply_text(f"سورة {surah['name']}")
        else:
            await update.message.reply_text("لم يتم العثور على السورة.")
        return

    # إذا كتب اسم السورة فقط
    surah = find_surah_by_name(text)
    if surah:
        first_ayah = surah["verses"][0]["text"]
        await update.message.reply_text(f"سورة {surah['name']}\n\n{first_ayah}")
        return

    # إذا كتب (اسم السورة + رقم الآية)
    parts = text.split()
    if len(parts) == 2 and parts[1].isdigit():
        surah_name = parts[0]
        ayah_num = int(parts[1])
        surah = find_surah_by_name(surah_name)
        if surah:
            ayah_text = get_ayah_text(surah, ayah_num)
            if ayah_text:
                await update.message.reply_text(f"{surah_name} - آية {ayah_num}\n\n{ayah_text}")
            else:
                await update.message.reply_text("لم يتم العثور على رقم الآية في هذه السورة.")
        else:
            await update.message.reply_text("لم يتم العثور على السورة.")
        return

    await update.message.reply_text("الرجاء إرسال اسم السورة أو رقمها أو السورة متبوعة برقم الآية.")

# ================= ربط المعالجات =================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ================= نقطة الدخول =================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # 🔹 إصلاح الخطأ: التأكد من تهيئة التطبيق قبل المعالجة
    async def process():
        if not application.initialized:
            await application.initialize()
        await application.process_update(update)

    asyncio.run(process())
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "بوت آيات القرآن يعمل ✅"

if __name__ == "__main__":
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    logger.info(f"🌍 تعيين Webhook على: {WEBHOOK_URL}")
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
