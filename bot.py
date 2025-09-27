import os
import json
import requests
from flask import Flask, request, jsonify

# =============================
# تحميل بيانات القرآن
# =============================
QURAN_URL = "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json"
print(f"⏳ تحميل بيانات القرآن من: {QURAN_URL}")
response = requests.get(QURAN_URL)
quran_data = response.json()
print(f"✅ تم تحميل القرآن بنجاح! عدد السور: {len(quran_data)}")

# =============================
# إعداد التوكن
# =============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ لم يتم العثور على BOT_TOKEN في المتغيرات البيئية!")
else:
    print(f"✅ تم قراءة التوكن بنجاح: {BOT_TOKEN[:10]}********")

# =============================
# تهيئة Flask
# =============================
app = Flask(__name__)

# =============================
# دوال المساعدة
# =============================
def send_message(chat_id, text):
    """إرسال رسالة للمستخدم"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ خطأ أثناء إرسال الرسالة: {e}")

def find_verse(surah_name_or_number, ayah_number):
    """البحث عن آية من السورة"""
    try:
        ayah_number = int(ayah_number)
    except:
        return None

    for surah in quran_data:
        if str(surah["number"]) == str(surah_name_or_number) or surah["name"].strip() == str(surah_name_or_number).strip():
            for verse in surah["verses"]:
                if verse["id"] == ayah_number:
                    return verse["text"]
    return None

# =============================
# الراوت الرئيسي للتحقق
# =============================
@app.route('/')
def home():
    return "✅ البوت يعمل بنجاح على Render!"

# =============================
# استقبال تحديثات Telegram
# =============================
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"error": "No update received"}), 400

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"].strip()

        print(f"📩 رسالة جديدة من المستخدم: {text}")

        if text.lower() == "/start":
            send_message(chat_id, "👋 مرحبًا بك في بوت آيات القرآن الكريم!\n\nاكتب مثلًا: البقرة 255 أو الكهف 10")
        else:
            try:
                parts = text.split()
                if len(parts) != 2:
                    send_message(chat_id, "❌ اكتب بصيغة صحيحة مثل: البقرة 255")
                    return jsonify({"status": "ok"}), 200

                surah, ayah = parts
                verse = find_verse(surah, ayah)
                if verse:
                    send_message(chat_id, f"📖 {verse}")
                else:
                    send_message(chat_id, "❌ لم أجد الآية المطلوبة، تأكد من الكتابة مثل: البقرة 255")
            except Exception as e:
                print(f"⚠️ خطأ أثناء المعالجة: {e}")
                send_message(chat_id, "❌ اكتب بصيغة صحيحة مثل: البقرة 255")

    return jsonify({"status": "ok"}), 200

# =============================
# تشغيل البوت
# =============================
if __name__ == '__main__':
    WEBHOOK_URL = f"https://ayatquran.onrender.com/{BOT_TOKEN}"
    set_webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    res = requests.get(set_webhook_url)
    print(f"🌍 تعيين Webhook على: {WEBHOOK_URL}")
    print(f"📬 نتيجة إعداد Webhook: {res.text}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))