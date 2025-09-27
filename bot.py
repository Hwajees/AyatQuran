import os
import requests
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد التسجيل في السجلات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# قراءة التوكن من المتغيرات البيئية
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("🚨 خطأ: لم يتم العثور على توكن صالح!")
    exit(1)

# رابط بيانات القرآن الكريم
QURAN_JSON_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"

# تحميل بيانات القرآن
print(f"⏳ تحميل بيانات القرآن من: {QURAN_JSON_URL}")
try:
    response = requests.get(QURAN_JSON_URL)
    response.raise_for_status()
    quran_data = response.json()
    print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")
except Exception as e:
    print(f"❌ فشل تحميل ملف القرآن من الرابط.\nالخطأ: {e}")
    exit(1)

# إنشاء تطبيق Flask
app = Flask(__name__)

# إنشاء تطبيق Telegram
application = Application.builder().token(BOT_TOKEN).build()

# ====== دوال البوت ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم*!\n"
        "اكتب مثلًا: `البقرة 255` للحصول على الآية المطلوبة.\n"
        "📖 البوت يدعم كل سور القرآن الكريم.",
        parse_mode="Markdown"
    )

async def get_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("❗ اكتب بصيغة صحيحة مثل: البقرة 255")

        surah_name = parts[0]
        ayah_number = int(parts[1])

        # البحث عن السورة
        surah = next((s for s in quran_data if s["name"] == surah_name or s["transliteration"] == surah_name), None)
        if not surah:
            await update.message.reply_text("❌ لم يتم العثور على اسم السورة.")
            return

        # البحث عن الآية
        ayah = next((a for a in surah["verses"] if a["id"] == ayah_number), None)
        if not ayah:
            await update.message.reply_text("❌ لم يتم العثور على هذه الآية في السورة.")
            return

        # إرسال الآية
        reply = f"📖 *{surah_name} - {ayah_number}*\n\n{ayah['text']}"
        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❗ اكتب بصيغة صحيحة مثل: البقرة 255")

# ====== إعداد الأوامر ======
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ayah))

# ====== Webhook ======
WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"

async def set_webhook():
    """إعداد الـ Webhook بشكل صحيح (مع await)."""
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

# ====== Flask Routes ======
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """تستقبل التحديثات من Telegram."""
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت يعمل بشكل سليم بإذن الله."

# ====== تشغيل التطبيق ======
if __name__ == "__main__":
    # تعيين الـ Webhook عند الإقلاع
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
