from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time


def setup_chrome_driver():
    """Setup Chrome with manual ChromeDriver"""
    
    # Possible paths for chromedriver.exe (adjust as needed)
    driver_paths = [
        "./chromedriver.exe",  # In your project folder
        "C:/chromedriver/chromedriver.exe",  # Common location
        "C:/WebDrivers/chromedriver.exe",  # Another common location
        "./drivers/chromedriver.exe",  # In a drivers subfolder
    ]
    
    driver_path = None
    for path in driver_paths:
        if os.path.exists(path):
            driver_path = path
            print(f"Found ChromeDriver at: {path}")
            break
    
    if not driver_path:
        print("ChromeDriver not found! Please download and place it in one of these locations:")
        for path in driver_paths:
            print(f"  - {path}")
        raise Exception("ChromeDriver executable not found")
    
    # Chrome options for LinkedIn scraping
    options = webdriver.ChromeOptions()
    
    # Anti-detection options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Performance and stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # User agent to appear more human-like
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Optional: Keep user data (uncomment if you want persistent sessions)
    # options.add_argument("--user-data-dir=./chrome_profile")
    
    # Optional: Run headless (uncomment to run without GUI)
    # options.add_argument("--headless")
    
    # Create service with ChromeDriver path
    service = Service(driver_path)
    
    # Create driver
    driver = webdriver.Chrome(service=service, options=options)
    
    # Remove automation indicators
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return driver

driver = setup_chrome_driver()

driver.get("https://infiniteajaxscroll.com/examples/blocks/")



# time.sleep(2)

# email = driver.find_element(By.CLASS_NAME, "login__input")
# email.send_keys("youssef@mail.com")

# time.sleep(2)

# btn = driver.find_element(By.CLASS_NAME, "button")
# btn.click()


# Scroll to the bottom of the page
time.sleep(2)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

# watch if an element is on the page
try:
    elem = driver.find_element("css selector", "div.test")
    print(elem.is_displayed())
except:
    print("doesn't exist")



time.sleep(10)