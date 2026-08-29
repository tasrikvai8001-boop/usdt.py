import importlib.util
import subprocess
import sys
import os
import time
import json
import random
import string
import threading
from datetime import datetime, timedelta

# --- AUTOMATIC DEPENDENCY CHECK ---
for pkg in ["flask", "pyTelegramBotAPI", "pillow", "requests"]:
    mod = "telebot" if pkg == "pyTelegramBotAPI" else ("PIL" if pkg == "pillow" else pkg)
    if importlib.util.find_spec(mod) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageDraw, ImageFont
import io

# ============================================
# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
# ============================================
app = Flask('')

@app.route('/')
def home():
    return "📧 NR Gmail Shop BDT Bot Engine is Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ============================================
# --- CONFIGURATION & SECURITY ---
# ============================================
BOT_TOKEN = "8979865542:AAH0CnXNCumXFYpRRcxjeNvnjrol9tkFvKw"
ADMIN_ID = 7833766898
BOT_NAME = "📧 𝒩𝑅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒉𝒐𝒑 𝑩𝑫𝑻 📩"
DATA_FILE = "nr_gmail_shop_data.json"

bot = telebot.TeleBot(BOT_TOKEN, num_threads=50)
db_lock = threading.RLock()

# ============================================
# --- DATABASE MANAGEMENT ---
# ============================================
def load_db():
    with db_lock:
        default_db = {
            "users": {},
            "banned_users": [],
            "force_channels": [],
            "ref_bonus_verify": 0.40,
            "min_withdraw": 5.0,
            "withdraw_min_ref": 2,
            "withdraw_fee_percent": 1.0,
            "daily_bonus_amount": 0.10,
            "leaderboard_prizes": [10.0, 4.0, 1.0],
            "maintenance_mode": False,
            "anti_fraud_enabled": True,
            "multi_acc_detection": True,
            "auto_payment_api": "",
            "payment_proof_channel": "",
            "cooldown_time": 10,
            "custom_buttons": {},
            "sys_texts": {
                "welcome": "Welcome back to our bot! Choose an option below:",
                "refer_rules": "Refer your friends and earn instant rewards once they verify!",
                "help_text": "If you face any issues, send your query here for support."
            },
            "tasks": {
                "shortlink": {"desc": "Complete Shortlink Task", "link": "https://example.com/short", "rate": 0.05, "limit": 10},
                "captcha": {"desc": "Solve Images or Text Captchas", "rate": 0.02, "limit": 20},
                "micro_task": {"desc": "Join Channel & Submit Screenshot Proof", "link": "https://t.me/example", "req": "Send Screenshot", "rate": 0.10, "limit": 5},
                "survey": {"desc": "Complete App Install or Survey", "link": "https://example.com/survey", "rate": 0.50, "limit": 2}
            },
            "unlock_conditions": {
                "task_earn": {"ref": 2, "tasks": 0},
                "watch_ads": {"ref": 3, "tasks": 0},
                "captcha_earn": {"ref": 5, "tasks": 0},
                "survey_apps": {"ref": 2, "tasks": 0}
            },
            "pending_proofs": {},
            "pending_withdraws": {},
            "ip_tracker": {}
        }
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump(default_db, f, indent=4, ensure_ascii=False)
            return default_db
        try:
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                for key, val in default_db.items():
                    if key not in data:
                        data[key] = val
                return data
        except:
            return default_db

def save_db(data):
    with db_lock:
        try:
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Database Save Error:", e)

def get_user(user_id, name="User", username=""):
    data = load_db()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "name": name,
            "username": username,
            "balance": 0.0,
            "total_ref_bonus": 0.0,
            "total_withdraw": 0.0,
            "pending_withdraw": 0.0,
            "completed_tasks": 0,
            "rejected_tasks": 0,
            "pending_tasks": 0,
            "lang": "bn",
            "referred_by": None,
            "ref_rewarded": False,
            "referrals": 0,
            "referral_list": [],
            "daily_bonus_claimed": False,
            "last_bonus_date": "",
            "last_active": time.time(),
            "device_id": None,
            "state": None,
            "temp_data": {}
        }
        save_db(data)
    else:
        data["users"][uid]["last_active"] = time.time()
        save_db(data)
    return data["users"][uid]

def update_user(user_id, key, val):
    data = load_db()
    uid = str(user_id)
    if uid in data["users"]:
        data["users"][uid][key] = val
        save_db(data)

# ============================================
# --- TELEBOT STYLISH COLOR BUTTON PATCH ---
# ============================================
_old_inline_dict = InlineKeyboardButton.to_dict
def _new_inline_dict(self):
    d = _old_inline_dict(self)
    if hasattr(self, 'style'): d['style'] = self.style
    return d
InlineKeyboardButton.to_dict = _new_inline_dict

_old_kb_dict = KeyboardButton.to_dict
def _new_kb_dict(self):
    d = _old_kb_dict(self)
    if hasattr(self, 'style'): d['style'] = self.style
    return d
KeyboardButton.to_dict = _new_kb_dict

# ============================================
# --- IMAGE CAPTCHA GENERATOR ---
# ============================================
def generate_image_captcha():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    img = Image.new('RGB', (160, 60), color=(28, 40, 51))
    draw = ImageDraw.Draw(img)
    
    for _ in range(8):
        x1, y1 = random.randint(0, 160), random.randint(0, 60)
        x2, y2 = random.randint(0, 160), random.randint(0, 60)
        draw.line([(x1, y1), (x2, y2)], fill=(100, 100, 100), width=1)
        
    try: font = ImageFont.truetype("arial.ttf", 30)
    except: font = ImageFont.load_default()
        
    draw.text((25, 12), code, fill=(241, 196, 15), font=font)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf, code

# ============================================
# --- FORCE JOIN & LIVE GUARD CHECKER ---
# ============================================
def check_force_join(user_id):
    data = load_db()
    left_channels = []
    for ch in data.get("force_channels", []):
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                left_channels.append(ch)
        except:
            left_channels.append(ch)
    return left_channels

def get_force_join_markup(left_channels):
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in left_channels:
        clean_ch = ch.replace("@", "")
        markup.add(InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{clean_ch}", style="primary"))
    markup.add(InlineKeyboardButton("✅ Verify Now", callback_data="verify_join", style="success"))
    return markup

# ============================================
# --- KEYBOARDS & MENUS ---
# ============================================
TXT_WALLET = "💰 𝑴𝒚 𝑾𝒂𝒍𝒍𝒆𝒕"
TXT_REFER = "⚡ 𝑰𝒏𝒔𝒕𝒂𝒏𝒕 𝑹𝒆𝒇𝒆𝒓"
TXT_DAILY_BONUS = "🎁 𝑫𝒂𝒊𝒍𝒚 𝑩𝒐𝒏𝒖𝒔"
TXT_MY_WORKS = "My Works"
TXT_WITHDRAW = "📥 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘 𝑼𝑺𝑫𝑻"
TXT_LEADERBOARD = "📊 𝑳𝒆𝒂𝒅𝒆𝒓𝒃𝒐𝒂𝒓𝒅"
TXT_SETTINGS = "⚙️ 𝑺𝒆𝒕𝒕𝒊𝒏𝒈𝒔 / 𝑯𝒆𝒍𝒑"
TXT_ADMIN = "⚙️ Admin Panel"

def get_main_menu(user_id):
    data = load_db()
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    markup.add(KeyboardButton(TXT_WALLET, style="primary"), KeyboardButton(TXT_REFER, style="primary"))
    markup.add(KeyboardButton(TXT_DAILY_BONUS, style="success"), KeyboardButton(TXT_MY_WORKS, style="success"))
    markup.add(KeyboardButton(TXT_WITHDRAW, style="danger"), KeyboardButton(TXT_LEADERBOARD, style="secondary"))
    markup.add(KeyboardButton(TXT_SETTINGS, style="secondary"))
    
    for btn_name in data.get("custom_buttons", {}).keys():
        markup.add(KeyboardButton(btn_name, style="primary"))
        
    if int(user_id) == ADMIN_ID:
        markup.add(KeyboardButton(TXT_ADMIN, style="danger"))
        
    return markup

def get_my_works_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🎯 𝑻𝒂𝒔𝒌 & 𝑬𝒂𝒓𝒏", style="primary"), KeyboardButton("📺 𝑾𝒂𝒕𝒄𝒉 𝑨𝒅𝒔", style="primary"))
    markup.add(KeyboardButton("🌐 𝑺𝒉𝒐𝒓𝒕𝒍𝒊𝒏𝒌 𝑩𝒐𝒏𝒖𝒔", style="success"), KeyboardButton("📋 𝑺𝒖𝒓𝒗𝒆𝒚 & 𝑮𝒂𝒎𝒆𝒔", style="success"))
    markup.add(KeyboardButton("⌨️ 𝑪𝒂𝒑𝒕𝒄𝒉𝒂 𝑬𝒂𝒓𝒏", style="warning"), KeyboardButton("🔙 Back", style="danger"))
    return markup

def get_admin_inline_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Set Force Join", callback_data="adm_force_join", style="primary"),
        InlineKeyboardButton("🎁 Set Ref Bonus", callback_data="adm_set_ref_bonus", style="primary")
    )
    markup.add(
        InlineKeyboardButton("💳 Set Min Withdraw", callback_data="adm_set_min_withdraw", style="primary"),
        InlineKeyboardButton("💸 Set Withdraw Fee", callback_data="adm_set_fee", style="primary")
    )
    markup.add(
        InlineKeyboardButton("🌐 Set Shortlink", callback_data="adm_set_shortlink", style="secondary"),
        InlineKeyboardButton("⌨️ Set Captcha Earn", callback_data="adm_set_captcha_earn", style="secondary")
    )
    markup.add(
        InlineKeyboardButton("📲 Set Micro-Tasks", callback_data="adm_set_micro_tasks", style="primary"),
        InlineKeyboardButton("📋 Set Survey & Apps", callback_data="adm_set_survey", style="primary")
    )
    markup.add(
        InlineKeyboardButton("📥 Pending Task Proofs", callback_data="adm_pending_proofs", style="warning"),
        InlineKeyboardButton("💸 Pending Withdrawals", callback_data="adm_pending_withdraws", style="danger")
    )
    markup.add(
        InlineKeyboardButton("🚫 Ban/Unban User", callback_data="adm_ban_unban", style="danger"),
        InlineKeyboardButton("🛡️ Anti-Fraud Toggle", callback_data="adm_toggle_fraud", style="primary")
    )
    markup.add(
        InlineKeyboardButton("📢 Smart Broadcast", callback_data="adm_broadcast_menu", style="primary"),
        InlineKeyboardButton("➕ Add Balance", callback_data="adm_add_bal", style="success")
    )
    markup.add(
        InlineKeyboardButton("➖ Cut Balance", callback_data="adm_cut_bal", style="danger"),
        InlineKeyboardButton("📊 Live Dashboard", callback_data="adm_stats", style="secondary")
    )
    markup.add(
        InlineKeyboardButton("🔴 Maintenance Mode", callback_data="adm_maint", style="danger"),
        InlineKeyboardButton("📁 Database Export", callback_data="adm_export", style="primary")
    )
    markup.add(
        InlineKeyboardButton("➕ Add Custom Btn", callback_data="adm_add_cbtn", style="success"),
        InlineKeyboardButton("🗑️ Del Custom Btn", callback_data="adm_del_cbtn", style="danger")
    )
    markup.add(
        InlineKeyboardButton("🔒 Unlock Conditions", callback_data="adm_unlock_cond", style="secondary"),
        InlineKeyboardButton("🏆 Set Leaderboard Prize", callback_data="adm_set_prizes", style="primary")
    )
    markup.add(
        InlineKeyboardButton("📝 Edit Text Messages", callback_data="adm_edit_texts", style="secondary"),
        InlineKeyboardButton("🎁 Set Daily Bonus Range", callback_data="adm_set_daily_range", style="primary")
    )
    markup.add(
        InlineKeyboardButton("🤖 Auto Payment API", callback_data="adm_auto_pay", style="primary"),
        InlineKeyboardButton("📢 Payment Channel", callback_data="adm_pay_channel", style="secondary")
    )
    markup.add(
        InlineKeyboardButton("🗑️ Delete Active Task", callback_data="adm_del_task", style="danger"),
        InlineKeyboardButton("🔄 Restart Server", callback_data="adm_restart", style="danger")
    )
    markup.add(
        InlineKeyboardButton("❌ Close Panel", callback_data="adm_close", style="danger")
    )
    return markup

# ============================================
# --- AUTOMATIC BACKGROUND THREADS ---
# ============================================
def leaderboard_reset_cron():
    while True:
        try:
            now = datetime.now()
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0 and now.hour >= 12:
                days_until_monday = 7
            target = (now + timedelta(days=days_until_monday)).replace(hour=12, minute=0, second=0, microsecond=0)
            sleep_sec = (target - now).total_seconds()
            time.sleep(sleep_sec)

            data = load_db()
            users = data.get("users", {})
            sorted_users = sorted(users.items(), key=lambda x: x[1].get("referrals", 0), reverse=True)[:3]
            prizes = data.get("leaderboard_prizes", [10.0, 4.0, 1.0])

            for idx, (uid, u_data) in enumerate(sorted_users):
                if idx < len(prizes) and u_data.get("referrals", 0) > 0:
                    pz = prizes[idx]
                    data["users"][uid]["balance"] += pz
                    try:
                        bot.send_message(int(uid), f"🎉 <b>অভিনন্দন!</b> আপনি সাপ্তাহিক লিডারবোর্ডে <b>{idx+1}st</b> স্থান অর্জন করায় <b>${pz}</b> অটোমেটিক বোনাস পেয়েছেন!", parse_mode="HTML")
                    except: pass
            
            for uid in data["users"]:
                data["users"][uid]["referrals"] = 0
            save_db(data)
        except Exception as e:
            print("Leaderboard Cron Error:", e)

def inactive_user_reminder_cron():
    while True:
        try:
            time.sleep(86400) # Check daily
            data = load_db()
            three_days_ago = time.time() - (3 * 86400)
            for uid, u_data in data.get("users", {}).items():
                if u_data.get("last_active", 0) < three_days_ago:
                    try:
                        bot.send_message(int(uid), "🔔 <b>আপনার $20 পর্যন্ত বোনাস অপেক্ষা করছে!</b>\nকাজ শুরু করতে এখনই বটে প্রবেশ করুন।", parse_mode="HTML")
                    except: pass
        except Exception as e:
            print("Inactive Reminder Error:", e)

threading.Thread(target=leaderboard_reset_cron, daemon=True).start()
threading.Thread(target=inactive_user_reminder_cron, daemon=True).start()

# ============================================
# --- START COMMAND HANDLER ---
# ============================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    data = load_db()

    if data.get("maintenance_mode") and int(user_id) != ADMIN_ID:
        bot.send_message(message.chat.id, "🔴 <b>বট বর্তমানে মেইনটেন্যান্স মোডে আছে। কিছুক্ষণ পর আবার চেষ্টা করুন।</b>", parse_mode="HTML")
        return

    if str(user_id) in data.get("banned_users", []):
        bot.send_message(message.chat.id, "⛔ আপনি এই বটে ব্লকড আছেন।")
        return

    user = get_user(user_id, message.from_user.first_name, message.from_user.username or "")

    args = message.text.split()
    if len(args) > 1 and user.get("referred_by") is None:
        ref_id = args[1]
        if ref_id != str(user_id) and ref_id in data["users"]:
            update_user(user_id, "referred_by", ref_id)
            ref_user = data["users"][ref_id]
            if ref_user.get("referrals", 0) > 15:
                bot.send_message(ADMIN_ID, f"⚠️ <b>Rapid Referral Alert!</b>\nUser <code>{ref_id}</code> (@{ref_user.get('username')}) has high rapid referrals!", parse_mode="HTML")

    img_buf, captcha_code = generate_image_captcha()
    update_user(user_id, "state", "verify_captcha_code")
    data = load_db()
    data["users"][str(user_id)]["temp_data"]["captcha_ans"] = captcha_code
    save_db(data)

    bot.send_photo(message.chat.id, img_buf, caption="🤖 <b>SECURITY CAPTCHA CHECK:</b>\n\nছবির ক্যাপচা কোডটি সঠিকভাবে নিচে লিখে দিন:", parse_mode="HTML")

# ============================================
# --- MAIN CALLBACK HANDLER ---
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = load_db()

    if call.data == "verify_join":
        left = check_force_join(user_id)
        if left:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)
            return

        user = get_user(user_id)
        if user.get("referred_by") and not user.get("ref_rewarded"):
            ref_id = str(user["referred_by"])
            if ref_id in data["users"]:
                bonus = data.get("ref_bonus_verify", 0.40)
                data["users"][ref_id]["balance"] += bonus
                data["users"][ref_id]["total_ref_bonus"] += bonus
                data["users"][ref_id]["referrals"] += 1
                data["users"][ref_id]["referral_list"].append({
                    "id": user_id,
                    "name": call.from_user.first_name,
                    "username": call.from_user.username or ""
                })
                data["users"][str(user_id)]["ref_rewarded"] = True
                save_db(data)
                try:
                    bot.send_message(ref_id, f"🎉 <b>New Referral Verification!</b>\nআপনি রেফার বোনাস <b>${bonus}</b> পেয়েছেন!", parse_mode="HTML")
                except: pass

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

        bot.send_message(call.message.chat.id, f"✅ <b>ভেরিফিকেশন সফল হয়েছে!</b>\n\n{data['sys_texts']['welcome']}", parse_mode="HTML", reply_markup=get_main_menu(user_id))

    elif call.data == "claim_daily_bonus":
        user = get_user(user_id)
        today_str = datetime.now().strftime("%Y-%m-%d")

        if user.get("last_bonus_date") == today_str:
            bot.answer_callback_query(call.id, "❌ আপনি আজ ইতিমধ্যেই ডেইলি বোনাস ক্লেইম করেছেন!", show_alert=True)
            return

        if user.get("referrals", 0) < 1 and user.get("completed_tasks", 0) < 2:
            bot.answer_callback_query(call.id, "🔒 বোনাস ক্লেইম করতে অন্তত ১টি রেফার বা ২ টি টাস্ক কমপ্লিট করুন!", show_alert=True)
            return

        b_amt = data.get("daily_bonus_amount", 0.10)
        data["users"][str(user_id)]["balance"] += b_amt
        data["users"][str(user_id)]["last_bonus_date"] = today_str
        save_db(data)

        bot.answer_callback_query(call.id, f"🎉 আপনি ${b_amt} ডেইলি বোনাস ক্লেইম করেছেন!", show_alert=True)
        bot.send_message(call.message.chat.id, f"🎉 <b>দৈনিক বোনাস সফলভাবে অ্যাকাউন্টে যোগ করা হয়েছে: ${b_amt}</b>", parse_mode="HTML")

    elif call.data == "submit_usdt_withdraw":
        user = get_user(user_id)
        min_w = data.get("min_withdraw", 5.0)
        min_ref = data.get("withdraw_min_ref", 2)

        if user["balance"] < min_w:
            bot.answer_callback_query(call.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! মিনিমাম উইথড্র ${min_w}", show_alert=True)
            return

        if user.get("referrals", 0) < min_ref:
            bot.answer_callback_query(call.id, f"❌ উইথড্র করতে অন্তত {min_ref} টি রেফার লাগবে!", show_alert=True)
            return

        update_user(user_id, "state", "enter_usdt_wallet")
        bot.send_message(call.message.chat.id, "📱 <b>আপনার USDT BEP 20 ওয়ালেট এড্রেস পাঠান:</b>", parse_mode="HTML")

    elif call.data == "refresh_wallet":
        user = get_user(user_id)
        msg = (f"👤 <b>Account Details Dashboard</b>\n\n"
               f"🏷️ নাম: <b>{user['name']}</b>\n"
               f"🆔 টেলিগ্রাম চ্যাট আইডি: <code>{user_id}</code>\n"
               f"💰 মোট ব্যালেন্স: <b>${user['balance']:.2f}</b>\n"
               f"👥 মোট রেফার: <b>{user['referrals']} জন</b>\n"
               f"📤 মোট উইথড্র: <b>${user['total_withdraw']:.2f}</b>\n"
               f"⏳ পেন্ডিং টাস্ক: <b>{user['pending_tasks']} টি</b>\n"
               f"❌ রিজেক্ট টাস্ক: <b>{user['rejected_tasks']} টি</b>")
        try:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
            bot.answer_callback_query(call.id, "✅ রিফ্রেশ করা হয়েছে!")
        except: pass

    elif call.data == "set_lang_bn":
        update_user(user_id, "lang", "bn")
        bot.answer_callback_query(call.id, "ভাষা বাংলা সেট করা হয়েছে!")
        bot.send_message(call.message.chat.id, "✅ ভাষা পরিবর্তিত হয়েছে!", reply_markup=get_main_menu(user_id))

    elif call.data == "set_lang_en":
        update_user(user_id, "lang", "en")
        bot.answer_callback_query(call.id, "Language set to English!")
        bot.send_message(call.message.chat.id, "✅ Language Changed!", reply_markup=get_main_menu(user_id))

    # ==================== ADMIN INLINE CALLBACKS ====================
    elif call.data.startswith("adm_") and int(user_id) == ADMIN_ID:
        act = call.data.replace("adm_", "")
        
        if act == "close":
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass

        elif act == "force_join":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("➕ Add Channel", callback_data="adm_add_ch", style="success"),
                InlineKeyboardButton("🗑️ Remove Channel", callback_data="adm_rem_ch", style="danger")
            )
            bot.send_message(call.message.chat.id, f"📢 <b>Force Join Channels:</b>\n<code>{data.get('force_channels', [])}</code>", parse_mode="HTML", reply_markup=markup)

        elif act == "add_ch":
            update_user(user_id, "state", "adm_input_add_ch")
            bot.send_message(call.message.chat.id, "চ্যানেল ইউজারনেম সেন্ড করুন (যেমন: `@mychannel`):")

        elif act == "rem_ch":
            update_user(user_id, "state", "adm_input_rem_ch")
            bot.send_message(call.message.chat.id, "যে চ্যানেল সরাতে চান তার ইউজারনেম সেন্ড করুন:")

        elif act == "set_ref_bonus":
            update_user(user_id, "state", "adm_set_ref_bonus_val")
            bot.send_message(call.message.chat.id, "নতুন রেফার বোনাস অ্যামাউন্ট ($) লিখুন:")

        elif act == "set_min_withdraw":
            update_user(user_id, "state", "adm_set_min_w_val")
            bot.send_message(call.message.chat.id, "নতুন মিনিমাম উইথড্র অ্যামাউন্ট ($) লিখুন:")

        elif act == "set_fee":
            update_user(user_id, "state", "adm_set_fee_val")
            bot.send_message(call.message.chat.id, "উইথড্র ফি শতাংশ (%) লিখুন (যেমন 1.5):")

        elif act == "set_shortlink":
            update_user(user_id, "state", "adm_set_shortlink_val")
            bot.send_message(call.message.chat.id, "Shortlink সেট করতে লিখুন:\n`LINK RATE LIMIT DESC`", parse_mode="Markdown")

        elif act == "set_captcha_earn":
            update_user(user_id, "state", "adm_set_captcha_earn_val")
            bot.send_message(call.message.chat.id, "Captcha Earn সেট করতে লিখুন:\n`RATE LIMIT DESC`", parse_mode="Markdown")

        elif act == "set_micro_tasks":
            update_user(user_id, "state", "adm_set_micro_val")
            bot.send_message(call.message.chat.id, "Micro Task সেট করতে লিখুন:\n`LINK RATE LIMIT REQ`", parse_mode="Markdown")

        elif act == "set_survey":
            update_user(user_id, "state", "adm_set_survey_val")
            bot.send_message(call.message.chat.id, "Survey & Apps সেট করতে লিখুন:\n`LINK RATE DESC`", parse_mode="Markdown")

        elif act == "pending_proofs":
            proofs = data.get("pending_proofs", {})
            if not proofs:
                bot.send_message(call.message.chat.id, "✅ কোনো পেন্ডিং টাস্ক প্রুফ নেই!")
                return
            for p_key, item in proofs.items():
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("✅ Approve", callback_data=f"appr_proof_{p_key}", style="success"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_proof_{p_key}", style="danger")
                )
                bot.send_photo(call.message.chat.id, item["photo"], caption=f"📩 <b>Task Proof Submited!</b>\nUser ID: <code>{item['user_id']}</code>\nTask: {item['task_name']}", parse_mode="HTML", reply_markup=markup)

        elif act == "pending_withdraws":
            withs = data.get("pending_withdraws", {})
            if not withs:
                bot.send_message(call.message.chat.id, "✅ কোনো পেন্ডিং উইথড্র নেই!")
                return
            for w_key, item in withs.items():
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("✅ Approve Pay", callback_data=f"appr_with_{w_key}", style="success"),
                    InlineKeyboardButton("❌ Reject & Refund", callback_data=f"rej_with_{w_key}", style="danger")
                )
                bot.send_message(call.message.chat.id, f"💸 <b>Withdrawal Request!</b>\nUser ID: <code>{item['user_id']}</code>\nWallet: <code>{item['wallet']}</code>\nAmount: <b>${item['amount']}</b>", parse_mode="HTML", reply_markup=markup)

        elif act == "ban_unban":
            update_user(user_id, "state", "adm_ban_unban_val")
            bot.send_message(call.message.chat.id, "Ban বা Unban করতে ইউজারের ID সেন্ড করুন:")

        elif act == "toggle_fraud":
            data["anti_fraud_enabled"] = not data.get("anti_fraud_enabled", True)
            save_db(data)
            st = "ON ✅" if data["anti_fraud_enabled"] else "OFF 🔴"
            bot.send_message(call.message.chat.id, f"🛡️ Anti-Fraud Guard: {st}")

        elif act == "broadcast_menu":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("📢 Text Broadcast", callback_data="adm_bcast_text", style="primary"),
                InlineKeyboardButton("📌 Pin Broadcast", callback_data="adm_bcast_pin", style="primary")
            )
            bot.send_message(call.message.chat.id, "📢 <b>Broadcast Panel:</b>", parse_mode="HTML", reply_markup=markup)

        elif act in ["bcast_text", "bcast_pin"]:
            update_user(user_id, "state", f"adm_input_{act}")
            bot.send_message(call.message.chat.id, "ব্রডকাস্ট মেসেজটি সেন্ড করুন:")

        elif act == "add_bal":
            update_user(user_id, "state", "adm_add_bal_val")
            bot.send_message(call.message.chat.id, "লিখুন: `USER_ID AMOUNT`", parse_mode="Markdown")

        elif act == "cut_bal":
            update_user(user_id, "state", "adm_cut_bal_val")
            bot.send_message(call.message.chat.id, "লিখুন: `USER_ID AMOUNT`", parse_mode="Markdown")

        elif act == "stats":
            msg = (f"📊 <b>Live Analytics Dashboard</b>\n\n"
                   f"👥 Total Registered Users: {len(data['users'])}\n"
                   f"💸 Pending Withdrawals: {len(data['pending_withdraws'])}\n"
                   f"📥 Pending Task Proofs: {len(data['pending_proofs'])}\n"
                   f"🚫 Banned Users: {len(data['banned_users'])}")
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")

        elif act == "maint":
            data["maintenance_mode"] = not data["maintenance_mode"]
            save_db(data)
            st = "চালু (ON) 🔴" if data["maintenance_mode"] else "বন্ধ (OFF) 🟢"
            bot.send_message(call.message.chat.id, f"🔴 Maintenance Mode: {st}")

        elif act == "export":
            with open(DATA_FILE, "rb") as f:
                bot.send_document(call.message.chat.id, f, caption="📁 Database JSON File")

        elif act == "add_cbtn":
            update_user(user_id, "state", "adm_add_cbtn_val")
            bot.send_message(call.message.chat.id, "নতুন বাটনের নাম লিখুন:")

        elif act == "del_cbtn":
            cbtns = data.get("custom_buttons", {})
            if not cbtns:
                bot.send_message(call.message.chat.id, "❌ ডিলিট করার মতো কোনো কাস্টম বাটন নেই!")
            else:
                markup = InlineKeyboardMarkup(row_width=1)
                for btn_n in cbtns.keys():
                    markup.add(InlineKeyboardButton(f"🗑️ Delete: {btn_n}", callback_data=f"del_cbtn_{btn_n}", style="danger"))
                bot.send_message(call.message.chat.id, "🗑️ মুছে ফেলার বাটন সিলেক্ট করুন:", reply_markup=markup)

        elif act == "unlock_cond":
            update_user(user_id, "state", "adm_unlock_cond_val")
            bot.send_message(call.message.chat.id, "লক শর্ত সেট করতে লিখুন:\n`TASK_KEY REF_COUNT`\n(যেমন: task_earn 2)", parse_mode="Markdown")

        elif act == "set_prizes":
            update_user(user_id, "state", "adm_set_prizes_val")
            bot.send_message(call.message.chat.id, "লিখুন: `PRIZE_1 PRIZE_2 PRIZE_3`", parse_mode="Markdown")

        elif act == "edit_texts":
            update_user(user_id, "state", "adm_edit_texts_val")
            bot.send_message(call.message.chat.id, "টেক্সট টাইপ সিলেক্ট করে লিখুন:\n`TYPE TEXT`\n(Types: welcome, refer_rules, help_text)", parse_mode="Markdown")

        elif act == "set_daily_range":
            update_user(user_id, "state", "adm_set_daily_range_val")
            bot.send_message(call.message.chat.id, "ডেইলি বোনাসের পরিমাণ লিখুন:")

        elif act == "auto_pay":
            update_user(user_id, "state", "adm_auto_pay_val")
            bot.send_message(call.message.chat.id, "Binance Pay / Oxapay API Key দিন:")

        elif act == "pay_channel":
            update_user(user_id, "state", "adm_pay_ch_val")
            bot.send_message(call.message.chat.id, "পেমেন্ট প্রুফ চ্যানেলের ইউজারনেম লিখুন (যেমন `@my_proofs`):")

        elif act == "del_task":
            update_user(user_id, "state", "adm_del_task_val")
            bot.send_message(call.message.chat.id, "যে টাস্ক ডিলিট করতে চান তার কী লিখুন (shortlink / captcha / micro_task / survey):")

        elif act == "restart":
            bot.send_message(call.message.chat.id, "🔄 <b>Bot Server Process Restarting...</b>", parse_mode="HTML")
            os.execl(sys.executable, sys.executable, *sys.argv)

    elif call.data.startswith("del_cbtn_") and int(user_id) == ADMIN_ID:
        btn_n = call.data.replace("del_cbtn_", "")
        if btn_n in data.get("custom_buttons", {}):
            del data["custom_buttons"][btn_n]
            save_db(data)
            bot.answer_callback_query(call.id, f"✅ '{btn_n}' মুছে ফেলা হয়েছে!", show_alert=True)
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass

    elif call.data.startswith("appr_proof_") or call.data.startswith("rej_proof_"):
        if int(user_id) != ADMIN_ID: return
        act = "appr" if call.data.startswith("appr_proof_") else "rej"
        p_key = call.data.replace("appr_proof_", "").replace("rej_proof_", "")
        proofs = data.get("pending_proofs", {})
        if p_key in proofs:
            item = proofs[p_key]
            u_id = str(item["user_id"])
            if act == "appr":
                data["users"][u_id]["balance"] += item["rate"]
                data["users"][u_id]["completed_tasks"] += 1
                data["users"][u_id]["pending_tasks"] = max(0, data["users"][u_id]["pending_tasks"] - 1)
                bot.edit_message_caption(f"✅ Approved! ${item['rate']} added.", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, f"🎉 আপনার টাস্ক প্রুফ এপ্রুভ হয়েছে! <b>${item['rate']}</b> ব্যালেন্সে যোগ করা হয়েছে।", parse_mode="HTML")
                except: pass
            else:
                data["users"][u_id]["rejected_tasks"] += 1
                data["users"][u_id]["pending_tasks"] = max(0, data["users"][u_id]["pending_tasks"] - 1)
                bot.edit_message_caption("❌ Task Proof Rejected!", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, "❌ আপনার জমা দেওয়া টাস্ক প্রুফটি বাতিল করা হয়েছে।", parse_mode="HTML")
                except: pass
            del data["pending_proofs"][p_key]
            save_db(data)

    elif call.data.startswith("appr_with_") or call.data.startswith("rej_with_"):
        if int(user_id) != ADMIN_ID: return
        act = "appr" if call.data.startswith("appr_with_") else "rej"
        w_key = call.data.replace("appr_with_", "").replace("rej_with_", "")
        withs = data.get("pending_withdraws", {})
        if w_key in withs:
            item = withs[w_key]
            u_id = str(item["user_id"])
            if act == "appr":
                data["users"][u_id]["total_withdraw"] += item["amount"]
                bot.edit_message_text(f"✅ Withdrawal Paid (${item['amount']}) to {item['wallet']}", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, f"🎉 আপনার <b>${item['amount']}</b> উইথড্র সফলভাবে পেমেন্ট করা হয়েছে!", parse_mode="HTML")
                except: pass
                
                pay_ch = data.get("payment_proof_channel", "")
                if pay_ch:
                    try:
                        bot.send_message(pay_ch, f"🎉 <b>New Payment Paid Out!</b>\n\n👤 User: <code>{u_id}</code>\n💳 Wallet: <code>{item['wallet']}</code>\n💰 Amount: <b>${item['amount']} USDT</b>\n⚡ Status: Approved ✅", parse_mode="HTML")
                    except: pass
            else:
                data["users"][u_id]["balance"] += item["amount"]
                bot.edit_message_text("❌ Withdrawal Rejected & Refunded!", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, f"❌ আপনার <b>${item['amount']}</b> উইথড্র বাতিল করা হয়েছে এবং ব্যালেন্স রিফান্ড করা হয়েছে।", parse_mode="HTML")
                except: pass
            del data["pending_withdraws"][w_key]
            save_db(data)

# ============================================
# --- MAIN MESSAGE ROUTER ---
# ============================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_text_messages(message):
    user_id = message.from_user.id
    data = load_db()

    if data.get("maintenance_mode") and int(user_id) != ADMIN_ID:
        bot.send_message(message.chat.id, "🔴 <b>বট বর্তমানে মেইনটেন্যান্স মোডে আছে।</b>", parse_mode="HTML")
        return

    if str(user_id) in data.get("banned_users", []):
        bot.send_message(message.chat.id, "⛔ আপনি ব্লকড আছেন।")
        return

    user = get_user(user_id, message.from_user.first_name, message.from_user.username or "")
    state = user.get("state")

    # Captcha Code Verification Flow
    if state == "verify_captcha_code":
        c_ans = user.get("temp_data", {}).get("captcha_ans", "")
        if message.text and message.text.strip().upper() == c_ans:
            update_user(user_id, "state", None)
            
            left = check_force_join(user_id)
            if left:
                msg = f"👋 <b>Welcome to {BOT_NAME}!</b>\n\nবটটি ব্যবহার করতে নিচের চ্যানেলগুলোতে জয়েন করুন এবং <b>Verify Now</b> বাটনে ক্লিক করুন:"
                bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=get_force_join_markup(left))
            else:
                bot.send_message(message.chat.id, "✅ <b>ক্যাপচা সফল হয়েছে!</b>", parse_mode="HTML", reply_markup=get_main_menu(user_id))
        else:
            bot.send_message(message.chat.id, "❌ <b>ভুল ক্যাপচা কোড!</b> পুনরায় চেষ্টা করতে /start চাপুন।", parse_mode="HTML")
        return

    # Real-time Enforcement Check
    left = check_force_join(user_id)
    if left and int(user_id) != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ <b>আপনি আমাদের চ্যানেল থেকে লিভ নিয়েছেন! কাজ চালিয়ে যেতে আবার জয়েন করুন:</b>", parse_mode="HTML", reply_markup=get_force_join_markup(left))
        return

    txt = message.text.strip() if message.text else ""

    # ==================== USER FLOW STATES ====================
    if state == "enter_usdt_wallet":
        update_user(user_id, "state", "enter_usdt_amount")
        data = load_db()
        data["users"][str(user_id)]["temp_data"]["wallet"] = txt
        save_db(data)
        bot.send_message(message.chat.id, "💵 <b>আপনার উইথড্র টাকার পরিমাণ (USDT) লিখুন:</b>", parse_mode="HTML")
        return

    elif state == "enter_usdt_amount":
        try:
            amt = float(txt)
            min_w = data.get("min_withdraw", 5.0)
            fee = data.get("withdraw_fee_percent", 1.0)
            net_amt = amt - (amt * (fee / 100.0))

            if amt < min_w or amt > user["balance"]:
                bot.send_message(message.chat.id, f"❌ ইনভ্যালিড পরিমাণ! আপনার ব্যালেন্স: ${user['balance']:.2f}")
                return

            msg_proc = bot.send_message(message.chat.id, "⏳ <b>দয়া করে অপেক্ষা করুন উইথড্র রিকোয়েস্ট পাঠানো হচ্ছে…!</b>", parse_mode="HTML")
            time.sleep(2)
            try: bot.delete_message(message.chat.id, msg_proc.message_id)
            except: pass

            wallet = user["temp_data"]["wallet"]
            data["users"][str(user_id)]["balance"] -= amt
            w_key = f"w_{user_id}_{int(time.time())}"
            data["pending_withdraws"][w_key] = {
                "user_id": user_id,
                "wallet": wallet,
                "amount": net_amt,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            update_user(user_id, "state", None)
            save_db(data)

            bot.send_message(message.chat.id, "✅ <b>আপনার উইথড্র ব্যালেন্স ১২-২৪ ঘন্টার মধ্যে পেয়ে যাবেন।</b>", parse_mode="HTML", reply_markup=get_main_menu(user_id))
            return
        except:
            bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন:")
            return

    elif state == "user_submit_support_ticket":
        update_user(user_id, "state", None)
        bot.send_message(ADMIN_ID, f"📩 <b>New Support Ticket!</b>\nUser: <code>{user_id}</code> (@{user.get('username')})\nMessage: {txt}", parse_mode="HTML")
        bot.send_message(message.chat.id, "✅ <b>আপনার সাপোর্ট টিকিট এডমিনের কাছে পাঠানো হয়েছে!</b>", parse_mode="HTML", reply_markup=get_main_menu(user_id))
        return

    elif state == "submit_micro_task_ss" and message.photo:
        photo_id = message.photo[-1].file_id
        p_key = f"proof_{user_id}_{int(time.time())}"
        data["pending_proofs"][p_key] = {
            "user_id": user_id,
            "photo": photo_id,
            "task_name": "Micro Task Proof",
            "rate": data["tasks"]["micro_task"]["rate"]
        }
        data["users"][str(user_id)]["pending_tasks"] += 1
        update_user(user_id, "state", None)
        save_db(data)
        bot.send_message(message.chat.id, "✅ <b>আপনার প্রুফ স্ক্রিনশট জমা নেওয়া হয়েছে! এডমিন চেক করে বোনাস যুক্ত করবে।</b>", parse_mode="HTML", reply_markup=get_main_menu(user_id))
        return

    # ==================== ADMIN INPUT STATES ====================
    if int(user_id) == ADMIN_ID and state:
        if state == "adm_input_add_ch":
            if txt.startswith("@"):
                data["force_channels"].append(txt)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ চ্যানেল যুক্ত হয়েছে: {txt}")
            update_user(user_id, "state", None)
            return

        elif state == "adm_input_rem_ch":
            if txt in data["force_channels"]:
                data["force_channels"].remove(txt)
                save_db(data)
                bot.send_message(message.chat.id, f"🗑️ চ্যানেল রিমুভ হয়েছে: {txt}")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_ref_bonus_val":
            try:
                data["ref_bonus_verify"] = float(txt)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ নতুন রেফার বোনাস: ${float(txt)}")
            except: bot.send_message(message.chat.id, "❌ সংখ্যা লিখুন।")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_min_w_val":
            try:
                data["min_withdraw"] = float(txt)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ মিনিমাম উইথড্র: ${float(txt)}")
            except: bot.send_message(message.chat.id, "❌ সংখ্যা লিখুন।")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_fee_val":
            try:
                data["withdraw_fee_percent"] = float(txt)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ উইথড্র ফি: {float(txt)}%")
            except: bot.send_message(message.chat.id, "❌ সংখ্যা লিখুন।")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_shortlink_val":
            try:
                lnk, rate, lim, desc = txt.split(" ", 3)
                data["tasks"]["shortlink"] = {"link": lnk, "rate": float(rate), "limit": int(lim), "desc": desc}
                save_db(data)
                bot.send_message(message.chat.id, "✅ Shortlink Task Updated!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `LINK RATE LIMIT DESC`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_captcha_earn_val":
            try:
                rate, lim, desc = txt.split(" ", 2)
                data["tasks"]["captcha"] = {"rate": float(rate), "limit": int(lim), "desc": desc}
                save_db(data)
                bot.send_message(message.chat.id, "✅ Captcha Task Updated!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `RATE LIMIT DESC`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_micro_val":
            try:
                lnk, rate, lim, req = txt.split(" ", 3)
                data["tasks"]["micro_task"] = {"link": lnk, "rate": float(rate), "limit": int(lim), "req": req, "desc": "Micro Task"}
                save_db(data)
                bot.send_message(message.chat.id, "✅ Micro Task Updated!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `LINK RATE LIMIT REQ`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_survey_val":
            try:
                lnk, rate, desc = txt.split(" ", 2)
                data["tasks"]["survey"] = {"link": lnk, "rate": float(rate), "desc": desc}
                save_db(data)
                bot.send_message(message.chat.id, "✅ Survey & Apps Task Updated!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `LINK RATE DESC`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_ban_unban_val":
            u_target = txt.strip()
            if u_target in data["banned_users"]:
                data["banned_users"].remove(u_target)
                bot.send_message(message.chat.id, f"🟢 User {u_target} Unbanned!")
            else:
                data["banned_users"].append(u_target)
                bot.send_message(message.chat.id, f"⛔ User {u_target} Banned!")
            save_db(data)
            update_user(user_id, "state", None)
            return

        elif state in ["adm_input_bcast_text", "adm_input_bcast_pin"]:
            mode = "pin" if state == "adm_input_bcast_pin" else "text"
            cnt = 0
            for uid in data["users"]:
                try:
                    m = bot.send_message(int(uid), f"📢 <b>Broadcast Notice:</b>\n\n{txt}", parse_mode="HTML")
                    if mode == "pin": bot.pin_chat_message(int(uid), m.message_id)
                    cnt += 1
                except: pass
            bot.send_message(message.chat.id, f"✅ Broadcast sent to {cnt} users!")
            update_user(user_id, "state", None)
            return

        elif state == "adm_add_bal_val":
            try:
                u_target, amt = txt.split()
                if u_target in data["users"]:
                    data["users"][u_target]["balance"] += float(amt)
                    save_db(data)
                    bot.send_message(message.chat.id, f"✅ Added ${amt} to {u_target}")
                    try: bot.send_message(int(u_target), f"🎉 Admin added ${amt} to your balance!")
                    except: pass
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `USER_ID AMOUNT`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_cut_bal_val":
            try:
                u_target, amt = txt.split()
                if u_target in data["users"]:
                    data["users"][u_target]["balance"] = max(0.0, data["users"][u_target]["balance"] - float(amt))
                    save_db(data)
                    bot.send_message(message.chat.id, f"✅ Cut ${amt} from {u_target}")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `USER_ID AMOUNT`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_add_cbtn_val":
            data["custom_buttons"][txt] = "reply"
            save_db(data)
            bot.send_message(message.chat.id, f"✅ Custom button '{txt}' added!", reply_markup=get_main_menu(user_id))
            update_user(user_id, "state", None)
            return

        elif state == "adm_unlock_cond_val":
            try:
                t_key, ref_c = txt.split()
                if t_key in data["unlock_conditions"]:
                    data["unlock_conditions"][t_key]["ref"] = int(ref_c)
                    save_db(data)
                    bot.send_message(message.chat.id, f"✅ Unlock condition for {t_key} set to {ref_c} refs!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `TASK_KEY REF_COUNT`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_prizes_val":
            try:
                p1, p2, p3 = txt.split()
                data["leaderboard_prizes"] = [float(p1), float(p2), float(p3)]
                save_db(data)
                bot.send_message(message.chat.id, "✅ Leaderboard prizes updated!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `PRIZE_1 PRIZE_2 PRIZE_3`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_edit_texts_val":
            try:
                t_type, t_val = txt.split(" ", 1)
                if t_type in data["sys_texts"]:
                    data["sys_texts"][t_type] = t_val
                    save_db(data)
                    bot.send_message(message.chat.id, f"✅ Text '{t_type}' updated!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `TYPE TEXT`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "adm_set_daily_range_val":
            try:
                data["daily_bonus_amount"] = float(txt)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ Daily Bonus set to ${float(txt)}")
            except: bot.send_message(message.chat.id, "❌ সংখ্যা লিখুন।")
            update_user(user_id, "state", None)
            return

        elif state == "adm_auto_pay_val":
            data["auto_payment_api"] = txt.strip()
            save_db(data)
            bot.send_message(message.chat.id, "✅ Auto-Payment API Saved!")
            update_user(user_id, "state", None)
            return

        elif state == "adm_pay_ch_val":
            data["payment_proof_channel"] = txt.strip()
            save_db(data)
            bot.send_message(message.chat.id, f"✅ Payment Proof Channel set to {txt}")
            update_user(user_id, "state", None)
            return

        elif state == "adm_del_task_val":
            t_key = txt.strip()
            if t_key in data["tasks"]:
                del data["tasks"][t_key]
                save_db(data)
                bot.send_message(message.chat.id, f"🗑️ Task '{t_key}' deleted!")
            update_user(user_id, "state", None)
            return

    # ==================== MAIN MENU COMMANDS ====================
    if txt == TXT_WALLET:
        msg = (f"👤 <b>Account Details Dashboard</b>\n\n"
               f"🏷️ নাম: <b>{user['name']}</b>\n"
               f"🆔 টেলিগ্রাম চ্যাট আইডি: <code>{user_id}</code>\n"
               f"💰 মোট ব্যালেন্স: <b>${user['balance']:.2f}</b>\n"
               f"👥 মোট রেফার: <b>{user['referrals']} জন</b>\n"
               f"📤 মোট উইথড্র: <b>${user['total_withdraw']:.2f}</b>\n"
               f"⏳ পেন্ডিং টাস্ক: <b>{user['pending_tasks']} টি</b>\n"
               f"❌ রিজেক্ট টাস্ক: <b>{user['rejected_tasks']} টি</b>")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 রিফ্রেশ করুন", callback_data="refresh_wallet", style="primary"))
        bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

    elif txt == TXT_REFER:
        bot_uname = bot.get_me().username
        ref_link = f"https://t.me/{bot_uname}?start={user_id}"
        msg = (f"⚡ <b>Instant Referral Program</b>\n\n"
               f"👤 নাম: <b>{user['name']}</b>\n"
               f"👥 মোট রেফার: <b>{user['referrals']} জন</b>\n"
               f"🔗 রেফার লিংক:\n<code>{ref_link}</code>\n\n"
               f"📜 <b>রুলস:</b> {data['sys_texts']['refer_rules']}")
        
        markup = InlineKeyboardMarkup(row_width=2)
        share_tg = f"https://t.me/share/url?url={ref_link}&text=Join%20Bot%20and%20Earn!"
        share_wa = f"https://api.whatsapp.com/send?text=Join%20Bot%20and%20Earn:%20{ref_link}"
        markup.add(
            InlineKeyboardButton("📲 WhatsApp-শেয়ার", url=share_wa, style="primary"),
            InlineKeyboardButton("✈️ Telegram-শেয়ার", url=share_tg, style="primary")
        )
        bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

    elif txt == TXT_DAILY_BONUS:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="claim_daily_bonus", style="success"))
        bot.send_message(message.chat.id, "🎁 <b>দৈনিক বোনাস ক্লেম করতে নিচের বাটনে চাপ দিন:</b>", parse_mode="HTML", reply_markup=markup)

    elif txt == TXT_MY_WORKS:
        bot.send_message(message.chat.id, "🛠️ <b>My Works Panel:</b>\n\nপছন্দের টাস্ক বেছে নিন:", parse_mode="HTML", reply_markup=get_my_works_menu())

    elif txt == "🎯 𝑻𝒂𝒔𝒌 & 𝑬𝒂𝒓𝒏":
        cond = data["unlock_conditions"]["task_earn"]
        if user.get("referrals", 0) < cond["ref"]:
            bot.send_message(message.chat.id, f"🔒 <b>এই কাজ থেকে দৈনিক $২ আয় করতে অন্তত {cond['ref']} জন বন্ধুকে শেয়ার করুন।</b>", parse_mode="HTML")
        else:
            update_user(user_id, "state", "submit_micro_task_ss")
            bot.send_message(message.chat.id, f"🎯 <b>Micro Task:</b>\n{data['tasks']['micro_task']['desc']}\nLink: {data['tasks']['micro_task']['link']}\n\nকাজ শেষ করে নিচে প্রুফ স্ক্রিনশট পাঠান:", parse_mode="HTML")

    elif txt == "📺 𝑾𝒂𝒕𝒄𝒉 𝑨𝒅𝒔":
        cond = data["unlock_conditions"]["watch_ads"]
        if user.get("referrals", 0) < cond["ref"]:
            bot.send_message(message.chat.id, f"🔒 <b>এই কাজ আনলক করতে অন্তত {cond['ref']} জন বন্ধুকে শেয়ার করুন।</b>", parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "📺 <b>Watch Ads Task Available!</b>", parse_mode="HTML")

    elif txt == "🌐 𝑺𝒉𝒐𝒓𝒕𝒍𝒊𝒏𝒌 𝑩𝒐𝒏𝒖𝒔":
        st = data["tasks"]["shortlink"]
        bot.send_message(message.chat.id, f"🌐 <b>Shortlink Task:</b>\n{st['desc']}\nLink: {st['link']}\nRate: ${st['rate']}", parse_mode="HTML")

    elif txt == "📋 𝑺𝒖𝒓𝒗𝒆𝒚 & 𝑮𝒂𝒎𝒆𝒔":
        cond = data["unlock_conditions"]["survey_apps"]
        if user.get("referrals", 0) < cond["ref"]:
            bot.send_message(message.chat.id, f"🔒 <b>এই সার্ভে কাজ আনলক করতে অন্তত {cond['ref']} জন রেফার লাগবে।</b>", parse_mode="HTML")
        else:
            sv = data["tasks"]["survey"]
            bot.send_message(message.chat.id, f"📋 <b>Survey Task:</b>\n{sv['desc']}\nLink: {sv['link']}", parse_mode="HTML")

    elif txt == "⌨️ 𝑪𝒂𝒑𝒕𝒄𝒉𝒂 𝑬𝒂𝒓𝒏":
        cond = data["unlock_conditions"]["captcha_earn"]
        if user.get("referrals", 0) < cond["ref"]:
            bot.send_message(message.chat.id, f"🔒 <b>ক্যাপচা আয় আনলক করতে অন্তত {cond['ref']} জন রেফার লাগবে।</b>", parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "⌨️ <b>Captcha Earn Available!</b>", parse_mode="HTML")

    elif txt == "🔙 Back":
        bot.send_message(message.chat.id, "Main Menu", reply_markup=get_main_menu(user_id))

    elif txt == TXT_WITHDRAW:
        msg = f"📥 <b>USDT Withdrawal System</b>\n\nআপনার ব্যালেন্স: <b>${user['balance']:.2f} USDT</b>\nমিনিমাম উইথড্র: <b>${data.get('min_withdraw', 5.0)} USDT</b>"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💸 উইথড্র করুন", callback_data="submit_usdt_withdraw", style="success"))
        bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

    elif txt == TXT_LEADERBOARD:
        prizes = data.get("leaderboard_prizes", [10.0, 4.0, 1.0])
        msg = (f"📊 <b>Weekly Top Leaderboard Rewards</b> 📊\n\n"
               f"🥇 1st Place: <b>${prizes[0]} USDT</b>\n"
               f"🥈 2nd Place: <b>${prizes[1]} USDT</b>\n"
               f"🥉 3rd Place: <b>${prizes[2]} USDT</b>\n\n"
               f"⏰ <i>প্রতি সোমবার দুপুর ১২:০০ টায় স্বয়ংক্রিয়ভাবে বিজয়ীদের পুরস্কৃত করা হয়!</i>")
        bot.send_message(message.chat.id, msg, parse_mode="HTML")

    elif txt == TXT_SETTINGS:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_lang_bn", style="primary"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en", style="primary")
        )
        bot.send_message(message.chat.id, f"⚙️ <b>Settings & Support</b>\n\n{data['sys_texts']['help_text']}\n\nআপনার কোনো বার্তা থাকলে নিচে টাইপ করুন:", parse_mode="HTML", reply_markup=markup)
        update_user(user_id, "state", "user_submit_support_ticket")

    elif txt == TXT_ADMIN and int(user_id) == ADMIN_ID:
        bot.send_message(message.chat.id, "⚙️ <b>Admin Control Panel:</b>", parse_mode="HTML", reply_markup=get_admin_inline_menu())

    elif txt in data.get("custom_buttons", {}):
        bot.send_message(message.chat.id, f"🔘 <b>{txt}:</b>\n\nএই বাটনে কাস্টম লিঙ্ক বা টেক্সট সেট করা আছে।", parse_mode="HTML")

# ============================================
# --- ENGINE START ---
# ============================================
if __name__ == "__main__":
    keep_alive()
    print(f"🚀 {BOT_NAME} Started Successfully...")
    bot.infinity_polling()
