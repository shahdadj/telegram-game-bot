import requests
import time
import random
from database import init_db, add_user, get_user, update_user

TOKEN = "8587480321:AAHQtL4tJASYVhcP-zuvui0rMMk8aBebE0g"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

init_db()

last_update_id = None
active_games = {}

def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": text})

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
                text = update["message"].get("text", "")

                add_user(user_id)

               if text.startswith("/start"):
                    send_message(chat_id, "سلام! 🎮 به بازی حدس عدد خوش اومدی!")

               elif text.startswith("/play"):
                    number = random.randint(1, 100)
                    active_games[user_id] = number
                    send_message(chat_id, "🎲 یه عدد بین 1 تا 100 انتخاب کردم! حدس بزن.")

                elif text.isdigit():
                    guess = int(text)

                    if user_id not in active_games:
                        send_message(chat_id, "اول /play بزن 😊")
                        continue

                    number = active_games[user_id]

                    if guess == number:
                        user = get_user(user_id)
                        tokens = user[0] + 10
                        update_user(user_id, tokens)
                        send_message(chat_id, f"🎉 درست حدس زدی! توکن جدیدت: {tokens}")
                        del active_games[user_id]

                    elif guess < number:
                        send_message(chat_id, "🔼 عدد بزرگ‌تره!")

                    else:
                        send_message(chat_id, "🔽 عدد کوچیک‌تره!")

                else:
                    send_message(chat_id, "برای شروع بازی /play بزن 🎮")

    time.sleep(1)