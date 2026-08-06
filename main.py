import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import io
import os
import json
import re
import threading
import gc
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from pypdf import PdfReader, PdfWriter

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
ADMIN_ID = 567818061 

bot = telebot.TeleBot(TOKEN)
user_sessions = {}      # រក្សារូបភាព
user_filenames = {}     # រក្សាឈ្មោះ File
user_prompt_msg = {}    # រក្សា Message ID របស់ប៊ូតុងជម្រើស
user_timers = {}        # រក្សា Timer
user_passwords = {}     # រក្សា Password (បោះបង់ ឬកំណត់)
user_awaiting_feedback = set() # រក្សា trạng thái ពេល user កំពុងសរសេរ feedback
user_awaiting_pass = set()     # រក្សា trạng thái ពេល user កំពុងវាយ password

# --- ៣. ប្រព័ន្ធគ្រប់គ្រងស្ថិតិ ---
STATS_FILE = 'bot_stats.json'

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data["total_users"] = list(set(data.get("total_users", [])))
                if "pdfs_today" not in data: data["pdfs_today"] = 0
                if "photos_today" not in data: data["photos_today"] = 0
                if "last_date" not in data: data["last_date"] = str(date.today())
                return data
        except Exception:
            pass
    return {"total_users": [], "pdfs_today": 0, "photos_today": 0, "last_date": str(date.today())}

bot_stats = load_stats()

def save_stats():
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving stats: {e}")

def check_new_day():
    today = str(date.today())
    if bot_stats["last_date"] != today:
        bot_stats["pdfs_today"] = 0
        bot_stats["photos_today"] = 0
        bot_stats["last_date"] = today
        save_stats()

def record_user(user_id):
    check_new_day()
    current_users = set(bot_stats["total_users"])
    if user_id not in current_users:
        current_users.add(user_id)
        bot_stats["total_users"] = list(current_users)
        save_stats()

def sanitize_filename(filename):
    cleaned = re.sub(r'[^\w\s\u1780-\u17FF-]', '', filename).strip()
    cleaned = cleaned.replace('_', ' ')
    return cleaned if cleaned else "Combined_Document"

# --- Command /stats សម្រាប់ Admin ---
@bot.message_handler(commands=['stats'])
def show_admin_stats(message):
    record_user(message.from_user.id)
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ អ្នកមិនមានសិទ្ធិប្រើ Command នេះទេ!")
        return

    check_new_day()
    total_users_count = len(set(bot_stats["total_users"]))
    pdfs_today = bot_stats["pdfs_today"]
    photos_today = bot_stats["photos_today"]

    stat_msg = (
        f"📊 **របាយការណ៍ស្ថិតិ Bot (Admin Only)** 📊\n\n"
        f"👥 **អ្នកប្រើប្រាស់សរុប (Unique Users) ៖** `{total_users_count} នាក់`\n"
        f"🖼 **រូបភាព Uploaded ថ្ងៃនេះ ៖** `{photos_today} រូប`\n"
        f"📄 **PDF បង្កើតបានថ្ងៃនេះ ៖** `{pdfs_today} ឯកសារ`\n"
        f"📅 **កាលបរិច្ឆេទ ៖** `{bot_stats['last_date']}`"
    )
    bot.reply_to(message, stat_msg, parse_mode="Markdown")

# --- Keyboards ---
def get_donate_keyboard():
    markup = InlineKeyboardMarkup()
    btn_donate = InlineKeyboardButton("☕️ ឧបត្ថម្ភថ្លៃកាហ្វេ / Donate ☕️", callback_data="show_donate")
    btn_feedback = InlineKeyboardButton("📩 ផ្ញើសារទៅ Admin / Feedback", callback_data="send_feedback")
    markup.add(btn_donate)
    markup.add(btn_feedback)
    return markup

def get_quality_keyboard(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    q100 = InlineKeyboardButton("✨ 100%", callback_data="make_100")
    q75  = InlineKeyboardButton("⚡️ 75%", callback_data="make_75")
    q50  = InlineKeyboardButton("📦 50%", callback_data="make_50")
    q20  = InlineKeyboardButton("🪶 20%", callback_data="make_20")
    
    # បង្ហាញ 상태 Password
    pass_status = "🔒 កំណត់ Pass: " + ("✅ មាន" if user_passwords.get(user_id) else "❌ គ្មាន")
    btn_pass = InlineKeyboardButton(pass_status, callback_data="set_password")
    
    btn_cancel = InlineKeyboardButton("❌ បោះបង់", callback_data="cancel_combine")
    btn_donate = InlineKeyboardButton("☕️ ឧបត្ថម្ភ Admin", callback_data="show_donate")
    
    markup.add(q100, q75)
    markup.add(q50, q20)
    markup.add(btn_pass)
    markup.add(btn_cancel, btn_donate)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    record_user(message.from_user.id)
    welcome_text = (
        f"ជំរាបសួរ! 📊\n"
        f"សេវាកម្មបំប្លែងរូបភាពទៅជា PDF **ឥតគិតថ្លៃ ឥតកំណត់!** 🎉\n\n"
        f"💡 **របៀបប្រើប្រាស់ ៖**\n"
        f"1️⃣ ជ្រើសរើស និងផ្ញើរូបភាពរបស់អ្នកចូលមកក្នុង Bot\n"
        f"2️⃣ អាចចុច **🔒 កំណត់ Pass** ដើម្បីដាក់លេខកូដសម្ងាត់លើ PDF\n"
        f"3️⃣ **ជ្រើសរើស Quality (100%, 75%, 50%, 20%)** ដើម្បីទាញយក PDF ភ្លាមៗ!\n\n"
        f"🙏 ប្រសិនបើចូលចិត្តសេវាកម្មនេះ លោកអ្នកអាចជួយឧបត្ថម្ភថ្លៃកាហ្វេបាន!"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_donate_keyboard(), parse_mode="Markdown")

# --- 📩 មុខងារ Feedback / Contact Admin ---
@bot.callback_query_handler(func=lambda call: call.data == 'send_feedback')
def prompt_feedback(call):
    user_id = call.from_user.id
    user_awaiting_feedback.add(user_id)
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id, 
        "✍️ **សូមវាយអត្ថបទ ឬសាររបស់អ្នកខាងក្រោម ៖**\n\n(សារនេះនឹងត្រូវបញ្ជូនទៅកាន់ Admin ផ្ទាល់)",
        parse_mode="Markdown"
    )

# --- 🔒 មុខងារ Set Password ---
@bot.callback_query_handler(func=lambda call: call.data == 'set_password')
def prompt_password(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    if user_passwords.get(user_id):
        # ប្រសិនបើមាន Password រួច ចុចដើម្បីដោះចេញវិញ
        del user_passwords[user_id]
        bot.send_message(call.message.chat.id, "🔓 **បានលុប Password ចោលវិញរួចរាល់!**", parse_mode="Markdown")
        send_or_update_prompt(call.message.chat.id, user_id)
    else:
        user_awaiting_pass.add(user_id)
        bot.send_message(call.message.chat.id, "🔐 **សូមវាយបញ្ចូល Password សម្រាប់ការពារ File PDF របស់អ្នក ៖**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == 'show_donate')
def handle_donate_selection(call):
    record_user(call.from_user.id)
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

# --- បង្កើត PDF + Encrypt Password ករណីមាន ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('make_'))
def handle_make_pdf(call):
    user_id = call.from_user.id
    record_user(user_id)
    selected_quality = int(call.data.split('_')[1])
    
    if user_id not in user_sessions or not user_sessions[user_id]:
        bot.answer_callback_query(call.id, "មិនមានរូបភាពទេ!")
        return

    bot.answer_callback_query(call.id, f"កំពុងបង្កើត PDF ({selected_quality}%)...")
    images = user_sessions[user_id]
    
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
            quality=selected_quality
        )
        pdf_bytes.seek(0)

        # 🔒 ប្រសិនបើ User បានកំណត់ Password
        user_pwd = user_passwords.get(user_id)
        if user_pwd:
            reader = PdfReader(pdf_bytes)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(user_pwd)
            
            encrypted_bytes = io.BytesIO()
            writer.write(encrypted_bytes)
            encrypted_bytes.seek(0)
            pdf_bytes = encrypted_bytes

        caption_msg = (
            f"✅ បានបង្កើត PDF រួចរាល់!\n"
            f"📸 ចំនួន ៖ {len(images)} រូប\n"
            f"⚙️ គុណភាព ៖ {selected_quality}%\n"
            f"🔒 Password ៖ {f'`{user_pwd}`' if user_pwd else 'គ្មាន'}\n\n"
            f"🙏 ប្រសិនបើពេញចិត្ត សូមជួយ Donate ដើម្បីគាំទ្រ Server Bot ផងណា! ❤️"
        )

        bot.send_document(
            call.message.chat.id,
            pdf_bytes,
            visible_file_name=final_pdf_name,
            caption=caption_msg,
            parse_mode="Markdown"
        )
        
        # 🧹 សម្អាត Memory
        del user_sessions[user_id]
        if user_id in user_filenames: del user_filenames[user_id]
        if user_id in user_prompt_msg: del user_prompt_msg[user_id]
        if user_id in user_passwords: del user_passwords[user_id]
        gc.collect()

        bot.delete_message(call.message.chat.id, call.message.message_id)

        check_new_day()
        bot_stats["pdfs_today"] += 1
        save_stats()
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"មានបញ្ហា ៖ {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_combine')
def handle_cancel(call):
    user_id = call.from_user.id
    record_user(user_id)
    if user_id in user_sessions: del user_sessions[user_id]
    if user_id in user_filenames: del user_filenames[user_id]
    if user_id in user_prompt_msg: del user_prompt_msg[user_id]
    if user_id in user_passwords: del user_passwords[user_id]
    gc.collect()
    
    bot.answer_callback_query(call.id, "បានបោះបង់!")
    bot.edit_message_text("❌ បានបោះបង់ការបង្កើត PDF!", call.message.chat.id, call.message.message_id)

def send_or_update_prompt(chat_id, user_id):
    if user_id in user_sessions and user_sessions[user_id]:
        count = len(user_sessions[user_id])
        fname = user_filenames.get(user_id, "Combined_Document")
        clean_fname = sanitize_filename(fname)
        pwd_info = f"🔐 Password ៖ <b>{user_passwords[user_id]}</b>" if user_id in user_passwords else "🔓 Password ៖ <b>គ្មាន</b>"

        msg_text = (
            f"📸 ទទួលបានរូបភាពចំនួន <b>{count} រូប</b> រួចរាល់!\n"
            f"🏷 ឈ្មោះ File ៖ <b>{clean_fname}.pdf</b>\n"
            f"{pwd_info}\n\n"
            f"👇 <b>សូមជ្រើសរើស Quality ខាងក្រោម ដើម្បីបង្កើតជា PDF ៖</b>"
        )

        if user_id in user_prompt_msg:
            try:
                bot.edit_message_text(
                    msg_text, 
                    chat_id, 
                    user_prompt_msg[user_id], 
                    reply_markup=get_quality_keyboard(user_id), 
                    parse_mode="HTML"
                )
                return
            except Exception:
                pass

        msg = bot.send_message(chat_id, msg_text, reply_markup=get_quality_keyboard(user_id), parse_mode="HTML")
        user_prompt_msg[user_id] = msg.message_id

# --- ចាប់យករាល់ការវាយអត្ថបទ (Text Messages) សម្រាប់ Feedback និង Password ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_inputs(message):
    user_id = message.from_user.id
    text = message.text.strip()

    # 1️⃣ ករណី User កំពុងផ្ញើ Feedback មក Admin
    if user_id in user_awaiting_feedback:
        user_awaiting_feedback.remove(user_id)
        
        # ផ្ញើសាររាយការណ៍ទៅកាន់ Admin ផ្ទាល់
        fb_msg = (
            f"📩 **សារថ្មីទទួលបានពី User!**\n\n"
            f"👤 **ឈ្មោះ ៖** {message.from_user.first_name}\n"
            f"🆔 **User ID ៖** `{user_id}`\n"
            f"💬 **អត្ថបទ ៖**\n{text}"
        )
        try:
            bot.send_message(ADMIN_ID, fb_msg, parse_mode="Markdown")
            bot.reply_to(message, "✅ **សាររបស់អ្នកត្រូវបានបញ្ជូនទៅកាន់ Admin រួចរាល់! សូមអរគុណ!**", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, "❌ មិនអាចបញ្ជូនសារបានឡើយ!")
        return

    # 2️⃣ ករណី User កំពុងវាយ Password
    if user_id in user_awaiting_pass:
        user_awaiting_pass.remove(user_id)
        user_passwords[user_id] = text
        bot.reply_to(message, f"🔐 **បានរក្សាទុក Password: `{text}` រួចរាល់!**", parse_mode="Markdown")
        if user_id in user_sessions:
            send_or_update_prompt(message.chat.id, user_id)
        return

    # ករណី Command ផ្សេងៗ
    if text.startswith('/'):
        return

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

    if message.caption and user_id not in user_filenames:
        user_filenames[user_id] = message.caption.strip()

    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        image = Image.open(io.BytesIO(downloaded_file))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        image.thumbnail((1024, 1024), Image.Resampling.BILINEAR)

        if user_id not in user_sessions:
            user_sessions[user_id] = []
        
        user_sessions[user_id].append(image)

        bot_stats["photos_today"] = bot_stats.get("photos_today", 0) + 1
        save_stats()

        if user_id in user_timers:
            user_timers[user_id].cancel()

        t = threading.Timer(2.0, send_or_update_prompt, args=[chat_id, user_id])
        user_timers[user_id] = t
        t.start()

    except Exception as e:
        print(f"Error handling image: {e}")
        bot.reply_to(message, "❌ មានបញ្ហាក្នុងការទាញយករូបភាព! សូមសាកល្បងផ្ញើម្តងទៀត។")

print("Bot កំពុងដំណើរការ...")
bot.infinity_polling()
