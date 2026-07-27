import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import io
from datetime import date
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- ១. Web Server សម្រាប់ Render + UptimeRobot ---
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

# --- ២. Telegram Bot Configuration (បន្ថែម Timeout វែងជាងមុន) ---
TOKEN = '8758108648:AAEiPmCO15tKVdg5qw7s0Ueh5vUjIDDF9So'
ADMIN_ID = 567818061

bot = telebot.TeleBot(TOKEN)
user_data = {}
user_sessions = {}
DAILY_FREE_LIMIT = 10

# --- អនុគមន៍បង្កើត ប៊ូតុងជ្រើសរើសកញ្ចប់ ---
def get_package_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🥉 $0.10 - 30 រូប", callback_data="pkg_0.10_30")
    btn2 = InlineKeyboardButton("🥈 $0.20 - 60 រូប", callback_data="pkg_0.20_60")
    btn3 = InlineKeyboardButton("🥇 $0.50 - 200 រូប", callback_data="pkg_0.50_200")
    btn4 = InlineKeyboardButton("💎 $1.00 - 500 រូប", callback_data="pkg_1.00_500")
    btn5 = InlineKeyboardButton("🚀 $2.00 - 1,100 រូប", callback_data="pkg_2.00_1100")
    btn6 = InlineKeyboardButton("👑 $5.00 - 3,000 រូប", callback_data="pkg_5.00_3000")
    btn7 = InlineKeyboardButton("🔥 $10.00 - 7,000 រូប", callback_data="pkg_10.00_7000")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)
    return markup

# --- អនុគមន៍បង្កើត ប៊ូតុង Combine រូបភាព ---
def get_combine_keyboard(count):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_done = InlineKeyboardButton(f"📥 បញ្ចប់ & បង្កើត PDF ({count} រូប)", callback_data="finish_combine")
    btn_cancel = InlineKeyboardButton("❌ បោះបង់", callback_data="cancel_combine")
    markup.add(btn_done, btn_cancel)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        f"ជំរាបសួរ! 📊\nសូមផ្ញើរូបថតមក ខ្ញុំនឹងបំប្លែងវាទៅជា PDF ជូន។\n\n"
        f"🎁 **ឥតគិតថ្លៃ ៖** {DAILY_FREE_LIMIT} រូប/ថ្ងៃ\n"
        f"💡 **ទន្លឺ ៖** អាចផ្ញើរូបម្ដងមួយ ឬផ្ញើរូបច្រើនសន្លឹកចូលគ្នាក្នុង File តែមួយបាន!\n\n"
        f"👇 **ប្រសិនបើចង់ទិញកូតបន្ថែម សូមជ្រើសរើសកញ្ចប់ខាងក្រោម ៖**"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_package_keyboard(), parse_mode="Markdown")

# --- Catch ការចុចប៊ូតុងកញ្ចប់ ---
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

    try:
        if os.path.exists('qr.jpg'):
            with open('qr.jpg', 'rb') as qr_photo:
                bot.send_photo(call.message.chat.id, photo=qr_photo, caption=payment_info, reply_markup=admin_markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, payment_info, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, payment_info, reply_markup=admin_markup, parse_mode="Markdown")

# --- Catch ការចុចប៊ូតុងបង្កើត PDF បញ្ចូលគ្នា (Combine) ---
@bot.callback_query_handler(func=lambda call: call.data in ['finish_combine', 'cancel_combine'])
def handle_combine_action(call):
    user_id = call.from_user.id
    
    if call.data == 'cancel_combine':
        if user_id in user_sessions:
            del user_sessions[user_id]
        bot.answer_callback_query(call.id, "បានបោះបង់ការរួមបញ្ចូលរូបភាព!")
        bot.edit_message_text("❌ បានបោះបង់ចោលការបង្កើត PDF រួមបញ្ចូលគ្នា!", call.message.chat.id, call.message.message_id)
        return

    if call.data == 'finish_combine':
        if user_id not in user_sessions or not user_sessions[user_id]:
            bot.answer_callback_query(call.id, "មិនមានរូបភាពសម្រាប់បង្កើត PDF ទេ!")
            return

        bot.answer_callback_query(call.id, "កំពុងបង្កើត និងផ្ញើ PDF...")
        images = user_sessions[user_id]
        
        try:
            pdf_bytes = io.BytesIO()
            # 🛠️ កែសម្រួល៖ បន្ថែម quality=75 និង optimize=True ឱ្យទំហំ PDF ស្រាល មិន timeout ពេល Upload
            images[0].save(
                pdf_bytes, 
                format='PDF', 
                save_all=True, 
                append_images=images[1:], 
                optimize=True, 
                quality=75
            )
            pdf_bytes.seek(0)

            # 🛠️ បន្ថែម timeout=120 (រង់ចាំបានរហូតដល់ ២ នាទី)
            bot.send_document(
                call.message.chat.id,
                pdf_bytes,
                visible_file_name="Combined_Document.pdf",
                caption=f"✅ បានរួមបញ្ចូលរូបភាពចំនួន **{len(images)} រូប** ទៅជា 1 File PDF រួចរាល់!",
                timeout=120
            )
            del user_sessions[user_id]
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"មានបញ្ហាក្នុងការបង្កើត PDF៖ {e}")

# --- Command បន្ថែម Quota ---
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
        bot.reply_to(message, "❌ ទម្រង់មិនត្រឹមត្រូវ! សូមវាយ៖ `/add USER_ID ចំនួនរូប`", parse_mode="Markdown")

# --- ទទួលរូបភាព និងបំប្លែង ---
@bot.message_handler(content_types=['photo', 'document'])
def handle_photo_or_document(message):
    user_id = message.from_user.id
    today = str(date.today())

    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        mime = message.document.mime_type or ""
        doc_name = message.document.file_name or ""
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
        if mime.startswith('image/') or doc_name.lower().endswith(valid_exts):
            file_id = message.document.file_id
        else:
            bot.reply_to(message, "❌ សូមផ្ញើតែរូបភាព (JPG, PNG, WEBP, ...) ប៉ុណ្ណោះ!")
            return

    if not file_id:
        return

    # ពិនិត្យ Quota
    if user_id not in user_data or user_data[user_id]["date"] != today:
        user_data[user_id] = {"date": today, "used": 0, "extra": 0}

    total_allowed = DAILY_FREE_LIMIT + user_data[user_data[user_id].get("extra", 0)] if "extra" in user_data[user_id] else DAILY_FREE_LIMIT
    used_count = user_data[user_id]["used"]

    if used_count >= total_allowed:
        limit_msg = f"⚠️ **អ្នកបានប្រើប្រាស់អស់កំណត់ {total_allowed} រូបសម្រាប់ថ្ងៃនេះហើយ!**\n\nសូមជ្រើសរើសកញ្ចប់ខាងក្រោម ដើម្បីទិញកូតបន្ថែម ៖"
        bot.reply_to(message, limit_msg, reply_markup=get_package_keyboard(), parse_mode="Markdown")
        return

    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # 🛠️ បង្រួមទំហំរូបភាពឱ្យនៅត្រឹមទំហំសមរម្យ (1280px) ដើម្បីកុំឱ្យធំពេក
        max_size = (1280, 1280)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        if user_id not in user_sessions:
            user_sessions[user_id] = []
        
        user_sessions[user_id].append(image)
        user_data[user_id]["used"] += 1
        count = len(user_sessions[user_id])

        msg_text = (
            f"📸 ទទួលបានរូបភាពទី **{count}** រួចរាល់!\n\n"
            f"• ប្រសិនបើចង់បន្ថែមរូបទៀត សូមផ្ញើរូបបន្តបន្ទាប់មក។\n"
            f"• ពេលផ្ញើរូបអស់ហើយ ចុចប៊ូតុងខាងក្រោមដើម្បីបង្កើតជា **1 File PDF** ៖"
        )

        bot.reply_to(message, msg_text, reply_markup=get_combine_keyboard(count), parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"មានបញ្ហាក្នុងការដំណើរការរូបភាព៖ {e}")

print("Bot កំពុងដំណើរការ...")
# 🛠️ បន្ថែម timeout លើ bot.polling ឱ្យប្រព័ន្ធដើរស្ទាត់ និងមិនប្រឈមការបាត់ Connection
bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
