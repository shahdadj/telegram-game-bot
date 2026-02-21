import requests
import time
import random
from database import init_db, add_user, get_user, update_user

TOKEN = "8587480321:AAHQtL4tJASYVhcP-zuvui0rMMk8aBebE0g"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

init_db()

last_update_id = None

def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": text})

def start_game(chat_id, user_id):
    number = random.randint(1, 100)
    update_user(chat_id, user_id, current_game="number_guess", game_state=str(number))
    send_message(chat_id, "🎲 یک عدد بین 1 تا 100 انتخاب کردم! حدس بزن.")

def check_guess(chat_id, user_id, guess):
    user = get_user(chat_id, user_id)
    if not user or user[5] != "number_guess":
        send_message(chat_id, "شما بازی فعالی ندارید. برای شروع /play بزنید.")
        return

    number = int(user[6])
    token = user[4]

    if guess == number:
        token += 10
        update_user(chat_id, user_id, token=token, current_game=None, game_state=None)
        send_message(chat_id, f"🎉 درست حدس زدی! توکنت: {token}")
    elif guess < number:
        send_message(chat_id, "🔼 عدد بزرگ‌تره!")
    else:
        send_message(chat_id, "🔽 عدد کوچیک‌تره!")

def get_updates():
    global last_update_id
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}
    if last_update_id:
        params["offset"] = last_update_id + 1
    return requests.get(url, params=params).json()

print("ربات روشن شد...")

while True:
    updates = get_updates()
    if updates["ok"]:
        for update in updates["result"]:
            last_update_id = update["update_id"]

            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                user_id = update["message"]["from"]["id"]
                username = update["message"]["from"].get("username", "")
                text = update["message"].get("text", "")

                add_user(chat_id, user_id, username)

                if text.startswith("/start"):
                    send_message(chat_id, "سلام! ربات بازی توکنی خوش اومدی!")

                elif text.startswith("/play"):
                    start_game(chat_id, user_id)

                elif text.isdigit():
                    check_guess(chat_id, user_id, int(text))

                else:
                    send_message(chat_id, "برای شروع بازی /play بزنید.")

    time.sleep(1)
