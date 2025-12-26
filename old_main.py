# main.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from config.settings import GROUP_URL
from auth.login_with_cookies import login_with_cookies
from auth.login_with_credentials import login_with_credentials
from scraper.group_scraper import scrape_group_members
from utils.cookie_handler import save_cookies
import tempfile
from utils.group_data_saver import GroupDataSaver

def setup_chrome_driver():
    """Setup Chrome with memory-optimized configuration"""
    
    # Possible paths for chromedriver.exe
    driver_paths = [
        "./chromedriver.exe",
        "C:/chromedriver/chromedriver.exe",
        "C:/WebDrivers/chromedriver.exe",
        "./drivers/chromedriver.exe",
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
    
    # MEMORY-OPTIMIZED Chrome options
    options = webdriver.ChromeOptions()
    
    # Anti-detection options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # MEMORY MANAGEMENT OPTIONS
    options.add_argument("--memory-pressure-off")  # Disable memory pressure
    options.add_argument("--max_old_space_size=4096")  # Limit heap to 4GB
    options.add_argument("--aggressive-cache-discard")  # Aggressively discard cache
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Performance and stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # REDUCE MEMORY CONSUMPTION
    options.add_argument("--disable-extensions")  # Disable all extensions
    options.add_argument("--disable-plugins")  # Disable plugins
    options.add_argument("--disable-images")  # Don't load images to save memory
    options.add_argument("--disable-javascript-harmony-shipping")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")  # Disable Chrome sync
    options.add_argument("--disable-translate")  # Disable translate
    
    # CACHE AND STORAGE MANAGEMENT
    options.add_argument("--aggressive-tab-discard")  # Discard tabs aggressively
    options.add_argument("--purge-memory-button")  # Enable memory purge
    options.add_argument("--force-purge-on-memory-pressure")  # Force purge on memory pressure
    
    # Set memory limits
    options.add_argument("--memory-pressure-threshold-mb=2048")  # Set memory threshold
    options.add_argument("--tab-memory-pressure-threshold-mb=1024")
    
    # User agent for LinkedIn compatibility
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Optional: Keep user data but in temp directory to avoid accumulation
    temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
    options.add_argument(f"--user-data-dir={temp_profile}")
    
    # Optional: Run headless to save more memory (uncomment if needed)
    # options.add_argument("--headless")
    
    # Create service
    service = Service(driver_path)
    
    # Create driver
    driver = webdriver.Chrome(service=service, options=options)
    
    # Remove automation indicators
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    # Set timeouts to prevent hanging
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    print("🚀 Chrome driver setup with memory optimizations complete!")
    return driver

def monitor_and_restart_if_needed(driver, data_saver, scraped_count):
    """
    Monitor memory usage and restart browser if needed
    """
    try:
        # Check memory usage
        memory_info = driver.execute_script("""
            if (window.performance && window.performance.memory) {
                return {
                    used: Math.round(window.performance.memory.usedJSHeapSize / 1024 / 1024),
                    total: Math.round(window.performance.memory.totalJSHeapSize / 1024 / 1024),
                    limit: Math.round(window.performance.memory.jsHeapSizeLimit / 1024 / 1024)
                };
            }
            return null;
        """)
        
        if memory_info:
            used_mb = memory_info['used']
            print(f"🔍 Current memory usage: {used_mb}MB")
            
            # If memory usage is too high (>3GB), recommend restart
            if used_mb > 3000:
                print("⚠️ HIGH MEMORY USAGE DETECTED!")
                print(f"📊 Scraped so far: {scraped_count} members")
                print("💡 Consider stopping and restarting the script to continue from where you left off")
                
                user_input = input("Continue anyway? (y/n): ").strip().lower()
                if user_input != 'y':
                    return False
        
        return True
        
    except Exception as e:
        print(f"Could not check memory usage: {e}")
        return True

if __name__ == "__main__":
    driver = None
    temp_profile = None
    
    try:
        print("🔧 Setting up memory-optimized Chrome driver...")
        driver = setup_chrome_driver()
        print("✅ Chrome driver setup successful!")

        logged_in = False

        # Try to login using cookies
        try:
            login_with_cookies(driver)
            logged_in = True
            print("🔑 Logged in with cookies.")
        except Exception as e:
            print(f"⚠️ Login with cookies failed: {e}")

        # If cookie login failed, try credentials
        if not logged_in:
            try:
                login_with_credentials(driver)
                save_cookies(driver)
                logged_in = True
                print("🔑 Logged in with credentials and cookies saved.")
            except Exception as e:
                print(f"❌ Login with credentials failed: {e}")

        # Proceed only if login was successful
        if logged_in:
            print("🚀 Starting memory-optimized scraping...")
            
            # Add memory monitoring before scraping
            try:
                memory_info = driver.execute_script("""
                    if (window.performance && window.performance.memory) {
                        return Math.round(window.performance.memory.usedJSHeapSize / 1024 / 1024);
                    }
                    return 0;
                """)
                print(f"📊 Initial memory usage: {memory_info}MB")
            except:
                pass
            
            # Start scraping with memory management
            scrape_group_members(driver, GROUP_URL)
            
        else:
            print("❌ Login failed. Exiting...")

    except KeyboardInterrupt:
        print("\n⚠️ Script interrupted by user")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if driver:
            try:
                print("🧹 Cleaning up browser...")
                driver.quit()
                print("✅ Browser closed successfully")
            except:
                print("⚠️ Error closing browser")
        
        # Clean up temp profile directory
        if temp_profile and os.path.exists(temp_profile):
            try:
                import shutil
                shutil.rmtree(temp_profile, ignore_errors=True)
                print("🧹 Temp profile directory cleaned up")
            except:
                print("⚠️ Could not clean temp profile directory")
        
        print("🎯 Script execution completed")