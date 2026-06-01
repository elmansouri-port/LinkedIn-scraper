import pandas as pd
import time
import random
import logging
from datetime import datetime
import os
from selenium.common.exceptions import WebDriverException
from .connection_sender import send_connection
from config.scraper_config import MESSAGE

# Setup logging
log_dir = 'data/logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'mass_connections.log')),
        logging.StreamHandler()
    ]
)

class MassConnectionSender:
    def __init__(self, driver, csv_file_path, note_message=None, use_note=True):
        self.driver = driver
        self.csv_file_path = csv_file_path
        self.note_message = note_message or MESSAGE
        self.use_note = use_note
        self.df = None
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        
    def load_csv(self):
        """Load CSV file and add tracking columns if they don't exist"""
        try:
            self.df = pd.read_csv(self.csv_file_path)
            logging.info(f"Loaded {len(self.df)} profiles from {self.csv_file_path}")
            
            # Add tracking columns if they don't exist
            if 'connection_status' not in self.df.columns:
                self.df['connection_status'] = 'pending'
            if 'connection_time' not in self.df.columns:
                self.df['connection_time'] = ''
            if 'connection_attempts' not in self.df.columns:
                self.df['connection_attempts'] = 0
                
            return True
        except Exception as e:
            logging.error(f"Failed to load CSV: {e}")
            return False
    
    def save_csv(self):
        """Save updated CSV with connection status"""
        try:
            self.df.to_csv(self.csv_file_path, index=False)
            logging.info("CSV file updated successfully")
        except Exception as e:
            logging.error(f"Failed to save CSV: {e}")
    
    def get_pending_profiles(self):
        """Get profiles that haven't been processed or failed"""
        return self.df[
            (self.df['connection_status'].isin(['pending', 'failed'])) &
            (self.df['connection_attempts'] < 3)  # Max 3 attempts
        ]
    
    def update_profile_status(self, index, status, error_message=None):
        """Update connection status for a profile"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.df.at[index, 'connection_status'] = status
        self.df.at[index, 'connection_time'] = current_time
        self.df.at[index, 'connection_attempts'] = self.df.at[index, 'connection_attempts'] + 1
        
        if error_message:
            if 'error_message' not in self.df.columns:
                self.df['error_message'] = ''
            self.df.at[index, 'error_message'] = error_message
    
    def random_delay(self, min_seconds=10, max_seconds=30):
        """Add random delay between connections to avoid detection"""
        delay = random.uniform(min_seconds, max_seconds)
        logging.info(f"Waiting {delay:.1f} seconds before next connection...")
        time.sleep(delay)
    
    def send_mass_connections(self, max_connections=None, delay_range=(10, 30)):
        """Send connection requests to multiple profiles"""
        if not self.load_csv():
            return False
        
        pending_profiles = self.get_pending_profiles()
        
        if len(pending_profiles) == 0:
            logging.info("No pending profiles to process")
            return True
        
        # Limit connections if specified
        if max_connections:
            pending_profiles = pending_profiles.head(max_connections)
        
        logging.info(f"Starting to send {len(pending_profiles)} connection requests")
        
        for idx, row in pending_profiles.iterrows():
            try:
                profile_url = row.get('profile_url', '')
                profile_name = row.get('name', 'Unknown')
                
                if not profile_url:
                    logging.warning(f"No profile URL for {profile_name}, skipping")
                    self.update_profile_status(idx, 'skipped', 'No profile URL')
                    self.skipped_count += 1
                    continue
                
                logging.info(f"Sending connection to: {profile_name}")
                logging.info(f"Profile URL: {profile_url}")
                
                # Send connection request
                send_connection(self.driver, profile_url, self.note_message, self.use_note)
                
                # Update status as successful
                self.update_profile_status(idx, 'sent')
                self.success_count += 1
                logging.info(f"✅ Connection sent successfully to {profile_name}")
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"❌ Failed to send connection to {profile_name}: {error_msg}")
                self.update_profile_status(idx, 'failed', error_msg)
                self.failed_count += 1
            
            finally:
                self.processed_count += 1
                
                # Save progress after each attempt
                self.save_csv()
                
                # Add delay between connections (except for the last one)
                if self.processed_count < len(pending_profiles):
                    self.random_delay(delay_range[0], delay_range[1])
        
        # Final summary
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print summary of the mass connection process"""
        logging.info("=" * 50)
        logging.info("MASS CONNECTION SUMMARY")
        logging.info("=" * 50)
        logging.info(f"Total processed: {self.processed_count}")
        logging.info(f"Successful: {self.success_count}")
        logging.info(f"Failed: {self.failed_count}")
        logging.info(f"Skipped: {self.skipped_count}")
        logging.info("=" * 50)
    
    def get_statistics(self):
        """Get current statistics from CSV"""
        if self.df is None:
            self.load_csv()
        
        stats = {
            'total_profiles': len(self.df),
            'sent': len(self.df[self.df['connection_status'] == 'sent']),
            'pending': len(self.df[self.df['connection_status'] == 'pending']),
            'failed': len(self.df[self.df['connection_status'] == 'failed']),
            'skipped': len(self.df[self.df['connection_status'] == 'skipped'])
        }
        
        return stats


def run_mass_connections(driver, csv_file_path='data/csv/group_members_1912468.csv', 
                        note_message=None, use_note=True, max_connections=20):
    """
    Main function to run mass connections
    
    Args:
        driver: Selenium WebDriver instance
        csv_file_path: Path to CSV file with profiles
        note_message: Custom message for connection requests
        use_note: Whether to send note with connection requests
        max_connections: Maximum number of connections to send in this run
    """
    
    # Create mass sender instance
    mass_sender = MassConnectionSender(driver, csv_file_path, note_message, use_note)
    
    # Show current statistics
    stats = mass_sender.get_statistics()
    logging.info("Current CSV Statistics:")
    for key, value in stats.items():
        logging.info(f"  {key}: {value}")
    
    # Start sending connections
    success = mass_sender.send_mass_connections(
        max_connections=max_connections,
        delay_range=(15, 35)  # 15-35 seconds delay between connections
    )
    
    return success


if __name__ == "__main__":
    # This would be used for testing
    print("Mass Connection Sender - Use run_mass_connections() function")