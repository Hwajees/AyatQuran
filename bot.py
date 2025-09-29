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
# Render يوفّر PORT تلقائياً؛ لكن إن أردت يمكنك ضبطه يدوياً في الإعدادات
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_PATH = f"/{BOT_TOKEN}"  # المسار الذي سيستخدمه تيليجرام
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
# تحويل الأرقام العربية إلى إنجليزية
AR_TO_EN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def find_ayah(surah_name, ayah_id):
    # normalize
    ayah_id = str(ayah_id).translate(AR_TO_EN)
    surah_name = surah_name.strip().replace("ال", "").replace("أ", "ا").replace("ة", "ه")
    for surah in quran_data:
        name_clean = surah["name"].replace("ال", "").replace("أ", "ا").replace("ة", "ه")
        if surah_name in name_clean or name_clean in surah_name:
            for verse in surah.get("verses", []):
                if str(verse.get("id")) == str(ayah_id):
                    return f"﴿{verse.get('text')}﴾\n\n📖 سورة {surah['name']} - آية {verse['id']}"
    return None

# ------ إعداد البوت handlers ------
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
        # المطلوب الآن: إذا الرسالة غير مطابقة لا نرد إطلاقًا
        return
    surah_name, ayah_id = match.groups()
    # نترجم الأرقام العربية داخل find_ayah
    result = find_ayah(surah_name, ayah_id)
    if result:
        await update.message.reply_text(result)
    else:
        # حسب طلبك: إذا الآية غير موجودة لا نرد ــ إذًا لا نفعل شيئًا هنا
        return

# ------ بناء الـ Application (لم يتم تهيئته بعد) ------
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ------ سنشغّل حلقة asyncio في Thread منفصل ونهيئ الـ Application هناك ------
async_loop = None

def run_async_loop():
    global async_loop
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)

    async def init_app():
        logger.info("🔁 تهيئة تطبيق telegram (initialize)...")
        await application.initialize()  # ضروري قبل استخدام process_update
        # محاولة ضبط webhook لدى تيليجرام (ستتجاهل الرسائل إن كان مثبتًا سابقًا)
        try:
            # تأكد من استخدام عنوان صحيح في WEBHOOK_URL (Render يعطي hostname في RENDER_EXTERNAL_HOSTNAME)
            hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
            if hostname:
                webhook_url = f"https://{hostname}{WEBHOOK_PATH}"
            else:
                # افتراضي (إن لم يتوفر اسم مضيف خارجي اضبطه يدويا في المتغير البيئي أو في السطر أدناه)
                webhook_url = f"https://ayatquran.onrender.com{WEBHOOK_PATH}"
            await application.bot.set_webhook(webhook_url)
            logger.info(f"✅ تم ضبط webhook -> {webhook_url}")
        except Exception as ex:
            logger.warning(f"⚠️ لم أتمكن من ضبط webhook تلقائيًا: {ex}")
        # نترك الحلقة تعمل
    async_loop.run_until_complete(init_app())
    async_loop.run_forever()

# نبدأ Thread قبل تشغيل Flask (ولكن سنشغّل Flask أسفل)
threading.Thread(target=run_async_loop, daemon=True).start()

# ------ مسار الـ webhook الذي سيستخدمه تيليجرام ------
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return "No data", 400
        # نحول إلى Update ثم نرسله لمعالجة التطبيق على حلقة الـ asyncio التي شغلناها
        update = Update.de_json(data, application.bot)
        # تنفيذ المعالجة في حلقة الـ asyncio في الـ Thread
        if async_loop is None:
            logger.error("❌ الحلقة غير جاهزة بعد")
            return "Service not ready", 503
        future = asyncio.run_coroutine_threadsafe(application.process_update(update), async_loop)
        # لا ننتظر النتيجة — نعيد 200 فوراً
        return "OK", 200
    except Exception as e:
        logger.exception(f"❌ خطأ في استلام webhook: {e}")
        return "Error", 500

# ------ بدء Flask (وهذا الخادم يجب أن يستمع على PORT الذي توفره Render) ------
if __name__ == "__main__":
    logger.info("🚀 بدأ تشغيل Flask - الخادم سيستمع للطلبات")
    # يجب أن يستمع Flask على نفس PORT المُعطى من Render حتى يراه UptimeRobot و Telegram
    app.run(host="0.0.0.0", port=PORT)
