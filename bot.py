# bot.py
import os
import json
import logging
import threading
import asyncio
import re
import concurrent.futures
from typing import Optional

from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ---------- إعدادات لوجر ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("quran-bot")

# ---------- جلب التوكن من المتغيرات البيئية ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TOKEN")
if not BOT_TOKEN:
    logger.error("❌ لم يُعطَ BOT_TOKEN في environment. عيّن المتغير BOT_TOKEN.")
    raise SystemExit("BOT_TOKEN missing")

# ---------- تحميل ملف JSON (يحاول اسمين للاحتمال) ----------
SURAH_FILES = ["surah_data.JSON", "surah_data.json"]
surahs = []
loaded = False
for fname in SURAH_FILES:
    try:
        with open(fname, "r", encoding="utf-8") as f:
            surahs = json.load(f)
        logger.info(f"✅ تم تحميل ملف {fname} بنجاح.")
        loaded = True
        break
    except FileNotFoundError:
        logger.warning(f"ملف {fname} غير موجود، جرّب التالي...")
    except json.JSONDecodeError as e:
        logger.error(f"❌ خطأ في تحميل {fname}: {e}")
        # لا نخرج هنا، نجرب الملف التالي إن وُجد
if not loaded:
    logger.error("❌ فشل تحميل أي ملف surah_data.*. تأكد من وجود الملف وصحّة صيغة JSON.")
    raise SystemExit("surah_data JSON not found or invalid")

# ---------- دوال تطبيع أسماء السور (fuzzy/simple normalization) ----------
ARABIC_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u06D6-\u06ED]")
def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = str(name)
    name = name.strip()
    # إزالة الحركات
    name = ARABIC_DIACRITICS.sub("", name)
    # توحيد الألف
    name = re.sub(r"[إأآ]", "ا", name)
    # ياء/ألف مقصورة
    name = name.replace("ى", "ي")
    # تاء مربوطة و الهاء نعتبرهما متساويتين -> نحول كل شيئ إلى هاء (أو نحذفها)
    # سنحوّل التاء المربوطة (ة) إلى هاء لتقارب الكتابة
    name = name.replace("ة", "ه")
    # تحويل الهمزة المتوسطة إلى همزة بسيطة (أ) -> (ا) تم مسبقاً
    # إزالة اللام التعريف في البداية لعمل تشابه (لا تغير باقي اللفظ)
    name = re.sub(r"^ال", "", name)
    # حذف المسافات والرموز الزائدة لتسهيل المقارنة
    name = re.sub(r"[^ء-ي0-9a-zA-Z]", "", name)
    name = name.lower()
    return name

def convert_arabic_digits_to_english(s: str) -> str:
    # يحول الأرقام الهندية إلى الغربية إن وُجدت
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    western_digits = "0123456789"
    trans = {ord(ar): wd for ar, wd in zip(arabic_digits, western_digits)}
    return s.translate(trans)

def find_surah_by_name(user_input: str) -> Optional[dict]:
    q = normalize_name(user_input)
    if not q:
        return None

    # محاولات بحث متدرّجة: مساواة تامة، احتواء، يبدأ بـ، مسافة حذف
    best = None
    for s in surahs:
        sname = s.get("name", "")
        norm = normalize_name(sname)
        if q == norm:
            return s
        if q in norm or norm in q:
            best = s
    return best

def find_ayah_text(surah: dict, ayah_id: int) -> Optional[str]:
    verses = surah.get("verses") or surah.get("ayahs") or []
    # verses expected to be list of dicts with field "id" and "text"
    for v in verses:
        # permissive keys
        vid = v.get("id") if isinstance(v, dict) else None
        if vid is None:
            # maybe verse is object with "no" or index-based
            continue
        try:
            if int(vid) == ayah_id:
                text = v.get("text") or v.get("ayat") or v.get("verse") or ""
                return text
        except Exception:
            continue
    return None

# ---------- إعداد تطبيق البوت (python-telegram-bot async Application) ----------
application = Application.builder().token(BOT_TOKEN).build()

# /start handler
async def start(update: Update, context):
    # رسالة مختصرة لطريقة الاستخدام — لا نكرر أي آية هنا
    msg = (
        "🌸 أهلاً! لعرض آية أرسل اسم السورة متبوعًا بمسافة ثم رقم الآية.\n"
        "مثال: `البقرة 2` أو `بقره 2` (التاء المربوطة/الهاء لا تهم).\n"
        "ملاحظة: اكتب الاسم قريبًا من الصحيح (يمكن اختصار أو تعديل الهمزات)."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# رسالة عندما لا نجد السورة أو الآية
async def handle_message(update: Update, context):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("❌ رجاءً أرسل اسم السورة متبوعًا بمسافة ورقم الآية.")
        return

    # تحويل أرقام عربية
    text_conv = convert_arabic_digits_to_english(text)
    parts = text_conv.split()
    if len(parts) < 2:
        await update.message.reply_text("✳️ الصيغة خاطئة. اكتب: اسم_السورة مسافة رقم_الآية\nمثال: البقرة 2")
        return

    # آخر جزء مفترض أن يكون رقم الآية
    possible_num = parts[-1]
    if not re.fullmatch(r"\d+", possible_num):
        # قد يكون المستخدم أرسل رقم بداخل النص بطرق غريبة؛ نطلب الصياغة الصحيحة
        await update.message.reply_text("✳️ يجب أن يكون آخر جزء رقماً، مثال: البقرة 2")
        return

    ayah_num = int(possible_num)
    surah_name = " ".join(parts[:-1])

    surah = find_surah_by_name(surah_name)
    if not surah:
        await update.message.reply_text("❌ لم أجد السورة المطلوبة. تأكد من كتابة الاسم بشكل قريب من الصحيح.")
        return

    # حسب مذكّرك: رقم السورة يكون في الحقل "no" (surah number) — لا نستخدمه هنا لكن تتحقق
    # البحث عن الآية ضمن الحقول verses -> تحتوي على كائنات بها "id" و "text"
    ayah_text = find_ayah_text(surah, ayah_num)
    if not ayah_text:
        await update.message.reply_text("❌ لم أجد الآية في هذه السورة. تأكد من رقم الآية.")
        return

    # إرسال الآية
    # نضيف اسم السورة والآية قبل النص
    surah_no = surah.get("no") or surah.get("id") or surah.get("number")
    header = f"📖 {surah.get('name','')} — آية {ayah_num}"
    await update.message.reply_text(f"{header}\n\n{ayah_text}")

# تسجيل الهاندلرز في التطبيق
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ---------- إدارة event loop خلفي آمن (لكي لا نواجه أخطاء Event loop is closed / thread) ----------
_background_loop: Optional[asyncio.AbstractEventLoop] = None
_bg_thread: Optional[threading.Thread] = None
_init_lock = threading.Lock()
_initialized = False

def ensure_background_loop_and_init():
    global _background_loop, _bg_thread, _initialized
    with _init_lock:
        if _initialized and _background_loop and _background_loop.is_running():
            return

        # أنشئ event loop جديد وشغّله في ثريد منفصل
        _background_loop = asyncio.new_event_loop()
        _bg_thread = threading.Thread(target=_background_loop.run_forever, daemon=True)
        _bg_thread.start()
        # initialize application on that loop (this binds httpx clients etc. to that loop)
        fut = asyncio.run_coroutine_threadsafe(application.initialize(), _background_loop)
        try:
            fut.result(timeout=20)
        except Exception as e:
            logger.exception("فشل أثناء تهيئة التطبيق async: %s", e)
            raise

        # حاول تعيين webhook (اسم النطاق من env أو من قيمة افتراضية)
        # يمكنك تعيين RENDER_EXTERNAL_HOSTNAME في متغيرات Render لمطابقة عنوانك الحقيقي
        hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME") or os.environ.get("HOSTNAME") or "ayatquran.onrender.com"
        webhook_url = os.environ.get("WEBHOOK_URL") or f"https://{hostname}/{BOT_TOKEN}"
        fut2 = asyncio.run_coroutine_threadsafe(application.bot.set_webhook(url=webhook_url), _background_loop)
        try:
            fut2.result(timeout=15)
            logger.info("🌍 تم تعيين Webhook على: %s", webhook_url)
        except Exception:
            logger.exception("تعذر تعيين webhook (قد يكون مسبقًا مُعيَّنًا).")

        _initialized = True

# ---------- Flask app و route للـ webhook ----------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Quran bot is running."

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    # أولًا تأكد أن التطبيق مُهيأ في خلفية العملية
    try:
        ensure_background_loop_and_init()
    except Exception as e:
        logger.exception("خطأ أثناء ensure_background_loop_and_init")
        # نرجع 500 ليعلم Render/Telegram بحدوث خطأ؛ لكن الهدف الأساسي هو تسجيله
        return "init error", 500

    update_json = request.get_json(force=True)
    if not update_json:
        return "no data", 400

    # بناء Update من الـ JSON
    try:
        update = Update.de_json(update_json, application.bot)
    except Exception as e:
        logger.exception("تعذر تحويل JSON إلى Update: %s", e)
        return "bad update", 400

    # جدولة معالجة التحديث على الـ background loop
    future = asyncio.run_coroutine_threadsafe(application.process_update(update), _background_loop)
    try:
        # ننتظر قليلاً لنتأكد من المعالجة — لكن حتى لو انتهت بالTimeout، نعيد 200 كي لا يعيد تيليجرام نفس الحدث
        future.result(timeout=8)
    except concurrent.futures.TimeoutError:
        logger.warning("معالجة التحديث استغرقت وقتاً طويلاً — أعدت 200 حتى لا يُعاد الإرسال من تيليجرام.")
    except Exception:
        logger.exception("خطأ أثناء process_update:")
    return "OK", 200

# ---------- تشغيل محلي (اختياري) ----------
if __name__ == "__main__":
    # عند التشغيل محليًا: نهيئ الخلفية ثم نشغّل Flask (للاختبار)
    ensure_background_loop_and_init()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
