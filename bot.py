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

# ---------------- ارسال پیام ----------------

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)

    requests.post(f"{BASE_URL}/sendMessage", data=data)

# ---------------- منوی اصلی ----------------

def show_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎲 حدس عدد", "callback_data": "number_game"}],
            [{"text": "🔥 شرط‌بندی", "callback_data": "bet_game"}],
            [{"text": "💰 موجودی", "callback_data": "balance"}]
        ]
    }

    send_message(chat_id, "🎮 یک بازی انتخاب کن:", keyboard)

# ---------------- بازی حدس عدد ----------------

def start_game(chat_id, user_id):
    number = random.randint(1, 100)
    active_games[user_id] = number
    attempts[user_id] = 0
    send_message(chat_id, "🎲 یک عدد بین 1 تا 100 انتخاب کردم! حدس بزن.")

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

        tokens += reward
        update_user(user_id, tokens)

        send_message(chat_id,
            f"🎉 درست حدس زدی!\n"
            f"🔢 تعداد تلاش: {tries}\n"
            f"💰 جایزه: {reward}\n"
            f"🏦 موجودی جدید: {tokens}"
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
    send_message(chat_id, f"💰 موجودی شما: {tokens} سکه")

# ---------------- ساخت شرط ----------------

def create_bet(chat_id, user_id, amount):
    tokens = get_user(user_id)[0]

    if tokens < amount:
        send_message(chat_id, "❌ سکه کافی نداری!")
        return

    pending_bets[chat_id] = {
        "creator": user_id,
        "amount": amount
    }

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ قبول", "callback_data": "accept_bet"},
                {"text": "❌ لغو", "callback_data": "cancel_bet"}
            ]
        ]
    }

    send_message(
        chat_id,
        f"🎲 شرط {amount} سکه‌ای ایجاد شد!\n"
        f"سازنده شرط: {user_id}",
        keyboard
    )

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
            for update in updates.get("result", []):

                last_update_id = update["update_id"]

                # ---------------- دکمه‌ها ----------------
                if "callback_query" in update:
                    query = update["callback_query"]
                    chat_id = query["message"]["chat"]["id"]
                    user_id = query["from"]["id"]
                    data = query["data"]

                    add_user(user_id)

                    if data == "number_game":
                        start_game(chat_id, user_id)

                    elif data == "bet_game":
                        send_message(chat_id, "برای ساخت شرط بنویس:\nشرط 50")

                    elif data == "balance":
                        show_balance(chat_id, user_id)

                    elif data == "accept_bet":
                        if chat_id not in pending_bets:
                            send_message(chat_id, "❌ شرطی وجود ندارد.")
                            continue

                        bet = pending_bets[chat_id]
                        creator = bet["creator"]
                        amount = bet["amount"]

                        if user_id == creator:
                            send_message(chat_id, "❌ نمی‌تونی شرط خودتو قبول کنی!")
                            continue

                        creator_tokens = get_user(creator)[0]
                        user_tokens = get_user(user_id)[0]

                        if creator_tokens < amount or user_tokens < amount:
                            send_message(chat_id, "❌ یکی از طرفین سکه کافی نداره!")
                            continue

                        update_user(creator, creator_tokens - amount)
                        update_user(user_id, user_tokens - amount)

                        winner = random.choice([creator, user_id])
                        winner_tokens = get_user(winner)[0]
                        update_user(winner, winner_tokens + amount * 2)

                        send_message(chat_id,
                            f"🔥 شرط انجام شد!\n"
                            f"💰 مبلغ: {amount}\n"
                            f"🏆 برنده: {winner}"
                        )

                        del pending_bets[chat_id]

                    elif data == "cancel_bet":
                        if chat_id not in pending_bets:
                            send_message(chat_id, "❌ شرطی وجود ندارد.")
                            continue

                        bet = pending_bets[chat_id]
                        creator = bet["creator"]

                        if user_id != creator:
                            send_message(chat_id, "❌ فقط سازنده می‌تونه لغو کنه!")
                            continue

                        send_message(chat_id, "❌ شرط لغو شد.")
                        del pending_bets[chat_id]

                # ---------------- پیام متنی ----------------
                elif "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")

                    add_user(user_id)

                    if text == "/start":
                        show_menu(chat_id)

                    elif text.isdigit():
                        check_guess(chat_id, user_id, int(text))

                    elif text.startswith("شرط"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1].isdigit():
                            create_bet(chat_id, user_id, int(parts[1]))

        time.sleep(1)

    except Exception as e:
        print("خطا:", e)
        time.sleep(5)
