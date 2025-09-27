import os
import requests
import asyncio
import re
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------------------
# تحميل بيانات القرآن من JSON
# ---------------------------
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
print(f"⏳ تحميل بيانات القرآن من: {QURAN_URL}")
try:
    response = requests.get(QURAN_URL)
    response.raise_for_status()
    quran_data = response.json()
    print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")
except Exception as e:
    print(f"❌ فشل تحميل ملف القرآن من الرابط: {e}")
    quran_data = []

# ---------------------------
# إعداد التوكن والتطبيق
# ---------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على التوكن في المتغيرات البيئية")

print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:10]}********")

# إنشاء Flask app و Telegram application
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ---------------------------
# دالة مساعدة لتنظيف الاسم
# ---------------------------
def normalize_surah_name(name: str) -> str:
    name = re.sub(r'[^\w\s]', '', name)  # إزالة الرموز
    name = name.replace("سورة", "").strip().lower()  # إزالة كلمة "سورة"
    return name

# ---------------------------
# الأوامر
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت آيات القرآن الكريم!\n\n"
        "📖 طريقة الاستخدام:\n"
        "أرسل اسم السورة متبوعًا برقم الآية، مثل:\n\n"
        "البقرة 255\n"
        "الكهف 10\n"
        "يوسف 4"
    )

async def get_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # تجاهل أوامر /start أو أي أمر آخر
    if text.startswith("/"):
        return

    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("❌ اكتب بصيغة صحيحة مثل: البقرة 255")
        return

    surah_name_input, ayah_number = parts[0], parts[1]

    if not ayah_number.isdigit():
        await update.message.reply_text("❌ رقم الآية يجب أن يكون رقمًا.")
        return

    normalized_input = normalize_surah_name(surah_name_input)

    for surah in quran_data:
        normalized_surah_name = normalize_surah_name(surah["name"])
        if normalized_surah_name == normalized_input:
            for ayah in surah["verses"]:
                if int(ayah["id"]) == int(ayah_number):
                    await update.message.reply_text(f"📖 {ayah['text']}")
                    return
            await update.message.reply_text("⚠️ لم أجد هذه الآية في السورة.")
            return

    await update.message.reply_text("⚠️ لم أجد السورة المطلوبة. تأكد من الاسم.")

# ---------------------------
# تسجيل الأوامر
# ---------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ayah))

# ---------------------------
# تهيئة التطبيق عند بدء السيرفر
# ---------------------------
async def init_telegram_app():
    await application.initialize()
    await application.start()
    webhook_url = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    print(f"🌍 تم تعيين Webhook على: {webhook_url}")

# ---------------------------
# Flask Webhook Routes
# ---------------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت يعمل على Render بنجاح!"

# ---------------------------
# بدء التشغيل
# ---------------------------
if __name__ == "__main__":
    asyncio.run(init_telegram_app())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))