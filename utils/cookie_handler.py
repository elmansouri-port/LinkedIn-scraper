# utils/cookie_handler.py
import pickle

def save_cookies(driver):
    try:
        cookies = driver.get_cookies()
        with open("cookies.pkl", "wb") as file:
            pickle.dump(cookies, file)
        print("✅ Cookies saved successfully!")
    except Exception as e:
        print(f"❌ Error saving cookies: {e}")

