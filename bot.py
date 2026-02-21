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
    requests.post(
        f"{BASE_URL}/sendMessage",
        data={"chat_id": chat_id, "text": text}
    )

def start_game(chat_id, user_id):
    # اگر بازی فعال داشت دوباره نسازه
    if user_id in active_games:
        send_message(chat_id, "شما در حال حاضر داخل بازی هستید 🎮 عددتو حدس بزن!")
        return

    number = random.randint(1, 100)
    active_games[user_id] = number
    send_message(chat_id, "🎲 یک عدد بین 1 تا 100 انتخاب کردم! حدس بزن.")

def check_guess(chat_id, user_id, guess):
    if user_id not in active_games:
        send_message(chat_id, "شما بازی فعالی ندارید. برای شروع /play بزنید.")
        return

    number = active_games[user_id]
    user = get_user(user_id)

    if not user:
        send_message(chat_id, "خطا در دریافت اطلاعات کاربر.")
        return

    tokens = user[0]

    if guess == number:
        tokens += 10
        update_user(user_id, tokens)
        del active_games[user_id]
        send_message(chat_id, f"🎉 درست حدس زدی! توکنت: {tokens}")
    elif guess < number:
        send_message(chat_id, "🔼 عدد بزرگ‌تره!")
    else:
        send_message(chat_id, "🔽 عدد کوچیک‌تره!")

def get_updates():
    global last_update_id

    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}

    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    response = requests.get(url, params=params).json()
    return response


print("ربات روشن شد...")

while True:
    try:
        updates = get_updates()

        if updates.get("ok"):
            for update in updates.get("result", []):

                update_id = update["update_id"]

                # جلوگیری از پردازش دوباره آپدیت
                if last_update_id is None or update_id > last_update_id:
                    last_update_id = update_id
                else:
                    continue

                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    user_id = update["message"]["from"]["id"]
                    text = update["message"].get("text", "")

                    add_user(user_id)

                    if text.startswith("/start"):
                        send_message(chat_id, "سلام! خوش اومدی 🎮")

                    elif text.startswith("/play"):
                        start_game(chat_id, user_id)

                    elif text.isdigit():
                        check_guess(chat_id, user_id, int(text))

                    else:
                        send_message(chat_id, "برای شروع بازی /play بزنید.")

        time.sleep(1)

    except Exception as e:
        print("خطا:", e)
        time.sleep(5)
