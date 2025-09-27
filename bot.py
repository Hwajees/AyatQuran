import os
import json
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==============================
# إعداد البوت وملف القرآن
# ==============================
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

# قراءة التوكن من متغير البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("🚨 خطأ: لم يتم العثور على توكن صالح!")
    print("❗ تأكد أنك أضفت المتغير BOT_TOKEN في إعدادات Render.")
    exit(1)
else:
    print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:8]}********")

# إنشاء تطبيق Telegram
application = Application.builder().token(BOT_TOKEN).build()

# ==============================
# دالة البحث عن آية
# ==============================
def find_ayah(surah_name, ayah_number):
    for surah in quran_data:
        if surah["name"].strip() == surah_name.strip() or surah["transliteration"].strip().lower() == surah_name.strip().lower():
            for ayah in surah["verses"]:
                if ayah["id"] == int(ayah_number):
                    return f"📖 {surah['name']} - آية {ayah['id']}\n\n{ayah['text']}"
    return None

# ==============================
# أوامر البوت
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم*!\n"
        "أرسل اسم السورة ورقم الآية مثل:\n\n"
        "`البقرة 255`\n"
        "وسأعرض لك الآية مباشرة بإذن الله 🌙",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text("❗ أرسل اسم السورة متبوعًا برقم الآية، مثل:\n`الكهف 10`", parse_mode="Markdown")
        return

    surah_name, ayah_number = parts[0], parts[1]

    if not ayah_number.isdigit():
        await update.message.reply_text("❗ رقم الآية يجب أن يكون عددًا صحيحًا.")
        return

    result = find_ayah(surah_name, ayah_number)
    if result:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("⚠️ لم يتم العثور على السورة أو رقم الآية، تأكد من الكتابة الصحيحة.")

# ==============================
# إعداد Flask لاستقبال Webhook
# ==============================
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/")
def home():
    return "✅ Quran Bot is running with Webhook!", 200

# ==============================
# تشغيل السيرفر وتعيين Webhook
# ==============================
if __name__ == "__main__":
    webhook_url = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    print(f"🌍 تعيين Webhook على: {webhook_url}")

    import asyncio
    asyncio.run(application.bot.set_webhook(webhook_url))

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))