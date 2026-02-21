import requests
import time
import random
from database import init_db, add_user, get_user, update_user

TOKEN = "8587480321:AAHQtL4tJASYVhcP-zuvui0rMMk8aBebE0g"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

init_db()

last_update_id = None
active_games = {}
attempts = {}
pending_bets = {}  # شرط‌های در انتظار

def send_message(chat_id, text):
    requests.post(
        f"{BASE_URL}/sendMessage",
        data={"chat_id": chat_id, "text": text}
    )

# ---------- بازی حدس عدد ----------

def start_game(chat_id, user_id):
    if user_id in active_games:
        send_message(chat_id, "شما داخل بازی هستید 🎮")
        return

    number = random.randint(1, 100)
    active_games[user_id] = number
    attempts[user_id] = 0
    send_message(chat_id, "🎲 یک عدد بین 1 تا 100 انتخاب کردم! حدس بزن.")

def calculate_reward(count):
    if count <= 5:
        return 50
    elif count <= 11:
        return 40
    elif count <= 35:
        return 20
    elif count <= 85:
        return 10
    else:
        return 1

def check_guess(chat_id, user_id, guess):
    if user_id not in active_games:
        return

    attempts[user_id] += 1
    number = active_games[user_id]
    tokens = get_user(user_id)[0]

    if guess == number:
        reward = calculate_reward(attempts[user_id])
        tokens += reward
        update_user(user_id, tokens)

        send_message(chat_id,
            f"🎉 درست حدس زدی!\n"
            f"💰 جایزه: {reward}\n"
            f"🏦 موجودی: {tokens}"
        )

        del active_games[user_id]
        del attempts[user_id]

    elif guess < number:
        send_message(chat_id, "🔼 بزرگ‌تره")
    else:
        send_message(chat_id, "🔽 کوچیک‌تره")

# ---------- موجودی ----------

def show_balance(chat_id, user_id):
    tokens = get_user(user_id)[0]
    send_message(chat_id, f"💰 موجودی شما: {tokens}")

# ---------- شرط دو نفره ----------

def create_bet(chat_id, user_id, amount, message_id):
    tokens = get_user(user_id)[0]

    if tokens < amount:
        send_message(chat_id, "❌ سکه کافی نداری!")
        return

    pending_bets[message_id] = {
        "creator": user_id,
        "amount": amount
    }

    send_message(chat_id,
        f"🎲 شرط {amount} سکه‌ای ایجاد شد!\n"
        f"روی این پیام ریپلای کن و بنویس: قبول"
    )

def accept_bet(chat_id, user_id, reply_message_id):
    if reply_message_id not in pending_bets:
        return

    bet = pending_bets[reply_message_id]
    creator = bet["creator"]
    amount = bet["amount"]

    if user_id == creator:
        send_message(chat_id, "❌ نمی‌تونی شرط خودتو قبول کنی!")
        return

    user_tokens = get_user(user_id)[0]
    creator_tokens = get_user(creator)[0]

    if user_tokens < amount:
        send_message(chat_id, "❌ سکه کافی نداری!")
        return

    if creator_tokens < amount:
        send_message(chat_id, "❌ سازنده شرط سکه کافی نداره!")
        return

    # کم کردن از هر دو
    update_user(user_id, user_tokens - amount)
    update_user(creator, creator_tokens - amount)

    winner = random.choice([user_id, creator])
    winner_tokens = get_user(winner)[0]
    update_user(winner, winner_tokens + (amount * 2))

    send_message(chat_id,
        f"🔥 شرط انجام شد!\n"
        f"💰 مبلغ: {amount}\n"
        f"🏆 برنده: {winner}"
    )

    del pending_bets[reply_message_id]

# ---------- دریافت آپدیت ----------

def get_updates():
    global last_update_id
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}

    if last_update_id:
        params["offset"] = last_update_id + 1

    return requests.get(url, params=params).json()

print("ربات روشن شد...")

while True:
    try:
        updates = get_updates()

        if updates.get("ok"):
            for update in updates.get("result", []):

                last_update_id = update["update_id"]

                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    message_id = msg["message_id"]

                    add_user(user_id)

                    if text.startswith("/play"):
                        start_game(chat_id, user_id)

                    elif text == "موجودی":
                        show_balance(chat_id, user_id)

                    elif text.startswith("شرط"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1].isdigit():
                            create_bet(chat_id, user_id, int(parts[1]), message_id)

                    elif text == "قبول" and "reply_to_message" in msg:
                        reply_id = msg["reply_to_message"]["message_id"]
                        accept_bet(chat_id, user_id, reply_id)

                    elif text.isdigit():
                        check_guess(chat_id, user_id, int(text))

        time.sleep(1)

    except Exception as e:
        print("خطا:", e)
        time.sleep(5)
