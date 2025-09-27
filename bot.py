import json
import requests
from flask import Flask, request
import os

# تحميل بيانات القرآن
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
print("⏳ تحميل بيانات القرآن من:", QURAN_URL)
quran_data = requests.get(QURAN_URL).json()
print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# إنشاء تطبيق Flask
app = Flask(__name__)

# قراءة التوكن من المتغير البيئي
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = "7179731919:AAHxZw48ElCJSeCVZUpsG-Pe7Z686qTNV6E"
print(f"✅ تم قراءة التوكن بنجاح: {TOKEN[:10]}********")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# تعيين Webhook
WEBHOOK_URL = f"https://ayatquran.onrender.com/{TOKEN}"
set_hook = requests.get(f"{BASE_URL}/setWebhook?url={WEBHOOK_URL}")
print("🌍 تعيين Webhook على:", WEBHOOK_URL)
print("🔗 نتيجة:", set_hook.text)


# إرسال رسالة
def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})


# نقطة الاستقبال (بدون async)
@app.route(f"/{TOKEN}", methods=["POST"])
def receive_update():
    update = request.get_json()

    if not update:
        return "No update", 400

    message = update.get("message")
    if not message:
        return "No message", 200

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if not text:
        send_message(chat_id, "أرسل اسم السورة ورقم الآية مثل: البقرة 255")
        return "ok", 200

    # تحليل المدخل
    parts = text.split()
    if len(parts) != 2:
        send_message(chat_id, "اكتب بصيغة صحيحة مثل: البقرة 255")
        return "ok", 200

    surah_name, ayah_number = parts[0], parts[1]

    try:
        ayah_number = int(ayah_number)
    except ValueError:
        send_message(chat_id, "رقم الآية يجب أن يكون عددًا صحيحًا.")
        return "ok", 200

    # البحث عن السورة
    surah = next((s for s in quran_data if s["name"] == surah_name or s["englishName"].lower() == surah_name.lower()), None)
    if not surah:
        send_message(chat_id, f"لم أجد سورة باسم {surah_name}")
        return "ok", 200

    # البحث عن الآية
    if ayah_number < 1 or ayah_number > len(surah["verses"]):
        send_message(chat_id, f"السورة {surah_name} تحتوي على {len(surah['verses'])} آيات فقط.")
        return "ok", 200

    ayah = surah["verses"][ayah_number - 1]
    text_ar = ayah["text"]
    send_message(chat_id, f"{surah_name} - آية {ayah_number}:\n{text_ar}")

    return "ok", 200


@app.route("/")
def home():
    return "بوت آيات القرآن يعمل ✅", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))