# bot.py
import os
import json
import logging
import re
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ------ إعداد السجلات ------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quran-bot")

# ------ إعداد Flask ------
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Quran Bot is running and healthy!"

# ------ متغيرات البيئة ------
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', os.getenv('HEROKU_APP_NAME', 'ayatquran.onrender.com'))}{WEBHOOK_PATH}"

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود في متغيرات البيئة. أضفه في إعدادات Render.")

# ------ تحميل بيانات السور ------
try:
    with open("surah_data.JSON", "r", encoding="utf-8") as f:
        quran_data = json.load(f)
    logger.info("✅ تم تحميل surah_data.JSON")
except Exception as e:
    logger.error(f"❌ خطأ عند تحميل surah_data.JSON: {e}")
    quran_data = []

# ------ دوال المساعدة ------
AR_TO_EN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def find_ayah(surah_name, ayah_id):
    # تحويل الأرقام العربية إلى إنجليزية
    ayah_id = str(ayah_id).translate(AR_TO_EN)

    # دالة لتطبيع الاسم
    def normalize_name(name):
        name = name.strip()
        # توحيد أشكال الهمزات
        name = name.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        # حذف "ال" في بداية الكلمة فقط (لأن البعض يكتبها بدونها)
        name = re.sub(r"^ال", "", name)
        # تحويل التاء المربوطة إلى هاء
        name = name.replace("ة", "ه")
        # إزالة التشكيل إن وجد
        name = re.sub(r"[\u064B-\u0652]", "", name)
        return name

    normalized_input = normalize_name(surah_name)

    # البحث عن سورة مطابقة بالضبط بعد التطبيع
    for surah in quran_data:
        normalized_surah = normalize_name(surah["name"])
        if normalized_input == normalized_surah:  # تطابق تام فقط
            for verse in surah.get("verses", []):
                if str(verse.get("id")) == str(ayah_id):
                    return f"﴿{verse.get('text')}﴾\n\n📖 سورة {surah['name']} - آية {verse['id']}"
            return None  # السورة صحيحة لكن الآية غير موجودة

    return None  # لم يتم العثور على سورة مطابقة

# ------ إعداد Handlers للبوت ------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في بوت آيات القرآن الكريم!\n\n"
        "أرسل اسم السورة متبوعًا برقم الآية مثل:\n"
        "📖 البقرة 255\n📖 الكهف 10"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    # قبول الأرقام العربية أو الإنجليزية
    match = re.match(r"([\u0621-\u064A\s]+)\s+([\d\u0660-\u0669]+)", text)
    if not match:
        # إذا لم تتطابق الرسالة مع النمط لا نرد إطلاقًا
        return
    surah_name, ayah_id = match.groups()
    result = find_ayah(surah_name, ayah_id)
    if result:
        await update.message.reply_text(result)
    # إذا لم يجد الآية أو السورة → لا يرد إطلاقًا

# ------ إنشاء التطبيق ------
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ------ تشغيل حلقة asyncio في Thread منفصل ------
async_loop = None

def run_async_loop():
    global async_loop
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)

    async def init_app():
        logger.info("🔁 تهيئة تطبيق telegram (initialize)...")
        await application.initialize()
        try:
            hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
            if hostname:
                webhook_url = f"https://{hostname}{WEBHOOK_PATH}"
            else:
                webhook_url = f"https://ayatquran.onrender.com{WEBHOOK_PATH}"
            await application.bot.set_webhook(webhook_url)
            logger.info(f"✅ تم ضبط webhook -> {webhook_url}")
        except Exception as ex:
            logger.warning(f"⚠️ لم أتمكن من ضبط webhook تلقائيًا: {ex}")
    async_loop.run_until_complete(init_app())
    async_loop.run_forever()

threading.Thread(target=run_async_loop, daemon=True).start()

# ------ مسار webhook ------
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return "No data", 400
        update = Update.de_json(data, application.bot)
        if async_loop is None:
            logger.error("❌ الحلقة غير جاهزة بعد")
            return "Service not ready", 503
        asyncio.run_coroutine_threadsafe(application.process_update(update), async_loop)
        return "OK", 200
    except Exception as e:
        logger.exception(f"❌ خطأ في استلام webhook: {e}")
        return "Error", 500

# ------ بدء Flask ------
if __name__ == "__main__":
    logger.info("🚀 بدأ تشغيل Flask - الخادم سيستمع للطلبات")
    app.run(host="0.0.0.0", port=PORT)
