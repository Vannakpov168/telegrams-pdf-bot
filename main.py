import telebot
from PIL import Image
import io
from datetime import date
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- ១. បង្កើត Web Server តូចមួយដើម្បីឱ្យ Render ស្គាល់ ( Free Tier + គាំទ្រ HEAD/GET ) ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

# រត់ Web Server ក្នុង Background
threading.Thread(target=run_http_server, daemon=True).start()

# --- ២. កូដ Telegram Bot របស់អ្នក ---
TOKEN = '8758108648:AAEiPmCO15tKVdg5qw7s0Ueh5vUjIDDF9So'
ADMIN_ID = 567818061

bot = telebot.TeleBot(TOKEN)
user_data = {}
DAILY_FREE_LIMIT = 10

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message, 
        f"ជំរាបសួរ! 📊\nសូមផ្ញើរូបថតមក ខ្ញុំនឹងបំប្លែងវាទៅជា PDF ជូន។\n\n"
        f"🎁 ឥតគិតថ្លៃ៖ {DAILY_FREE_LIMIT} រូប/ថ្ងៃ\n"
        f"💳 បន្ថែម៖ បាញ់ប្រាក់ $0.01 ដើម្បីទទួលបាន ៣០ រូបបន្ថែម!"
    )

@bot.message_handler(commands=['add'])
def add_extra_quota(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ អ្នកមិនមានសិទ្ធិប្រើប្រាស់ Command នេះទេ!")
        return

    try:
        args = message.text.split()
        target_user_id = int(args[1])
        today = str(date.today())

        if target_user_id not in user_data or user_data[target_user_id]["date"] != today:
            user_data[target_user_id] = {"date": today, "used": 0, "extra": 0}

        user_data[target_user_id]["extra"] += 30
        bot.reply_to(message, f"✅ បានបន្ថែម ៣០ រូបជូន User ID: `{target_user_id}` រួចរាល់!", parse_mode="Markdown")
        
        bot.send_message(
            target_user_id, 
            "🎉 **ការទូទាត់ទទួលបានជោគជ័យ!**\nអ្នកទទួលបានសិទ្ធិបំប្លែងរូបភាព **៣០ រូបបន្ថែម** សម្រាប់ថ្ងៃនេះ!"
        )
    except Exception as e:
        bot.reply_to(message, "❌ ទម្រង់មិនត្រឹមត្រូវ! សូមវាយ៖ `/add USER_ID` (ឧទាហរណ៍៖ `/add 12345678`)")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    today = str(date.today())

    if user_id not in user_data or user_data[user_id]["date"] != today:
        user_data[user_id] = {"date": today, "used": 0, "extra": 0}

    total_allowed = DAILY_FREE_LIMIT + user_data[user_id]["extra"]
    used_count = user_data[user_id]["used"]

    if used_count >= total_allowed:
        payment_info = (
            f"❌ **អ្នកបានប្រើប្រាស់អស់កំណត់ {total_allowed} រូបសម្រាប់ថ្ងៃនេះហើយ!**\n\n"
            f"💳 **ចង់បំប្លែងបន្ថែម (៣០ រូបទៀត) ៖**\n"
            f"1. បាញ់ប្រាក់ចំនួន **$0.01** មកកាន់ ABA ៖ `000 743 463` (POV Vannak)\n"
            f"2. ផ្ញើវិក្កយបត្រ (Receipt) មកកាន់ Admin ៖ @PovVannak168\n"
            f"3. ភ្ជាប់ជាមួយ **User ID របស់អ្នក** ៖ `{user_id}`\n\n"
            f"*(បន្ទាប់ពីផ្ទៀងផ្ទាត់រួច Admin នឹងបន្ថែម ៣០ រូបជូនភ្លាមៗ!)*"
        )
        bot.reply_to(message, payment_info, parse_mode="Markdown")
        return

    try:
        bot.reply_to(message, f"កំពុងបំប្លែងរូបភាព... ⏳ ({used_count + 1}/{total_allowed})")

        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format='PDF')
        pdf_bytes.seek(0)

        user_data[user_id]["used"] += 1
        remaining = total_allowed - user_data[user_id]["used"]

        bot.send_document(
            message.chat.id, 
            pdf_bytes, 
            visible_file_name="photo_to_pdf.pdf",
            caption=f"នេះជាឯកសារ PDF របស់អ្នក! 📄\n\n*(អាចប្រើបាន {remaining} រូបទៀតសម្រាប់ថ្ងៃនេះ)*"
        )
    except Exception as e:
        bot.reply_to(message, f"មានបញ្ហាក្នុងការបំប្លែង៖ {e}")

print("Bot កំពុងដំណើរការ...")
bot.polling()
