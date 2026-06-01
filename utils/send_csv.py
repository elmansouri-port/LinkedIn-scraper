#utils\send_csv.py
import time
import pandas as pd
from datetime import datetime
from config.scraper_config import GROUP_URL, MESSAGE, GROUP_ID


def load_csv_file():
    """Load the CSV file with group members"""
    csv_path = f"data/csv/group_members_{GROUP_ID}.csv"
    try:
        df = pd.read_csv(csv_path)
        
        # Add status and time columns if they don't exist
        if 'status' not in df.columns:
            df['status'] = 'pending'
        if 'sent_time' not in df.columns:
            df['sent_time'] = ''
            
        return df
    except FileNotFoundError:
        print(f"CSV file not found: {csv_path}")
        return None

def save_csv_file(df):
    """Save the updated CSV file"""
    csv_path = f"data/csv/group_members_{GROUP_ID}.csv"
    df.to_csv(csv_path, index=False)
    print(f"CSV updated and saved to {csv_path}")
