import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ==============================
# 🔹 إعدادات البوت
# ==============================
BOT_TOKEN = "ضع_توكن_البوت_هنا"

# ✅ رابط مباشر لملف القرآن الكامل بالعربية (بدون الحاجة لرفع ملف)
url = "https://raw.githubusercontent.com/semarketir/quranjson/master/source/surah.json"
response = requests.get(url)
quran_data = response.json()


# ==============================
# 🔹 دالة جلب الآية
# ==============================
def get_verse(sura_name, aya_number):
    # تنظيف الاسم (إزالة كلمة سورة والمسافات)
    sura_name = sura_name.strip().replace("سورة", "").strip()

    for sura in quran_data:
        name = sura["name"].replace("سورة", "").strip()
        if name == sura_name:
            verses = sura["verses"]
            if 1 <= aya_number <= len(verses):
                return verses[aya_number - 1]["text"]
            else:
                return f"❌ رقم الآية غير صحيح. هذه السورة تحتوي على {len(verses)} آيات."
    
    return "❌ لم أجد السورة. تأكد من كتابة الاسم الصحيح بالعربية."


# ==============================
# 🔹 عند استقبال رسالة من المستخدم
# ==============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # تقسيم الرسالة إلى جزأين (اسم السورة + رقم الآية)
    parts = text.split()
    if len(parts) != 2:
        await update.message.reply_text("❗ أرسل اسم السورة ورقم الآية فقط مثل:\n\nالبقرة 255\nالكهف 10")
        return

    sura_name = parts[0]
    try:
        aya_number = int(parts[1])
    except ValueError:
        await update.message.reply_text("❗ رقم الآية يجب أن يكون رقمًا صحيحًا.")
        return

    # جلب الآية
    result = get_verse(sura_name, aya_number)
    await update.message.reply_text(result)


# ==============================
# 🔹 تشغيل البوت
# ==============================
async def main():
    print("✅ البوت يعمل الآن على Render...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()


# تشغيل التطبيق
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())