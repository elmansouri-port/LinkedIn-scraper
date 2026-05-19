# old_main.py
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
from utils.group_data_saver import GroupDataSaver
from core.driver_manager import DriverManager

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
        print("🔧 Setting up Chrome driver...")
        driver, temp_profile = DriverManager.setup_chrome_driver()
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
        
        # Profile directory is persistent — kept for future sessions
        
        print("🎯 Script execution completed")