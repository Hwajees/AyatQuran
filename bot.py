import os
import requests
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ==========================
# إعداد Flask (حتى يبقى البوت نشطًا على Render)
# ==========================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Quran Bot is running on Render!"

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

# إنشاء قاموس للوصول السريع للسور
quran_dict = {sura["name"]: sura for sura in quran_data}

# ==========================
# إعداد التوكن
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("🚨 خطأ: لم يتم العثور على توكن صالح!")
    print("❗ تأكد أنك أضفت المتغير BOT_TOKEN في إعدادات Render.")
    exit()

print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:8]}********")

# ==========================
# دوال البوت
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحبًا بك!\nأرسل اسم السورة ورقم الآية مثل:\n\nالبقرة 255")

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

# ==========================
# تشغيل البوت
# ==========================
async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 البوت يعمل الآن على Render...")
    await app_bot.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))