# auth/login_with_cookies.py
import pickle
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def login_with_cookies(driver):
    try:
        if not os.path.exists("cookies.pkl"):
            print("No cookies file found. Please login with credentials first.")
            return False
            
        print("Loading cookies...")
        driver.get("https://www.linkedin.com")
        
        with open("cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Could not add cookie: {e}")
                
        driver.refresh()
        
        # Check if login was successful
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.any_of(
                EC.url_contains("/feed/"),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='nav-user-profile']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__primary-link-me-menu-trigger"))
            ))
            print("✅ Cookie login successful!")
            return True
        except:
            print("❌ Cookie login failed. Cookies may be expired.")
            return False
            
    except Exception as e:
        print(f"Cookie login error: {e}")
        return False