# utils/group_data_saver.py
import csv
import os
import sqlite3
from datetime import datetime
from config.scraper_config import GROUP_ID


class GroupDataSaver:
    def __init__(self, filename=None, db_name=None):
        # Ensure the data directory exists
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.data_dir = os.path.abspath(self.data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Create subdirectories for CSV and DB
        csv_dir = os.path.join(self.data_dir, 'csv')
        db_dir = os.path.join(self.data_dir, 'db')
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(db_dir, exist_ok=True)
        
        # Generate filename with timestamp if not provided
        if filename is None:
            filename = f"csv/group_members_{GROUP_ID}.csv"
        self.filename = os.path.join(self.data_dir, filename)
        self.file_exists = os.path.exists(self.filename)

        # Setup database
        if db_name is None:
            db_name = f"db/group_members_{GROUP_ID}.db"
        self.db_path = os.path.join(self.data_dir, db_name)
        
        self._setup_database()
        
        # Create CSV with headers if it doesn't exist
        if not self.file_exists:
            self._create_csv_with_headers()
    
    def _setup_database(self):
        """Create database and table if they don't exist"""
        try:
            # Ensure the directory exists
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"Created database directory: {db_dir}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table with unique constraint on profile_link
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_link TEXT UNIQUE NOT NULL,
                    name TEXT,
                    headline TEXT,
                    profile_img_link TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()

        except Exception as e:
            raise RuntimeError(f"Database setup failed at {self.db_path}: {e}") from e
    
    def _create_csv_with_headers(self):
        """Create CSV file with headers"""
        try:
            # Ensure CSV directory exists
            csv_dir = os.path.dirname(self.filename)
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir, exist_ok=True)
                
            with open(self.filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Name', 'Profile Link', 'Headline', 'Profile_img_link'])
        except Exception as e:
            print(f"CSV creation error: {e}")
            raise
    
    def _is_duplicate(self, profile_link):
        """Check if profile_link already exists in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO group_members (profile_link, name, headline, profile_img_link) VALUES (?, ?, ?, ?)', 
                         (profile_link, None, None, None))
            conn.commit()
            # If we get here, it's not a duplicate - remove the placeholder record
            cursor.execute('DELETE FROM group_members WHERE profile_link = ? AND name IS NULL', (profile_link,))
            conn.commit()
            conn.close()
            return False
        except sqlite3.IntegrityError:
            # Duplicate found
            conn.close()
            return True
    
    def save_data(self, name, profile_link, headline, profile_img_link):
        """Save member data to CSV file only if not duplicate in database"""
        try:
            # Try to insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO group_members (profile_link, name, headline, profile_img_link) 
                VALUES (?, ?, ?, ?)
            ''', (profile_link, name, headline, profile_img_link))
            
            conn.commit()
            conn.close()
            
            # If database insert successful, save to CSV
            with open(self.filename, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([name, profile_link, headline, profile_img_link])
            
            print(f"✓ Saved new member: {name}")
            return True
            
        except sqlite3.IntegrityError:
            # Duplicate profile link found
            print(f"⚠ Duplicate member skipped: {name} (Profile already exists)")
            return False
        except Exception as e:
            print(f"✗ Error saving member {name}: {str(e)}")
            return False
    
    def get_total_members(self):
        """Get total count of unique members in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM group_members')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_all_members(self):
        """Get all members from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name, profile_link, headline, profile_img_link, created_at FROM group_members ORDER BY created_at')
        members = cursor.fetchall()
        conn.close()
        return members