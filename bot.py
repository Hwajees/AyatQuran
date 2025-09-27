import os
import json
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===============================
# تحميل القرآن مرة واحدة عند التشغيل
# ===============================
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
print("⏳ تحميل بيانات القرآن من:", QURAN_URL)
response = requests.get(QURAN_URL)
QURAN = response.json()
print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(QURAN)}")

# ===============================
# إعداد التوكن وتطبيق Flask
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على التوكن! تأكد من إضافته في إعدادات Render كمتغير بيئة BOT_TOKEN.")

print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:10]}********")

app = Flask(__name__)

# ===============================
# دوال البوت
# ===============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحبًا بك في بوت آيات القرآن الكريم.\nاكتب مثل: البقرة 255 أو الكهف 10")

async def send_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ اكتب بصيغة صحيحة مثل: البقرة 255")
            return

        surah_name, ayah_num = parts
        ayah_num = int(ayah_num)

        # البحث عن السورة المطلوبة
        surah = next((s for s in QURAN if s["name"] == surah_name or s["transliteration"] == surah_name.capitalize()), None)

        if not surah:
            await update.message.reply_text("❌ لم أجد هذه السورة.")
            return

        # البحث عن الآية المطلوبة
        ayahs = surah["verses"]
        if 1 <= ayah_num <= len(ayahs):
            ayah_text = ayahs[ayah_num - 1]["text"]
            await update.message.reply_text(f"📖 {surah_name} [{ayah_num}]\n\n{ayah_text}")
        else:
            await update.message.reply_text("❌ رقم الآية غير صحيح.")
    except Exception as e:
        print("❌ خطأ أثناء المعالجة:", e)
        await update.message.reply_text("حدث خطأ أثناء جلب الآية. حاول مرة أخرى.")

# ===============================
# إعداد التطبيق
# ===============================
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_ayah))

# ===============================
# إعداد Webhook
# ===============================
WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
print("🌍 تعيين Webhook على:", WEBHOOK_URL)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """نقطة استقبال التحديثات من تليجرام"""
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "✅ بوت آيات القرآن يعمل بنجاح!", 200

if __name__ == "__main__":
    # تعيين Webhook فعليًا
    application.bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
