import os
import json
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==========================
# تحميل بيانات القرآن
# ==========================
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"

print("⏳ تحميل بيانات القرآن من:", QURAN_URL)
response = requests.get(QURAN_URL)
quran_data = response.json()
print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# ==========================
# إعداد التوكن
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على التوكن! تأكد من ضبط المتغير BOT_TOKEN في إعدادات Render.")

print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:9]}********")

# ==========================
# إعداد البوت
# ==========================
application = Application.builder().token(BOT_TOKEN).build()

# ==========================
# الأوامر الأساسية
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 أهلاً بك في *بوت آيات القرآن الكريم*\n\n"
        "📖 يمكنك إرسال:\n"
        "- اسم السورة مثل: *البقرة*\n"
        "- أو رقم السورة مثل: *2*\n"
        "- أو اكتب: *البقرة 255* لعرض آية محددة.\n\n"
        "🌙 نسأل الله أن ينفعك بالقرآن الكريم ❤️"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ==========================
# البحث عن السورة أو الآية
# ==========================
def get_surah(name_or_number):
    """إيجاد السورة بالاسم أو الرقم"""
    for surah in quran_data:
        if (
            str(surah["id"]) == str(name_or_number)
            or surah["name"].strip() == name_or_number.strip()
            or surah["transliteration"].lower() == name_or_number.lower()
        ):
            return surah
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # التحقق من وجود رقم آية بعد السورة
    parts = text.split()
    if len(parts) == 2 and parts[1].isdigit():
        surah_name = parts[0]
        ayah_number = int(parts[1])
        surah = get_surah(surah_name)
        if not surah:
            await update.message.reply_text("❌ لم يتم العثور على السورة، حاول مرة أخرى.")
            return

        ayahs = surah["verses"]
        if 1 <= ayah_number <= len(ayahs):
            ayah = ayahs[ayah_number - 1]
            await update.message.reply_text(
                f"📖 *{surah['name']}* - آية {ayah_number}\n\n{ayah['text']}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("⚠️ رقم الآية غير صحيح.")
        return

    # إذا أرسل المستخدم اسم السورة فقط
    surah = get_surah(text)
    if surah:
        ayah_count = len(surah["verses"])
        await update.message.reply_text(
            f"📘 *{surah['name']}* ({surah['transliteration']})\n"
            f"عدد الآيات: {ayah_count}\n\n"
            f"للحصول على آية محددة أرسل مثل:\n"
            f"👉 {surah['name']} 1",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ لم يتم العثور على السورة، حاول مرة أخرى.")


# ==========================
# إضافة المعالجات Handlers
# ==========================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==========================
# إعداد Flask و Webhook
# ==========================
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK", 200

@app.route("/")
def home():
    return "✅ Quran Bot is running with Webhook!", 200

# ==========================
# التشغيل الرئيسي
# ==========================
if __name__ == "__main__":
    webhook_url = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    print(f"🌍 تعيين Webhook على: {webhook_url}")

    # تعيين Webhook قبل بدء السيرفر
    asyncio.run(application.bot.set_webhook(webhook_url))

    # تشغيل Flask
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))