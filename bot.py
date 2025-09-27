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

response = requests.get(QURAN_URL)
if response.status_code != 200:
    print("❌ فشل تحميل ملف القرآن من الرابط.")
    exit()

quran_data = response.json()
print("✅ تم تحميل القرآن بنجاح! عدد السور:", len(quran_data))
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
# إعداد البوت
# ==========================
application = Application.builder().token(BOT_TOKEN).build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحبًا بك في بوت القرآن الكريم.\nأرسل اسم السورة ورقم الآية مثل:\n\nالبقرة 255")

# الرسائل العادية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ أرسل اسم السورة ورقم الآية فقط مثل:\n\nالبقرة 255")
            return

        sura_name, ayah_number = parts[0], int(parts[1])

        sura = quran_dict.get(sura_name)
        if not sura:
            await update.message.reply_text("❌ لم أجد السورة. تأكد من كتابة الاسم الصحيح بالعربية.")
            return

        ayahs = sura["ayahs"]
        if ayah_number < 1 or ayah_number > len(ayahs):
            await update.message.reply_text(f"❌ رقم الآية غير صحيح. هذه السورة تحتوي على {len(ayahs)} آيات.")
            return

        ayah_text = ayahs[ayah_number - 1]["text"]
        await update.message.reply_text(f"📖 {sura_name} - آية {ayah_number}:\n\n{ayah_text}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ: {e}")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==========================
# Flask Webhook endpoint
# ==========================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/")
def home():
    return "✅ Quran Bot is running with Webhook!"

# ==========================
# إعداد Webhook عند التشغيل
# ==========================
@app.before_first_request
def init_webhook():
    url = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    print(f"🌍 إعداد Webhook على: {url}")
    application.bot.set_webhook(url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
