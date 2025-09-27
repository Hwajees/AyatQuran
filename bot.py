import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading
import asyncio

# ==============================
# 🔹 إعداد التوكن
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ==============================
# 🔹 قائمة بأسماء السور مع أرقامها (لأن API يستخدم رقم السورة)
# ==============================
sura_numbers = {
    "الفاتحة": 1, "البقرة": 2, "آل عمران": 3, "النساء": 4, "المائدة": 5,
    "الأنعام": 6, "الأعراف": 7, "الأنفال": 8, "التوبة": 9, "يونس": 10,
    "هود": 11, "يوسف": 12, "الرعد": 13, "إبراهيم": 14, "الحجر": 15,
    "النحل": 16, "الإسراء": 17, "الكهف": 18, "مريم": 19, "طه": 20,
    "الأنبياء": 21, "الحج": 22, "المؤمنون": 23, "النور": 24, "الفرقان": 25,
    "الشعراء": 26, "النمل": 27, "القصص": 28, "العنكبوت": 29, "الروم": 30,
    "لقمان": 31, "السجدة": 32, "الأحزاب": 33, "سبأ": 34, "فاطر": 35,
    "يس": 36, "الصافات": 37, "ص": 38, "الزمر": 39, "غافر": 40,
    "فصلت": 41, "الشورى": 42, "الزخرف": 43, "الدخان": 44, "الجاثية": 45,
    "الأحقاف": 46, "محمد": 47, "الفتح": 48, "الحجرات": 49, "ق": 50,
    "الذاريات": 51, "الطور": 52, "النجم": 53, "القمر": 54, "الرحمن": 55,
    "الواقعة": 56, "الحديد": 57, "المجادلة": 58, "الحشر": 59, "الممتحنة": 60,
    "الصف": 61, "الجمعة": 62, "المنافقون": 63, "التغابن": 64, "الطلاق": 65,
    "التحريم": 66, "الملك": 67, "القلم": 68, "الحاقة": 69, "المعارج": 70,
    "نوح": 71, "الجن": 72, "المزمل": 73, "المدثر": 74, "القيامة": 75,
    "الإنسان": 76, "المرسلات": 77, "النبأ": 78, "النازعات": 79, "عبس": 80,
    "التكوير": 81, "الانفطار": 82, "المطففين": 83, "الانشقاق": 84, "البروج": 85,
    "الطارق": 86, "الأعلى": 87, "الغاشية": 88, "الفجر": 89, "البلد": 90,
    "الشمس": 91, "الليل": 92, "الضحى": 93, "الشرح": 94, "التين": 95,
    "العلق": 96, "القدر": 97, "البينة": 98, "الزلزلة": 99, "العاديات": 100,
    "القارعة": 101, "التكاثر": 102, "العصر": 103, "الهمزة": 104, "الفيل": 105,
    "قريش": 106, "الماعون": 107, "الكوثر": 108, "الكافرون": 109, "النصر": 110,
    "المسد": 111, "الإخلاص": 112, "الفلق": 113, "الناس": 114
}

# ==============================
# 🔹 دالة بدء البوت
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 أهلاً بك في بوت القرآن الكريم!\n\n"
        "اكتب اسم السورة ورقم الآية مثل:\n"
        "البقرة 255\n\n"
        "وسأرسل لك الآية المطلوبة بإذن الله 🌙"
    )

# ==============================
# 🔹 دالة جلب الآية
# ==============================
async def get_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    parts = user_input.split()

    if len(parts) != 2:
        await update.message.reply_text("⚠️ أرسل اسم السورة متبوعًا برقم الآية، مثل: الكهف 10")
        return

    sura_name, ayah_number = parts

    if sura_name not in sura_numbers:
        await update.message.reply_text("❌ لم أجد هذه السورة. تأكد من كتابة الاسم بالعربية مثل: البقرة أو الكهف.")
        return

    if not ayah_number.isdigit():
        await update.message.reply_text("⚠️ رقم الآية يجب أن يكون رقمًا، مثل: البقرة 255")
        return

    sura_number = sura_numbers[sura_name]
    ayah_number = int(ayah_number)

    # طلب الآية من API
    url = f"https://api.alquran.cloud/v1/ayah/{sura_number}:{ayah_number}"
    response = requests.get(url)
    data = response.json()

    if data["code"] == 200:
        verse_text = data["data"]["text"]
        await update.message.reply_text(f"📖 {sura_name} ({ayah_number})\n\n{verse_text}")
    else:
        await update.message.reply_text("❌ لم أجد هذه الآية. تأكد من رقمها الصحيح.")

# ==============================
# 🔹 Flask لتشغيل الخدمة على Render Web Service
# ==============================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Quran Bot is running on Render!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# ==============================
# 🔹 تشغيل البوت
# ==============================
async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ayah))
    print("✅ البوت يعمل الآن على Render...")
    await app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    asyncio.run(main())