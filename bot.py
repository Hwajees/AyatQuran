import os
import json
import logging
import asyncio
import re
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ==============================
# إعداد السجلّات (Logs)
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ayatquran-bot")

# ==============================
# إعداد البوت و Flask
# ==============================
TOKEN = os.environ.get("BOT_TOKEN") or "ضع_التوكن_الخاص_بك_هنا"
application = Application.builder().token(TOKEN).build()
app = Flask(__name__)

# ==============================
# تحميل ملف JSON للسور
# ==============================
with open("surah_data.json", "r", encoding="utf-8") as f:
    SURAH_DATA = json.load(f)

# ==============================
# دالة مساعدة: تنظيف اسم السورة
# ==============================
def normalize_surah_name(name: str) -> str:
    """تحويل الاسم إلى صيغة قياسية للمقارنة الذكية"""
    name = name.strip().lower()
    name = re.sub(r"[ًٌٍَُِّْـٰ]", "", name)  # حذف التشكيل
    name = name.replace("سوره", "").replace("سورة", "").strip()  # حذف كلمة "سورة"
    return name

# ==============================
# دالة مساعدة: البحث عن السورة
# ==============================
def find_surah_by_name(name: str):
    name = normalize_surah_name(name)
    for surah in SURAH_DATA:
        surah_name = normalize_surah_name(surah["name"])
        if surah_name == name:
            return surah
    return None

# ==============================
# أوامر البوت
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شرح البرنامج فقط عند البدء"""
    msg = (
        "👋 مرحبًا بك في *بوت آيات القرآن الكريم* 🌿\n\n"
        "📖 يمكنك كتابة اسم السورة ورقم الآية مثل:\n"
        "› البقرة 255\n"
        "› الكهف 10\n\n"
        "💡 سيقوم البوت بجلب الآية وقراءتها صوتيًا بإذن الله."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع إدخال المستخدم"""
    text = update.message.text.strip()

    # محاولة استخراج الاسم والرقم
    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("❌ الرجاء كتابة: اسم السورة متبوعًا برقم الآية مثل:\nالبقرة 255")
        return

    surah_name, ayah_number = parts[0], parts[1]

    if not ayah_number.isdigit():
        await update.message.reply_text("❌ رقم الآية يجب أن يكون رقمًا صحيحًا.")
        return

    surah = find_surah_by_name(surah_name)
    if not surah:
        await update.message.reply_text("❌ لم أتمكن من العثور على السورة، تأكد من الاسم.")
        return

    surah_number = surah["number"]
    api_url = f"https://api.alquran.cloud/v1/ayah/{surah_number}:{ayah_number}/ar.alafasy"

    import requests
    response = requests.get(api_url)

    if response.status_code != 200:
        await update.message.reply_text("⚠️ حدث خطأ أثناء جلب البيانات من الخادم.")
        return

    data = response.json()
    if data["status"] != "OK":
        await update.message.reply_text("❌ لم يتم العثور على الآية المطلوبة.")
        return

    ayah = data["data"]["text"]
    audio = data["data"]["audio"]

    await update.message.reply_text(f"📖 {ayah}")
    await update.message.reply_audio(audio, caption=f"🎧 تلاوة من سورة {surah['name']} - الآية {ayah_number}")

# ==============================
# ربط الأوامر
# ==============================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==============================
# Webhook (Flask)
# ==============================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_handler():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))  # ✅ الإصلاح هنا
    except Exception as e:
        logger.exception(f"❌ خطأ أثناء المعالجة: {e}")
        return "error", 500
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "Ayat Quran Bot is running 🕌", 200

# ==============================
# تشغيل التطبيق محليًا (اختياري)
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
