# auth/login_with_credentials.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.scraper_config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
import pickle

def login_with_credentials(driver):
    try:
        print("Navigating to LinkedIn login...")
        driver.get("https://www.linkedin.com/login")
        
        # Wait for elements to be present and clickable
        wait = WebDriverWait(driver, 15)
        
        print("Waiting for login form...")
        email_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
        password_input = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        
        print("Filling in credentials...")
        email_input.clear()
        email_input.send_keys(LINKEDIN_EMAIL)
        
        password_input.clear()
        password_input.send_keys(LINKEDIN_PASSWORD)
        
        # Add small delay to appear more human-like
        time.sleep(1)
        
        # Find and click the login button
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
        
        print("Login submitted. Waiting for response...")
        
        # Wait for successful login or verification prompt
        try:
            # Check for successful login (LinkedIn feed or profile page)
            wait.until(EC.any_of(
                EC.url_contains("/feed/"),
                EC.url_contains("/in/"),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='nav-user-profile']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__primary-link-me-menu-trigger"))
            ))
            print("✅ Login completed successfully!")
            
            # Save cookies to file
            from pathlib import Path
            cookies_file = Path(".auth") / "cookies.pkl"
            cookies_file.parent.mkdir(exist_ok=True)
            with open(cookies_file, "wb") as file:
                pickle.dump(driver.get_cookies(), file)
            print(f"✅ Cookies saved to {cookies_file}")
            
        except Exception:
            # Check if there's a verification challenge
            current_url = driver.current_url
            if "challenge" in current_url or "checkpoint" in current_url:
                print("🔐 LinkedIn is asking for verification. Please complete it manually in the browser.")
                input("Press Enter after completing the verification...")
            else:
                print("⚠️  Login status unclear. Please check the browser window.")
                print(f"Current URL: {current_url}")
                input("Press Enter to continue if login looks successful...")
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print(f"Current URL: {driver.current_url}")
        raise
