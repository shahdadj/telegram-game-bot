import requests
import time
import random
import json
from database import init_db, add_user, get_user, update_user

TOKEN = "8587480321:AAHQtL4tJASYVhcP-zuvui0rMMk8aBebE0g"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

init_db()

last_update_id = None
active_games = {}
attempts = {}
pending_bets = {}

# ---------------- ابزار کمکی ----------------

def get_display_name(user):
    username = user.get("username")
    if username:
        return "@" + username
    return str(user["id"])

# ---------------- ارسال پیام ----------------

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)

    res = requests.post(f"{BASE_URL}/sendMessage", data=data).json()
    return res

def edit_message(chat_id, message_id, text):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    requests.post(f"{BASE_URL}/editMessageText", data=data)

# ---------------- منو ----------------

def show_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎲 حدس عدد", "callback_data": "number"}],
            [{"text": "🔥 شرط‌بندی", "callback_data": "bet"}],
            [{"text": "💰 موجودی", "callback_data": "balance"}]
        ]
    }
    send_message(chat_id, "🎮 انتخاب کن:", keyboard)

# ---------------- بازی حدس عدد ----------------

def start_number_game(chat_id, user_id):
    active_games[user_id] = random.randint(1, 100)
    attempts[user_id] = 0
    send_message(chat_id, "🎲 یک عدد بین 1 تا 100 انتخاب کردم!")

def check_guess(chat_id, user_id, guess):
    if user_id not in active_games:
        return

    attempts[user_id] += 1
    number = active_games[user_id]
    tries = attempts[user_id]
    tokens = get_user(user_id)[0]

    if guess == number:

        if tries <= 5:
            reward = 50
        elif tries <= 11:
            reward = 40
        elif tries <= 35:
            reward = 20
        elif tries <= 85:
            reward = 10
        else:
            reward = 1

        update_user(user_id, tokens + reward)

        send_message(chat_id,
            f"🎉 درست حدس زدی!\n"
            f"تلاش: {tries}\n"
            f"جایزه: {reward}"
        )

        del active_games[user_id]
        del attempts[user_id]

    elif guess < number:
        send_message(chat_id, "🔼 بزرگ‌تره")
    else:
        send_message(chat_id, "🔽 کوچیک‌تره")

# ---------------- موجودی ----------------

def show_balance(chat_id, user_id):
    tokens = get_user(user_id)[0]
    send_message(chat_id, f"💰 موجودی: {tokens}")

# ---------------- ساخت شرط ----------------

def create_bet(chat_id, user, amount):
    user_id = user["id"]
    name = get_display_name(user)

    tokens = get_user(user_id)[0]
    if tokens < amount:
        send_message(chat_id, "❌ سکه کافی نداری")
        return

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ قبول", "callback_data": "accept"},
                {"text": "❌ لغو", "callback_data": "cancel"}
            ]
        ]
    }

    res = send_message(
        chat_id,
        f"🎲 شرط {amount} سکه‌ای\n"
        f"سازنده: {name}",
        keyboard
    )

    message_id = res["result"]["message_id"]

    pending_bets[chat_id] = {
        "creator": user,
        "amount": amount,
        "message_id": message_id
    }

# ---------------- دریافت آپدیت ----------------

def get_updates():
    global last_update_id
    params = {"timeout": 30}
    if last_update_id:
        params["offset"] = last_update_id + 1
    return requests.get(f"{BASE_URL}/getUpdates", params=params).json()

print("ربات روشن شد...")

# ---------------- حلقه اصلی ----------------

while True:
    try:
        updates = get_updates()

        if updates.get("ok"):
            for update in updates["result"]:
                last_update_id = update["update_id"]

                # ---------- دکمه ----------
                if "callback_query" in update:
                    query = update["callback_query"]
                    chat_id = query["message"]["chat"]["id"]
                    user = query["from"]
                    user_id = user["id"]
                    data = query["data"]

                    add_user(user_id)

                    if data == "number":
                        start_number_game(chat_id, user_id)

                    elif data == "bet":
                        send_message(chat_id, "مثال:\nشرطبندی 20")

                    elif data == "balance":
                        show_balance(chat_id, user_id)

                    elif data == "accept":

                        if chat_id not in pending_bets:
                            continue

                        bet = pending_bets[chat_id]
                        creator = bet["creator"]
                        amount = bet["amount"]
                        message_id = bet["message_id"]

                        if user_id == creator["id"]:
                            send_message(chat_id, "❌ نمی‌تونی شرط خودتو قبول کنی")
                            continue

                        creator_tokens = get_user(creator["id"])[0]
                        user_tokens = get_user(user_id)[0]

                        if creator_tokens < amount or user_tokens < amount:
                            send_message(chat_id, "❌ یکی سکه کافی نداره")
                            continue

                        update_user(creator["id"], creator_tokens - amount)
                        update_user(user_id, user_tokens - amount)

                        winner = random.choice([creator["id"], user_id])
                        winner_tokens = get_user(winner)[0]
                        update_user(winner, winner_tokens + amount * 2)

                        winner_name = get_display_name(
                            creator if winner == creator["id"] else user
                        )

                        edit_message(
                            chat_id,
                            message_id,
                            f"🔥 شرط انجام شد!\n"
                            f"مبلغ: {amount}\n"
                            f"برنده: {winner_name}"
                        )

                        del pending_bets[chat_id]

                    elif data == "cancel":

                        if chat_id not in pending_bets:
                            continue

                        bet = pending_bets[chat_id]
                        creator = bet["creator"]

                        if user_id != creator["id"]:
                            send_message(chat_id, "❌ فقط سازنده می‌تونه لغو کنه")
                            continue

                        edit_message(
                            chat_id,
                            bet["message_id"],
                            "❌ شرط لغو شد"
                        )

                        del pending_bets[chat_id]

                # ---------- پیام متنی ----------
                elif "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    user = msg["from"]
                    user_id = user["id"]
                    text = msg.get("text", "")

                    add_user(user_id)

                    command = text.split()[0] if text else ""

                    if command.startswith("/start"):
                        show_menu(chat_id)

                    elif text.isdigit():
                        check_guess(chat_id, user_id, int(text))

                    elif text.startswith("شرطبندی"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1].isdigit():
                            create_bet(chat_id, user, int(parts[1]))

        time.sleep(1)

    except Exception as e:
        print("خطا:", e)
        time.sleep(5)
