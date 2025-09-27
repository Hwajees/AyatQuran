import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading
import asyncio

# ==============================
# 🔹 إعداد توكن البوت
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ==============================
# 🔹 تحميل بيانات القرآن (JSON مباشر)
# ==============================
QURAN_URL = "https://raw.githubusercontent.com/risan/quran-json/main/quran.json"
response = requests.get(QURAN_URL)
quran_data = response.json()

# تحويل البيانات إلى قاموس يسهل البحث فيه
sura_dict = {sura["name"]: sura for sura in quran_data}

# ==============================
# 🔹 دوال البوت
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 أهلاً بك في بوت القرآن الكريم!\n\n"
        "أرسل اسم السورة بالعربية مثل:\n"
        "الأنعام\nالبقرة\nالكهف\n\n"
        "وسأرسل لك نص السورة كاملًا إن شاء الله 🌙"
    )

async def get_sura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    sura = sura_dict.get(user_input)
    if sura:
        verses = [verse["text"] for verse in sura["verses"]]
        full_text = "\n".join(verses)

        # تجنب تجاوز حدود تيليجرام (4096 حرف)
        for i in range(0, len(full_text), 4000):
            await update.message.reply_text(full_text[i:i+4000])
    else:
        await update.message.reply_text("❌ لم أجد السورة. تأكد من كتابة الاسم الصحيح بالعربية.")

# ==============================
# 🔹 Flask server لتشغيل البوت على Render Web Service
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
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_sura))
    print("✅ البوت يعمل الآن على Render...")
    await app_bot.run_polling()

if __name__ == "__main__":
    # تشغيل خادم Flask في خيط منفصل
    threading.Thread(target=run_flask).start()

    # تشغيل البوت
    asyncio.run(main())