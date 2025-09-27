import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ==========================
# إعداد Flask
# ==========================
app = Flask(__name__)

# ==========================
# تحميل بيانات القرآن
# ==========================
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
print("⏳ تحميل بيانات القرآن من:", QURAN_URL)

try:
    response = requests.get(QURAN_URL)
    response.raise_for_status()
    quran_data = response.json()
    print("✅ تم تحميل القرآن بنجاح! عدد السور:", len(quran_data))
except Exception as e:
    print("❌ فشل تحميل ملف القرآن:", e)
    exit()

quran_dict = {sura["name"]: sura for sura in quran_data}

# ==========================
# إعداد التوكن
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("🚨 لم يتم العثور على التوكن! أضفه في إعدادات Render باسم BOT_TOKEN")
    exit()

print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:8]}********")

# ==========================
# إنشاء تطبيق Telegram Bot
# ==========================
application = Application.builder().token(BOT_TOKEN).build()

# ==========================
# المعالجات
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في *بوت القرآن الكريم!*\n\n"
        "📖 أرسل اسم السورة ورقم الآية، مثل:\n"
        "`البقرة 255`",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ أرسل اسم السورة ورقم الآية مثل:\nالبقرة 255")
            return

        sura_name, ayah_number = parts[0], int(parts[1])

        sura = quran_dict.get(sura_name)
        if not sura:
            await update.message.reply_text("❌ لم أجد السورة. تأكد من كتابة الاسم الصحيح بالعربية.")
            return

        ayahs = sura["ayahs"]
        if ayah_number < 1 or ayah_number > len(ayahs):
            await update.message.reply_text(f"❌ رقم الآية غير صحيح. السورة تحتوي على {len(ayahs)} آيات.")
            return

        ayah_text = ayahs[ayah_number - 1]["text"]
        await update.message.reply_text(f"📖 {sura_name} - آية {ayah_number}\n\n{ayah_text}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ: {e}")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==========================
# Webhook
# ==========================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

@app.route("/")
def home():
    return "✅ Quran Bot is running with Webhook!"

# ==========================
# عند بدء التشغيل
# ==========================
@app.before_first_request
def set_webhook():
    webhook_url = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    print(f"🌍 تعيين Webhook على: {webhook_url}")
    import asyncio
    asyncio.run(application.bot.set_webhook(webhook_url))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))