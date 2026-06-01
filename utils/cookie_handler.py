# utils/cookie_handler.py
import pickle
from pathlib import Path

# New organized path
COOKIES_FILE = Path(".auth") / "cookies.pkl"

def save_cookies(driver):
    try:
        cookies = driver.get_cookies()
        COOKIES_FILE.parent.mkdir(exist_ok=True)
        with open(COOKIES_FILE, "wb") as file:
            pickle.dump(cookies, file)
        print(f"✅ Cookies saved to {COOKIES_FILE}")
    except Exception as e:
        print(f"❌ Error saving cookies: {e}")

