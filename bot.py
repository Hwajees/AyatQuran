import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ تحميل بيانات القرآن من رابط موثوق ومنسق بصيغة JSON صحيحة
url = "https://cdn.jsdelivr.net/gh/risan/quran-json@main/data/quran.json"
response = requests.get(url)
quran_data = json.loads(response.text)

# 🔹 التأكد أن البيانات قائمة وليست نصًا
if isinstance(quran_data, dict) and "quran" in quran_data:
    quran_data = quran_data["quran"]

# 🔹 إنشاء قاموس باسم السورة بالعربية
sura_dict = {}
for sura in quran_data:
    try:
        name = sura.get("name", "").strip()
        if name:
            sura_dict[name] = sura
    except Exception:
        continue

# 🕌 أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحباً بك في بوت القرآن الكريم!\n\n"
        "أرسل لي اسم السورة ورقم الآية، مثل:\n"
        "البقرة 255\n"
        "الكهف 10\n"
        "النساء 34"
    )

# 📖 دالة معالجة الرسائل
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    try:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ الرجاء إدخال اسم السورة ثم رقم الآية مثل: البقرة 255")
            return

        sura_name = parts[0]
        ayah_number = int(parts[1])

        sura = sura_dict.get(sura_name)
        if not sura:
            await update.message.reply_text("❌ لم أجد السورة. تأكد من كتابة الاسم الصحيح بالعربية.")
            return

        ayahs = sura["ayahs"]
        if ayah_number < 1 or ayah_number > len(ayahs):
            await update.message.reply_text(f"❌ هذه السورة تحتوي على {len(ayahs)} آيات فقط.")
            return

        ayah_text = ayahs[ayah_number - 1]["text"]

        sender = update.message.from_user.first_name
        await update.message.reply_text(
            f"📖 {sura_name} - آية {ayah_number}\n\n"
            f"{ayah_text}\n\n"
            f"🔹 طلب من: {sender}"
        )

    except ValueError:
        await update.message.reply_text("⚠️ رقم الآية يجب أن يكون رقمًا فقط.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء المعالجة: {e}")

# ⚙️ تشغيل البوت
async def main():
    token = os.getenv("TOKEN")
    if not token:
        print("❌ لم يتم العثور على TOKEN في المتغيرات البيئية.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ البوت يعمل الآن على Render...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())