# main.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from config.settings import GROUP_URL
from auth.login_with_cookies import login_with_cookies
from auth.login_with_credentials import login_with_credentials
from scraper.group_scraper import scraper, get_scraping_mode
from utils.cookie_handler import save_cookies
from actions.group_outreach import message_all_group_members
from actions.search_profiles import search_connections
from actions.connection_sender import send_connection
from actions.mass_connections_sender import run_mass_connections
from scraper.google_search_profile_scraper import GoogleLinkedInProfileScraper
from core.driver_manager import DriverManager

def get_max_members_input():
    """Get user input for maximum number of members to scrape"""
    while True:
        max_input = input("\n📊 Enter maximum number of members to scrape (press Enter for unlimited): ").strip()
        
        if not max_input:
            print("📈 Will scrape unlimited members")
            return None
        
        try:
            max_members = int(max_input)
            if max_members <= 0:
                print("⚠️ Please enter a positive number")
                continue
            print(f"📈 Will scrape maximum {max_members} members")
            return max_members
        except ValueError:
            print("⚠️ Please enter a valid number")
            continue

def get_user_action():
    """Prompt the user to choose an action."""
    while True:
        print("\nWhat would you like to do?")
        print("1. Scrape LinkedIn group members")
        print("2. Send messages to group members")
        print("3. Scrape profiles from LinkedIn search")
        print("4. Send a single connection request")
        print("5. Send mass connection requests from CSV")
        print("6. Scrape LinkedIn profiles using Google search")

        choice = input("Enter your choice (1 - 6): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6"]:
            return choice
        
        print("Invalid choice. Please enter a number between 1 and 6.")

def get_search_parameters():
    """Get search parameters from user for LinkedIn search connections"""
    print("\n🔍 LinkedIn Search Connection Parameters:")
    
    keywords = input("Enter search keywords (e.g., 'technical recruiter'): ").strip()
    if not keywords:
        keywords = "technical recruiter"  # Default
    
    location = input("Enter location (press Enter for default): ").strip()
    
    # Get maximum connections
    while True:
        max_input = input("Enter maximum connection requests (default 20): ").strip()
        if not max_input:
            max_connections = 20
            break
        try:
            max_connections = int(max_input)
            if max_connections <= 0:
                print("⚠️ Please enter a positive number")
                continue
            break
        except ValueError:
            print("⚠️ Please enter a valid number")
            continue
    
    # Get starting page
    while True:
        page_input = input("Enter starting page number (default 1): ").strip()
        if not page_input:
            start_page = 1
            break
        try:
            start_page = int(page_input)
            if start_page <= 0:
                print("⚠️ Please enter a positive number")
                continue
            break
        except ValueError:
            print("⚠️ Please enter a valid number")
            continue
    
    return {
        'keywords': keywords,
        'location': location,
        'max_connections': max_connections,
        'start_page': start_page
    }


if __name__ == "__main__":
    driver = None
    temp_profile = None
    try:
        # Ask the user what they want to do
        action = get_user_action()

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
            if action == "1":
                # Scrape data from a group
                max_members = get_max_members_input()
                scraping_mode = get_scraping_mode()
                print(f"🚀 Starting enhanced search-based scraping in {scraping_mode} mode...")
                total_scraped = scraper(driver, GROUP_URL, max_members, scraping_mode)
                print(f"🎉 scraping completed! Total unique members: {total_scraped}")
            elif action == "2":
                # Send messages to group members
                print("🚀 Starting messaging campaign...")
                message_all_group_members(driver)
            elif action == "3":
                # scrap profiles from search
                profnum = input("Enter the desired number of profiles: ")
                keywords = input("What kaywords you want to search: ")
                start_page = input("Start from :")
                if start_page == None:
                    start_page = 1
                print("🚀 Starting connection search...")
                search_connections(driver, keywords, int(profnum), start_page)
            elif action == "4":
                # Send single connections
                print("🚀 Starting connection sender...")
                profile_url = input("Enter the profile url: ")
                note_message = input("Enter the note: ")
                send_connection(driver, profile_url, note_message)
            elif action == "5":
                # Send mass connections
                print("🚀 Starting connection campaign...")
                note_message = input("Enter the note: ")
                csv_file_path = input("Enter the csv file path: ")

                if note_message :
                    use_note = True
                else:
                    use_note = False

                run_mass_connections(driver, csv_file_path, note_message, use_note )
            elif action == "6":
                # Scrape profiles from google search
                print("🚀 Starting Google linkedin profiles Scraper...")
                keywords = input("Enter the keywords (seperated with spaces): ")
                oblig_keywords = input("Enter the obligator keywords (seperated with spaces): ")
                max_profiles = input("Enter the number or profiles to scrape: ")
                max_profiles_per_key_word = input("Enter the number or profiles to scrape per keyword: ")
                GoogleLinkedInProfileScraper.scrape_google_linkedin_profiles(driver, keywords, oblig_keywords, int(max_profiles), int(max_profiles_per_key_word))
        else:
            print("❌ Login failed. Exiting...")

    except KeyboardInterrupt:
        print("\n⚠️ Script interrupted by user")
        print("💾 Your progress has been saved and you can resume later!")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        DriverManager.cleanup_driver(driver)