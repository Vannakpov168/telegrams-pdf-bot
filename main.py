import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import io
from datetime import date
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- ១. Web Server សម្រាប់ Render + UptimeRobot (Free Tier) ---
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

threading.Thread(target=run_http_server, daemon=True).start()

# --- ២. Telegram Bot Configuration ---
TOKEN = '8758108648:AAEiPmCO15tKVdg5qw7s0Ueh5vUjIDDF9So'
ADMIN_ID = 567818061

bot = telebot.TeleBot(TOKEN)
user_data = {}
DAILY_FREE_LIMIT = 10

# --- អនុគមន៍បង្កើត ប៊ូតុងជ្រើសរើសកញ្ចប់ (Inline Keyboard) ---
def get_package_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🥉 $0.10 (410៛) - 30រូប", callback_data="pkg_0.10_30")
    btn2 = InlineKeyboardButton("🥈 $0.20 (820៛) - 60រូប", callback_data="pkg_0.20_60")
    btn3 = InlineKeyboardButton("🥇 $0.50 (2,050៛) - 200រូប", callback_data="pkg_0.50_200")
    btn4 = InlineKeyboardButton("💎 $1.00 (4,100៛) - 500រូប", callback_data="pkg_1.00_500")
    btn5 = InlineKeyboardButton("🚀 $2.00 (8,200៛) - 1,100រូប", callback_data="pkg_2.00_1100")
    btn6 = InlineKeyboardButton("👑 $5.00 (20,500៛) - 3,000រូប", callback_data="pkg_5.00_3000")
    btn7 = InlineKeyboardButton("🔥 $10.00 (41,000៛) - 7,000រូប", callback_data="pkg_10.00_7000")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        f"ជំរាបសួរ! 📊\nសូមផ្ញើរូបថតមក ខ្ញុំនឹងបំប្លែងវាទៅជា PDF ជូន។\n\n"
        f"🎁 **ឥតគិតថ្លៃ ៖** {DAILY_FREE_LIMIT} រូប/ថ្ងៃ\n"
        f"💡 **ទន្លឺ ៖** ផ្ញើជា File/Document ឬដាក់ Caption ដើម្បីរក្សាឈ្មោះ File ដើម!\n\n"
        f"👇 **ប្រសិនបើចង់ទិញកូតបន្ថែម សូមជ្រើសរើសកញ្ចប់ខាងក្រោម ៖**"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_package_keyboard(), parse_mode="Markdown")

# --- Catch ការចុចប៊ូតុងកញ្ចប់ (បាញ់រូប KHQR ជូន User) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('pkg_'))
def handle_package_selection(call):
    _, price, amount = call.data.split('_')
    user_id = call.from_user.id
    price_usd = float(price)
    price_khr = int(price_usd * 4100)

    payment_info = (
        f"✅ **អ្នកបានជ្រើសរើសកញ្ចប់ ៖ ${price_usd:.2f} / {price_khr:,} ៛ ({amount} រូប)**\n\n"
        f"📲 **សូមស្កែន QR Code ខាងលើដើម្បីទូទាត់ប្រាក់ ៖**\n"
        f"• **ABA ដុល្លារ ($) ៖** `003 345 485` (${price_usd:.2f})\n"
        f"• **ABA រៀល (៛) ៖** `600 272 171` ({price_khr:,} ៛)\n"
        f"• **ឈ្មោះ ៖** POV VANNAK\n\n"
        f"🆔 **User ID របស់អ្នក ៖** `{user_id}` *(សូម Copy លេខនេះ)*\n\n"
        f"📩 បាញ់ប្រាក់រួច សូមផ្ញើ **រូបភាពវិក្កយបត្រ (Receipt)** + **User ID** មកកាន់ Admin ដើម្បីបើកកញ្ចប់!"
    )

    admin_markup = InlineKeyboardMarkup()
    btn_admin = InlineKeyboardButton("📩 ផ្ញើវិក្កយបត្រទៅ Admin", url="https://t.me/PovVannak168")
    admin_markup.add(btn_admin)

    # ផ្ញើរូប KHQR ទៅកាន់ User
    try:
        if os.path.exists('qr.jpg'):
            with open('qr.jpg', 'rb') as qr_photo:
                bot.send_photo(call.message.chat.id, photo=qr_photo, caption=payment_info, reply_markup=admin_markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, payment_info, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, payment_info, reply_markup=admin_markup, parse_mode="Markdown")

# --- Command បន្ថែម Quota និងផ្ញើសារអរគុណ ---
@bot.message_handler(commands=['add'])
def add_extra_quota(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ អ្នកមិនមានសិទ្ធិប្រើប្រាស់ Command នេះទេ!")
        return

    try:
        args = message.text.split()
        target_user_id = int(args[1])
        amount = int(args[2]) if len(args) > 2 else 30
        today = str(date.today())

        if target_user_id not in user_data or user_data[target_user_id]["date"] != today:
            user_data[target_user_id] = {"date": today, "used": 0, "extra": 0}

        user_data[target_user_id]["extra"] += amount
        bot.reply_to(message, f"✅ បានបន្ថែម {amount} រូបជូន User ID: `{target_user_id}` រួចរាល់!", parse_mode="Markdown")
        
        thank_you_msg = (
            f"🎉 **ការទូទាត់ទទួលបានជោគជ័យ!**\n\n"
            f"សូមអរគុណដែលបានជ្រើសរើសសេវាកម្មយើងខ្ញុំ! 🙏✨\n"
            f"អ្នកទទួលបានសិទ្ធិបំប្លែងរូបភាព **{amount} រូបបន្ថែម** រួចរាល់ហើយ!\n\n"
            f"សូមផ្ញើរូបភាពមកកាន់ Bot ដើម្បីបំប្លែងបានភ្លាមៗ! 📄"
        )
        bot.send_message(target_user_id, thank_you_msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ ទម្រង់មិនត្រឹមត្រូវ! សូមវាយ៖ `/add USER_ID ចំនួនរូប`\nឧទាហរណ៍៖ `/add 12345678 500`", parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'document'])
def handle_photo_or_document(message):
    user_id = message.from_user.id
    today = str(date.today())

    file_id = None
    pdf_filename = "photo_to_pdf.pdf"

    if message.photo:
        file_id = message.photo[-1].file_id
        if message.caption:
            clean_name = "".join(c for c in message.caption if c.isalnum() or c in (' ', '_', '-')).strip()
            if clean_name:
                pdf_filename = f"{clean_name}.pdf"
    elif message.document:
        mime = message.document.mime_type or ""
        doc_name = message.document.file_name or ""
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
        
        if mime.startswith('image/') or doc_name.lower().endswith(valid_exts):
            file_id = message.document.file_id
            base_name = os.path.splitext(doc_name)[0]
            pdf_filename = f"{base_name}.pdf"
        else:
            bot.reply_to(message, "❌ សូមផ្ញើតែរូបភាព (JPG, PNG, WEBP, ...) ប៉ុណ្ណោះ!")
            return

    if not file_id:
        return

    if user_id not in user_data or user_data[user_id]["date"] != today:
        user_data[user_id] = {"date": today, "used": 0, "extra": 0}

    total_allowed = DAILY_FREE_LIMIT + user_data[user_id]["extra"]
    used_count = user_data[user_id]["used"]

    if used_count >= total_allowed:
        limit_msg = (
            f"⚠️ **អ្នកបានប្រើប្រាស់អស់កំណត់ {total_allowed} រូបសម្រាប់ថ្ងៃនេះហើយ!**\n\n"
            f"សូមជ្រើសរើសកញ្ចប់ខាងក្រោម ដើម្បីទិញកូតបន្ថែម ៖"
        )
        bot.reply_to(message, limit_msg, reply_markup=get_package_keyboard(), parse_mode="Markdown")
        return

    try:
        bot.reply_to(message, f"កំពុងបំប្លែង `{pdf_filename}`... ⏳ ({used_count + 1}/{total_allowed})", parse_mode="Markdown")

        file_info = bot.get_file(file_id)
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
            visible_file_name=pdf_filename,
            caption=f"នេះជាឯកសារ PDF របស់អ្នក! 📄\n\n*(អាចប្រើបាន {remaining} រូបទៀតសម្រាប់ថ្ងៃនេះ)*"
        )
    except Exception as e:
        bot.reply_to(message, f"មានបញ្ហាក្នុងការបំប្លែង៖ {e}")

print("Bot កំពុងដំណើរការ...")
bot.polling()
