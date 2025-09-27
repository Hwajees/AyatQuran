import logging
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
from difflib import get_close_matches
import re

# إعداد السجلّات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# تحميل بيانات القرآن
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
response = requests.get(QURAN_URL)
quran_data = response.json()
logger.info(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# التوكن
TOKEN = "7179731919:AAHxZw48ElCJSeCVZUpsG-Pe7Z686qTNV6E"

# رابط الويب هوك
WEBHOOK_URL = f"https://ayatquran.onrender.com/{TOKEN}"

# إعداد Flask
app = Flask(__name__)

# إنشاء تطبيق البوت
application = Application.builder().token(TOKEN).build()

# ===============================
# 🔍 دوال البحث الذكي
# ===============================

def normalize_name(name: str):
    """إزالة التشكيل وكلمة سورة وتحويل الاسم إلى حروف صغيرة"""
    name = name.strip().lower()
    name = re.sub(r'[ًٌٍَُِّْٰ]', '', name)  # إزالة التشكيل
    name = re.sub(r'\b(سورة|سوره)\b', '', name).strip()  # إزالة كلمة سورة
    return name


def find_surah(user_input: str):
    """البحث عن السورة بالاسم العربي فقط مع دعم الأخطاء الإملائية البسيطة"""
    normalized_input = normalize_name(user_input)
    surah_names = [normalize_name(surah["name"]) for surah in quran_data]

    # مطابقة تامة
    for surah in quran_data:
        if normalized_input == normalize_name(surah["name"]):
            return surah

    # مطابقة تقريبية (ذكاء بحثي)
    close_matches = get_close_matches(normalized_input, surah_names, n=1, cutoff=0.75)
    if close_matches:
        best_match = close_matches[0]
        for surah in quran_data:
            if normalize_name(surah["name"]) == best_match:
                return surah

    return None


# ===============================
# 🕌 دوال البوت
# ===============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شرح استخدام البوت"""
    msg = (
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم* 🌙\n\n"
        "📖 أرسل اسم السورة ورقم الآية بهذا الشكل:\n"
        "➡️ *البقرة 255*\n"
        "أو مثلًا:\n"
        "➡️ *الكهف 10*\n\n"
        "وسأرسل لك الآية بإذن الله 💫"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع الرسائل النصية"""
    text = update.message.text.strip()

    # فصل الاسم عن الرقم
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❗ اكتب بصيغة صحيحة مثل: البقرة 255")
        return

    surah_name = " ".join(parts[:-1])
    verse_number_str = parts[-1]

    if not verse_number_str.isdigit():
        await update.message.reply_text("❗ رقم الآية غير صحيح.")
        return

    verse_number = int(verse_number_str)
    surah = find_surah(surah_name)

    if not surah:
        await update.message.reply_text("❌ لم أتعرف على اسم السورة. حاول مرة أخرى.")
        return

    if verse_number < 1 or verse_number > surah["total_verses"]:
        await update.message.reply_text(f"⚠️ سورة {surah['name']} تحتوي على {surah['total_verses']} آية فقط.")
        return

    verse_text = surah["verses"][verse_number - 1]["text"]
    await update.message.reply_text(f"📖 {surah['name']} - آية {verse_number}:\n\n{verse_text}")


# ===============================
# 🌐 Flask Webhook
# ===============================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """نقطة استقبال التحديثات من Telegram"""
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, application.bot)
    try:
        asyncio.run(application.initialize())  # ✅ الحل للمشكلة السابقة
        asyncio.run(application.process_update(update))
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة التحديث: {e}")
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "🌙 بوت القرآن الكريم يعمل بنجاح بإذن الله."


# ===============================
# 🚀 تشغيل البوت
# ===============================
if __name__ == "__main__":
    # إعداد Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # تعيين Webhook
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

    # تشغيل Flask
    app.run(host="0.0.0.0", port=10000)
