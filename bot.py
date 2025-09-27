import os
import requests
from flask import Flask
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ قراءة التوكن من متغير البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ✅ فحص التوكن قبل التشغيل
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("🚨 خطأ: لم يتم العثور على توكن صالح!")
    print("❗ تأكد أنك أضفت المتغير BOT_TOKEN بشكل صحيح في إعدادات Render (Environment Variables).")
    print("❗ مثال صحيح للتوكن: 123456789:ABCDefGhIJKlmNoPQRstuVWxyZ")
    raise SystemExit("❌ إيقاف التشغيل: لا يوجد توكن بوت صالح.")

print("✅ تم قراءة التوكن بنجاح:", BOT_TOKEN[:10] + "********")  # لا يطبع التوكن الكامل لأمانك

# ✅ رابط ملف JSON للقرآن الكريم بالعربية
QURAN_URL = "https://raw.githubusercontent.com/semarketir/quranjson/master/source/quran.json"

# ✅ تحميل بيانات القرآن
response = requests.get(QURAN_URL)
if response.status_code != 200:
    raise SystemExit("❌ فشل تحميل ملف القرآن من الرابط.")
quran_data = response.json()

# 🕌 دالة البحث عن آية
def find_ayah(sura_name, ayah_number):
    for sura in quran_data["chapters"]:
        if sura["name_arabic"] == sura_name:
            verses = sura["verses"]
            for verse in verses:
                if verse["id"] == ayah_number:
                    return verse["text_arabic"]
            return None
    return None

# 🕋 أمر البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌿 مرحبًا بك في *بوت القرآن الكريم*.\n"
        "أرسل اسم السورة ورقم الآية مثل:\n\n"
        "البقرة 255\n"
        "الكهف 10\n\n"
        "وسأرسل لك نص الآية بإذن الله 🤍",
        parse_mode="Markdown"
    )

# ✉️ معالجة الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text("❌ يرجى إرسال اسم السورة ثم رقم الآية مثل:\nمثال: البقرة 255")
        return

    sura_name, ayah_num_str = parts
    if not ayah_num_str.isdigit():
        await update.message.reply_text("❌ رقم الآية يجب أن يكون رقمًا صحيحًا.")
        return

    ayah_number = int(ayah_num_str)
    ayah_text = find_ayah(sura_name, ayah_number)

    if ayah_text:
        await update.message.reply_text(f"📖 {sura_name} - الآية {ayah_number}\n\n{ayah_text}")
    else:
        await update.message.reply_text("❌ لم أجد السورة أو رقم الآية. تأكد من الكتابة الصحيحة بالعربية.")

# 🚀 Flask server (لضمان بقاء البوت نشطًا على Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ بوت القرآن الكريم يعمل الآن بإذن الله."

# 🚀 تشغيل البوت
async def main():
    print("✅ البوت يعمل الآن على Render...")
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())