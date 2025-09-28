# bot.py
import os
import requests
import asyncio
import threading
import logging
import re
from difflib import get_close_matches
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ayatquran-bot")

# ---------- إعدادات ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ضع توكن البوت في متغير البيئة
BASE_URL = os.getenv("BASE_URL")    # مثال: "https://ayatquran.onrender.com"
if not BOT_TOKEN or not BASE_URL:
    logger.error("❌ الرجاء تعيين متغيرات البيئة BOT_TOKEN و BASE_URL في Render.")
    raise SystemExit("Missing BOT_TOKEN or BASE_URL env var")

WEBHOOK_URL = f"{BASE_URL.rstrip('/')}/{BOT_TOKEN}"

# تحميل بيانات القرآن
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
logger.info("⏳ تحميل بيانات القرآن من: %s", QURAN_URL)
try:
    r = requests.get(QURAN_URL, timeout=15)
    r.raise_for_status()
    quran_data = r.json()
    logger.info("✅ تم تحميل القرآن بنجاح! عدد السور: %s", len(quran_data))
except Exception as e:
    logger.exception("❌ خطأ عند تحميل ملف القرآن: %s", e)
    quran_data = []

# ---------- Flask و Telegram Application ----------
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ---------- دوال مساعدة لتحسين البحث بالعربية ----------
def remove_tashkeel(text: str) -> str:
    return re.sub(r'[\u0617-\u061A\u064B-\u0652]', '', text)

def normalize_name(name: str) -> str:
    name = name or ""
    name = name.strip().lower()
    name = remove_tashkeel(name)
    name = re.sub(r'\b(سورة|سوره)\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def find_surah(user_input: str):
    normalized_input = normalize_name(user_input)
    surah_names = [normalize_name(s["name"]) for s in quran_data]

    # مطابقة تامة
    for s in quran_data:
        if normalized_input == normalize_name(s["name"]):
            return s

    # مطابقة تقريبية (أخطاء إملائية بسيطة)
    close = get_close_matches(normalized_input, surah_names, n=1, cutoff=0.75)
    if close:
        best = close[0]
        for s in quran_data:
            if normalize_name(s["name"]) == best:
                return s
    return None

# ---------- handlers ----------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت آيات القرآن!\n\n"
        "أرسل اسم السورة متبوعاً برقم الآية (بالعربية فقط)، مثال:\n"
        "البقرة 255\n"
        "الكهف 10\n"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return

    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❗ اكتب بصيغة صحيحة مثل: البقرة 255")
        return

    surah_name = " ".join(parts[:-1])
    verse_str = parts[-1]
    if not verse_str.isdigit():
        await update.message.reply_text("❗ رقم الآية غير صحيح.")
        return

    verse_num = int(verse_str)
    surah = find_surah(surah_name)
    if not surah:
        await update.message.reply_text("❌ لم أتعرف على اسم السورة. تأكد من كتابته بالعربية.")
        return

    if verse_num < 1 or verse_num > surah.get("total_verses", 0):
        await update.message.reply_text(f"⚠️ سورة {surah['name']} تحتوي على {surah.get('total_verses',0)} آيات فقط.")
        return

    verse_text = surah["verses"][verse_num - 1]["text"]
    await update.message.reply_text(f"📖 {surah['name']} - آية {verse_num}:\n\n{verse_text}")

# تسجيل الhandlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ---------- نبدأ حلقة asyncio في خيط مستقل ----------
telegram_loop = None

async def _init_telegram_app_async():
    """تهيئة الApplication (initialize + start) على حلقة asyncio موجودة."""
    await application.initialize()
    await application.start()
    # تعيين webhook عبر API telegram
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🌍 تم تعيين Webhook على: %s", WEBHOOK_URL)

def start_telegram_loop_in_thread():
    global telegram_loop
    telegram_loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(telegram_loop)
        telegram_loop.run_forever()

    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()

    # جدولة تهيئة التطبيق على حلقة الخلفية
    fut = asyncio.run_coroutine_threadsafe(_init_telegram_app_async(), telegram_loop)
    try:
        fut.result(timeout=30)  # انتظر الانتهاء (أو رمي استثناء)
        logger.info("✅ Telegram Application initialized and webhook set.")
    except Exception as e:
        logger.exception("❌ فشل تهيئة تطبيق Telegram: %s", e)
        raise

# شغّل الحلقة عند بدء العامل (كل worker في Gunicorn سيشغّل هذه الدالة عند استيراد الموديول)
start_telegram_loop_in_thread()

# ---------- webhook route (سريع، لا يعالج التحديث هنا مباشرة) ----------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"ok": False, "reason": "no json"}), 400
    update = Update.de_json(data, application.bot)

    # وضع التحديث في طابور المعالجة داخل حلقة Telegram
    # نستخدم run_coroutine_threadsafe لوضع عنصر في الqueue
    coro = application.update_queue.put(update)
    asyncio.run_coroutine_threadsafe(coro, telegram_loop)
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "✅ AyatQuran bot — running"

# لا تستعمل app.run() لأن Gunicorn سيشغّل WSGI app مباشرة
