"""
LinkedIn Scraper CLI - New version using service layer
This provides the same interface as main.py but uses the core services
"""
from core.driver_manager import DriverManager
from core.services import ScraperService, ConnectionService, MessagingService
from config.settings import GROUP_URL
from scraper.group_scraper import get_scraping_mode
import time
import sys


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


def main():
    # Ensure data directories exist
    import os
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/csv", exist_ok=True)

    driver = None
    temp_profile = None
    try:
        # Ask the user what they want to do
        action = get_user_action()

        print("🔧 Setting up Chrome driver...")
        driver, temp_profile = DriverManager.setup_chrome_driver()
        print("✅ Chrome driver setup successful!")

        # Use AuthManager for authentication
        from auth.auth_manager import AuthManager
        from config import settings
        
        print("🔑 Attempting to login...")
        auth_manager = AuthManager(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)
        logged_in = auth_manager.login(driver)
        
        if not logged_in:
            print("❌ Login failed. Exiting...")
            return

        # Proceed with actions
        if action == "1":
            # Scrape data from a group
            max_members = get_max_members_input()
            scraping_mode = get_scraping_mode()
            print(f"🚀 Starting scraping in {scraping_mode} mode...")
            
            result = ScraperService.scrape_group_members(
                driver, GROUP_URL, max_members, scraping_mode
            )
            
            if result['success']:
                print(f"🎉 {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        elif action == "2":
            # Send messages to group members
            print("🚀 Starting messaging campaign...")
            result = MessagingService.send_group_messages(driver)
            
            if result['success']:
                print(f"🎉 {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        elif action == "3":
            # Scrape profiles from search
            keywords = input("What keywords you want to search: ")
            profnum = input("Enter the desired number of profiles: ")
            start_page = input("Start from (press Enter for 1): ").strip()
            start_page = int(start_page) if start_page else 1
            
            print("🚀 Starting profile search...")
            result = ScraperService.search_and_scrape_profiles(
                driver, keywords, int(profnum), start_page
            )
            
            if result['success']:
                print(f"🎉 {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        elif action == "4":
            # Send single connection
            print("🚀 Starting connection sender...")
            profile_url = input("Enter the profile url: ")
            note_message = input("Enter the note (or press Enter for none): ").strip()
            note_message = note_message if note_message else None
            
            result = ConnectionService.send_single_connection(
                driver, profile_url, note_message
            )
            
            if result['success']:
                print(f"🎉 {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        elif action == "5":
            # Send mass connections
            print("🚀 Starting connection campaign...")
            csv_file_path = input("Enter the csv file path: ")
            note_message = input("Enter the note (or press Enter for none): ").strip()
            
            use_note = bool(note_message)
            
            result = ConnectionService.send_mass_connections(
                driver, csv_file_path, note_message, use_note
            )
            
            if result['success']:
                print(f"🎉 {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        elif action == "6":
            # Scrape profiles from Google search
            print("🚀 Starting Google LinkedIn profiles Scraper...")
            keywords = input("Enter the keywords (separated with spaces): ")
            oblig_keywords = input("Enter the obligatory keywords (separated with spaces): ")
            max_profiles = input("Enter the number of profiles to scrape: ")
            max_profiles_per_keyword = input("Enter the number of profiles to scrape per keyword: ")
            
            result = ScraperService.scrape_google_linkedin_profiles(
                driver, keywords, oblig_keywords, 
                int(max_profiles), int(max_profiles_per_keyword)
            )
            
            if result['success']:
                print(f"🎉 {result['message']}")
            else:
                print(f"❌ {result['message']}")

    except KeyboardInterrupt:
        print("\n⚠️ Script interrupted by user")
        print("💾 Your progress has been saved and you can resume later!")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if driver:
            DriverManager.cleanup_driver(driver, temp_profile)


if __name__ == "__main__":
    main()
