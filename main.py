import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import io
import os
import json
import re
import threading
from datetime import date
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
ADMIN_ID = 567818061 # ជំនួសដោយ User ID Telegram របស់អ្នក

bot = telebot.TeleBot(TOKEN)
user_sessions = {}  # រក្សារូបភាព
user_filenames = {} # រក្សាឈ្មោះ File Name ដែល User វាយចូល
user_timers = {}    # រក្សា Timer

# --- ៣. ប្រព័ន្ធគ្រប់គ្រងស្ថិតិ (Stats Management) ---
STATS_FILE = 'bot_stats.json'

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_users": [], "pdfs_today": 0, "last_date": str(date.today())}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f)
    except Exception as e:
        print(f"Error saving stats: {e}")

bot_stats = load_stats()

def check_new_day():
    today = str(date.today())
    if bot_stats["last_date"] != today:
        bot_stats["pdfs_today"] = 0
        bot_stats["last_date"] = today
        save_stats(bot_stats)

def record_user(user_id):
    if user_id not in bot_stats["total_users"]:
        bot_stats["total_users"].append(user_id)
        save_stats(bot_stats)

# --- មុខងារសម្អាតឈ្មោះ File កុំឱ្យមាន Error ---
def sanitize_filename(filename):
    # រក្សាទុកតែអក្សរ លេខ ដកឃ្លា និងសញ្ញា _ - 
    cleaned = re.sub(r'[^\w\s\ Khmer-]', '', filename).strip()
    return cleaned if cleaned else "Combined_Document"

# --- Command /stats សម្រាប់ Admin ---
@bot.message_handler(commands=['stats'])
def show_admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ អ្នកមិនមានសិទ្ធិប្រើ Command នេះទេ!")
        return

    check_new_day()
    total_users = len(bot_stats["total_users"])
    pdfs_today = bot_stats["pdfs_today"]

    stat_msg = (
        f"📊 **របាយការណ៍ស្ថិតិ Bot** 📊\n\n"
        f"👥 **អ្នកប្រើប្រាស់សរុប (Total Users) ៖** `{total_users} នាក់`\n"
        f"📄 **PDF បានបង្កើតថ្ងៃនេះ ៖** `{pdfs_today} ដង`\n"
        f"📅 **កាលបរិច្ឆេទ ៖** `{bot_stats['last_date']}`"
    )
    bot.reply_to(message, stat_msg, parse_mode="Markdown")

# --- ប៊ូតុង និងមុខងារផ្សេងៗ ---
def get_donate_keyboard():
    markup = InlineKeyboardMarkup()
    btn_donate = InlineKeyboardButton("☕️ ឧបត្ថម្ភថ្លៃកាហ្វេ / Donate ☕️", callback_data="show_donate")
    markup.add(btn_donate)
    return markup

def get_combine_keyboard(count):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_done = InlineKeyboardButton(f"📥 បង្កើត PDF Combine ({count} រូប)", callback_data="finish_combine")
    btn_cancel = InlineKeyboardButton("❌ បោះបង់", callback_data="cancel_combine")
    btn_donate = InlineKeyboardButton("☕️ ឧបត្ថម្ភ Admin", callback_data="show_donate")
    markup.add(btn_done, btn_cancel)
    markup.add(btn_donate)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    record_user(message.from_user.id)
    welcome_text = (
        f"ជំរាបសួរ! 📊\n"
        f"សេវាកម្មបំប្លែងរូបភាពទៅជា PDF **ឥតគិតថ្លៃ ឥតកំណត់!** 🎉\n\n"
        f"💡 **របៀបប្រើប្រាស់ ៖**\n"
        f"1️⃣ ជ្រើសរើស និងផ្ញើរូបភាពរបស់អ្នកចូលមកក្នុង Bot\n"
        f"2️⃣ **ល្បិចពិសេស ៖** លោកអ្នកអាច **វាយឈ្មោះ File ក្នុង Caption** ភ្ជាប់ជាមួយរូបភាព នោះ File PDF នឹងចេញមកតាមឈ្មោះនោះ!\n"
        f"3️⃣ ចុចប៊ូតុង **📥 បង្កើត PDF Combine** ជាការស្រេច!\n\n"
        f"🙏 ប្រសិនបើចូលចិត្តសេវាកម្មនេះ លោកអ្នកអាចជួយឧបត្ថម្ភថ្លៃកាហ្វេដើម្បីគាំទ្រ Server បាន!"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_donate_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == 'show_donate')
def handle_donate_selection(call):
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

@bot.callback_query_handler(func=lambda call: call.data in ['finish_combine', 'cancel_combine'])
def handle_combine_action(call):
    user_id = call.from_user.id
    
    if call.data == 'cancel_combine':
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in user_filenames:
            del user_filenames[user_id]
        bot.answer_callback_query(call.id, "បានបោះបង់!")
        bot.edit_message_text("❌ បានបោះបង់ការបង្កើត PDF!", call.message.chat.id, call.message.message_id)
        return

    if call.data == 'finish_combine':
        if user_id not in user_sessions or not user_sessions[user_id]:
            bot.answer_callback_query(call.id, "មិនមានរូបភាពទេ!")
            return

        bot.answer_callback_query(call.id, "កំពុងបង្កើត PDF Combine...")
        images = user_sessions[user_id]
        
        # កំណត់ឈ្មោះ File តាម Caption របស់ User (បើគ្មានទេ ប្រើ Combined_Document)
        raw_name = user_filenames.get(user_id, "Combined_Document")
        clean_name = sanitize_filename(raw_name)
        final_pdf_name = f"{clean_name}.pdf"
        
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
                visible_file_name=final_pdf_name,
                caption=(
                    f"✅ បានបង្កើត PDF ឈ្មោះ ៖ **{final_pdf_name}**\n"
                    f"📸 ចំនួន ៖ **{len(images)} រូប**\n\n"
                    f"🙏 ប្រសិនបើពេញចិត្ត សូមជួយ Donate ដើម្បីគាំទ្រ Server Bot ផងណា! ❤️"
                ),
                parse_mode="Markdown"
            )
            
            # លុប Data ចាស់ចោលបន្ទាប់ពីផ្ញើរួច
            del user_sessions[user_id]
            if user_id in user_filenames:
                del user_filenames[user_id]

            bot.delete_message(call.message.chat.id, call.message.message_id)

            # កត់ត្រាស្ថិតិ
            check_new_day()
            bot_stats["pdfs_today"] += 1
            save_stats(bot_stats)
            
        except Exception as e:
            bot.send_message(call.message.chat.id, f"មានបញ្ហា ៖ {e}")

def send_combine_prompt(chat_id, user_id):
    if user_id in user_sessions and user_sessions[user_id]:
        count = len(user_sessions[user_id])
        fname = user_filenames.get(user_id, "Combined_Document")
        clean_fname = sanitize_filename(fname)

        msg_text = (
            f"📸 ទទួលបានរូបភាពចំនួន **{count} រូប** រួចរាល់!\n"
            f"🏷 ឈ្មោះ File ដែលត្រូវបង្កើត ៖ **{clean_fname}.pdf**\n\n"
            f"• ចុចប៊ូតុងខាងក្រោមដើម្បីបង្កើតជា File PDF ៖"
        )
        bot.send_message(chat_id, msg_text, reply_markup=get_combine_keyboard(count), parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'document'])
def handle_photo_or_document(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    record_user(user_id)

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

    # ចាប់យក Caption ដែល User វាយភ្ជាប់ជាមួយរូបភាពដំបូងគេ
    if message.caption and user_id not in user_filenames:
        user_filenames[user_id] = message.caption.strip()

    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)

        if user_id not in user_sessions:
            user_sessions[user_id] = []
        
        user_sessions[user_id].append(image)

        if user_id in user_timers:
            user_timers[user_id].cancel()

        t = threading.Timer(1.5, send_combine_prompt, args=[chat_id, user_id])
        user_timers[user_id] = t
        t.start()

    except Exception as e:
        bot.reply_to(message, f"មានបញ្ហា ៖ {e}")

print("Bot កំពុងដំណើរការ...")
bot.infinity_polling()
