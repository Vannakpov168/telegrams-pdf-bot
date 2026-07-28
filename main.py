import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import io
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

# --- ២. Telegram Bot Configuration ---
TOKEN = '8758108648:AAEiPmCO15tKVdg5qw7s0Ueh5vUjIDDF9So'

bot = telebot.TeleBot(TOKEN)
user_sessions = {}  # រក្សារូបភាពសម្រាប់ Combine

# --- ប៊ូតុង Donate/ទិញកាហ្វេជូន Admin ---
def get_donate_keyboard():
    markup = InlineKeyboardMarkup()
    btn_donate = InlineKeyboardButton("☕️ ឧបត្ថម្ភថ្លៃកាហ្វេ / Donate ☕️", callback_data="show_donate")
    markup.add(btn_donate)
    return markup

# --- ប៊ូតុង បង្កើត PDF (Combine) ---
def get_combine_keyboard(count):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_done = InlineKeyboardButton(f"📥 បង្កើត PDF ({count} រូប)", callback_data="finish_combine")
    btn_cancel = InlineKeyboardButton("❌ បោះបង់", callback_data="cancel_combine")
    btn_donate = InlineKeyboardButton("☕️ ឧបត្ថម្ភ Admin", callback_data="show_donate")
    markup.add(btn_done, btn_cancel)
    markup.add(btn_donate)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        f"ជំរាបសួរ! 📊\n"
        f"សេវាកម្មបំប្លែងរូបភាពទៅជា PDF **ឥតគិតថ្លៃ ឥតកំណត់ (Unlimited Free)!** 🎉\n\n"
        f"💡 **របៀបប្រើប្រាស់ ៖**\n"
        f"1️⃣ ផ្ញើរូបភាពរបស់អ្នកមកកាន់ Bot (ម្តងមួយៗ ឬច្រើនរូប)\n"
        f"2️⃣ ចុចប៊ូតុង **📥 បង្កើត PDF** ដើម្បីទាញយកឯកសារ\n\n"
        f"🙏 ប្រសិនបើចូលចិត្តសេវាកម្មនេះ លោកអ្នកអាចជួយឧបត្ថម្ភថ្លៃកាហ្វេដើម្បីគាំទ្រ Server បាន!"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_donate_keyboard(), parse_mode="Markdown")

# --- Catch ការចុចប៊ូតុង Donate ---
@bot.callback_query_handler(func=lambda call: call.data == 'show_donate')
def handle_donate_selection(call):
    user_id = call.from_user.id

    payment_info = (
        f"🎉 **សូមអរគុណសម្រាប់ការគាំទ្រ និងឧបត្ថម្ភដល់ការអភិវឌ្ឍន៍ Bot នេះ!** 🙏✨\n\n"
        f"📲 **សូមស្កែន QR Code ខាងលើ ឬផ្ញើតាមគណនី ABA ៖**\n"
        f"• **ABA ដុល្លារ ($) ៖** `003 345 485`\n"
        f"• **ABA រៀល (៛) ៖** `600 272 171`\n"
        f"• **ឈ្មោះ ៖** POV VANNAK\n\n"
        f"❤️ គ្រប់ការឧបត្ថម្ភរបស់អ្នកជាកម្លាំងចិត្តដ៏ធំធេងសម្រាប់យើងខ្ញុំ!"
    )

    try:
        if os.path.exists('qr.jpg'):
            with open('qr.jpg', 'rb') as qr_photo:
                bot.send_photo(call.message.chat.id, photo=qr_photo, caption=payment_info, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, payment_info, parse_mode="Markdown")
    except Exception:
        bot.send_message(call.message.chat.id, payment_info, parse_mode="Markdown")

# --- Catch ការចុចប៊ូតុង បង្កើត PDF ឬ បោះបង់ ---
@bot.callback_query_handler(func=lambda call: call.data in ['finish_combine', 'cancel_combine'])
def handle_combine_action(call):
    user_id = call.from_user.id
    
    if call.data == 'cancel_combine':
        if user_id in user_sessions:
            del user_sessions[user_id]
        bot.answer_callback_query(call.id, "បានបោះបង់!")
        bot.edit_message_text("❌ បានបោះបង់ការបង្កើត PDF!", call.message.chat.id, call.message.message_id)
        return

    if call.data == 'finish_combine':
        if user_id not in user_sessions or not user_sessions[user_id]:
            bot.answer_callback_query(call.id, "មិនមានរូបភាពទេ!")
            return

        bot.answer_callback_query(call.id, "កំពុងបង្កើត PDF...")
        images = user_sessions[user_id]
        
        try:
            pdf_bytes = io.BytesIO()
            images[0].save(
                pdf_bytes, 
                format='PDF', 
                save_all=True, 
                append_images=images[1:], 
                optimize=True, 
                quality=75
            )
            pdf_bytes.seek(0)

            bot.send_document(
                call.message.chat.id,
                pdf_bytes,
                visible_file_name="Document.pdf",
                caption=f"✅ បានបង្កើត PDF ពី **{len(images)} រូប** រួចរាល់!\n\n🙏 ប្រសិនបើពេញចិត្ត សូមជួយ Donate ដើម្បីគាំទ្រ Server Bot ផងណា! ❤️"
            )
            del user_sessions[user_id]
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"មានបញ្ហា ៖ {e}")

# --- ទទួលរូបភាព ---
@bot.message_handler(content_types=['photo', 'document'])
def handle_photo_or_document(message):
    user_id = message.from_user.id

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
            bot.reply_to(message, "❌ សូមផ្ញើតែរូបភាព (JPG, PNG) ប៉ុណ្ណោះ!")
            return

    if not file_id:
        return

    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # បង្រួមទំហំរូបដើម្បីឱ្យ File ស្រាល និងដើរលឿន
        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)

        if user_id not in user_sessions:
            user_sessions[user_id] = []
        
        user_sessions[user_id].append(image)
        count = len(user_sessions[user_id])

        msg_text = (
            f"📸 ទទួលបានរូបភាពទី **{count}** រួចរាល់!\n\n"
            f"• អាចផ្ញើរូបបន្ថែមទៀត ឬចុចប៊ូតុងខាងក្រោមដើម្បីទាញយក **PDF** ៖"
        )

        bot.reply_to(message, msg_text, reply_markup=get_combine_keyboard(count), parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"មានបញ្ហា ៖ {e}")

print("Bot កំពុងដំណើរការ...")
bot.infinity_polling()
