import os
import json
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== إعداد الأساسيات =====
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ لم يتم العثور على توكن البوت! أضفه في إعدادات Render كـ BOT_TOKEN")
    exit()

bot = Bot(TOKEN)
app = Flask(__name__)

QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"

print(f"⏳ تحميل بيانات القرآن من: {QURAN_URL}")
quran_data = requests.get(QURAN_URL).json()
print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# ===== البحث عن آية =====
def find_ayah(surah_name, ayah_number):
    for surah in quran_data:
        if surah["name"].strip() == surah_name.strip():
            for ayah in surah["verses"]:
                if ayah["id"] == int(ayah_number):
                    return ayah["text"]
    return None

# ===== المعالجة =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # تجاهل أوامر start
    if text.lower() in ["/start", "start", "ابدا"]:
        await update.message.reply_text("👋 مرحبًا! أرسل اسم السورة ورقم الآية مثل:\n\nالبقرة 255")
        return

    # تقسيم النص
    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("❗ اكتب بصيغة صحيحة مثل: البقرة 255")
        return

    surah_name, ayah_num = parts

    # تحقق أن رقم الآية رقم فعلاً
    if not ayah_num.isdigit():
        await update.message.reply_text("❗ رقم الآية يجب أن يكون رقمًا، مثل: البقرة 255")
        return

    ayah_text = find_ayah(surah_name, ayah_num)
    if ayah_text:
        await update.message.reply_text(f"📖 {surah_name} ({ayah_num})\n\n{ayah_text}")
    else:
        await update.message.reply_text("❌ لم يتم العثور على السورة أو الآية. تأكد من الكتابة الصحيحة.")

# ===== إعداد التطبيق =====
application = Application.builder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===== إعداد Webhook =====
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "🤖 Quran Bot is Running!"

# ===== تشغيل البوت =====
if __name__ == "__main__":
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{TOKEN}"
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))