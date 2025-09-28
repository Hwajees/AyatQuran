import os
import json
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجل (Logs)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ayatquran-bot")

# تحميل متغير البيئة الخاص بالتوكن
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ لم يتم تعيين متغير البيئة BOT_TOKEN")

# إنشاء التطبيق والبوت
application = Application.builder().token(BOT_TOKEN).build()

# إنشاء تطبيق Flask
app = Flask(__name__)

# تحميل بيانات السور من ملف JSON
def load_surah_data():
    try:
        with open("surah_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("✅ تم تحميل ملف surah_data.json بنجاح.")
        return data
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل ملف surah_data.json: {e}")
        return []

surah_data = load_surah_data()

# دالة للعثور على السورة حسب الاسم أو الرقم
def find_surah(query):
    for surah in surah_data:
        if str(surah["id"]) == str(query) or surah["name"].strip() == query.strip():
            return surah
    return None

# دالة بدء التشغيل
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌸 مرحبًا بك في بوت آيات القرآن الكريم!\n"
        "أرسل اسم السورة أو رقمها لعرض آياتها.\n"
        "مثال:\n- الفاتحة\n- البقرة 255"
    )

# دالة عرض الآية أو السورة
async def send_ayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    # فصل بين السورة والآية (مثلاً: الكهف 10)
    parts = user_input.split()
    surah_name = parts[0]
    ayah_number = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    surah = find_surah(surah_name)

    if not surah:
        await update.message.reply_text("❌ لم أجد السورة المطلوبة. تأكد من كتابة الاسم أو الرقم بشكل صحيح.")
        return

    # إذا لم يحدد المستخدم رقم آية → نعرض أول 5 آيات فقط
    if not ayah_number:
        verses_preview = surah["verses"][:5]
        message = f"📖 سورة {surah['name']} ({surah['id']})\n\n"
        for verse in verses_preview:
            message += f"{verse['id']}. {verse['text']}\n"
        message += "\n(أرسل رقم آية لعرضها مثل: البقرة 255)"
        await update.message.reply_text(message)
        return

    # إذا طلب المستخدم آية محددة
    for verse in surah["verses"]:
        if verse["id"] == ayah_number:
            await update.message.reply_text(
                f"📖 سورة {surah['name']} ({surah['id']})\n"
                f"آية {verse['id']}:\n\n{verse['text']}"
            )
            return

    await update.message.reply_text("⚠️ لم أجد هذه الآية في السورة.")

# ربط الأوامر
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_ayah))

# مسار Render الرئيسي
@app.route("/")
def home():
    return "✅ Quran bot is running!"

# مسار Webhook لمعالجة تحديثات Telegram
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    async def process():
        try:
            await application.initialize()
        except RuntimeError:
            # إذا تم تهيئة التطبيق مسبقًا
            pass
        await application.process_update(update)

    asyncio.run(process())
    return "ok", 200

# التشغيل الرئيسي
if __name__ == "__main__":
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    logger.info(f"🌍 تم تعيين Webhook على: {WEBHOOK_URL}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
