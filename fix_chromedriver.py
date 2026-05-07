"""
Quick fix: Download ChromeDriver manually and place it in PATH
Run: python fix_chromedriver.py
"""
import os
import sys
import ssl
import urllib.request

# Disable SSL verification (temporary fix for corporate firewalls)
ssl._create_default_https_context = ssl._create_unverified_context

# Get Chrome version
import subprocess
try:
    result = subprocess.run(
        r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --version',
        shell=True, capture_output=True, text=True
    )
    chrome_version = result.stdout.strip().split()[-1]
    major_version = chrome_version.split('.')[0]
    print(f"Chrome version: {chrome_version}")
except Exception as e:
    print(f"Could not detect Chrome version: {e}")
    major_version = "148"

# Download URL for ChromeDriver
# For Chrome 115+, use Chrome for Testing
url = f"https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"

print("Fetching ChromeDriver download info...")
try:
    with urllib.request.urlopen(url, timeout=10) as response:
        data = response.read()
        import json
        versions = json.loads(data)
        
        # Find matching version
        for version_info in versions.get("versions", []):
            if version_info.get("version", "").startswith(major_version + "."):
                downloads = version_info.get("downloads", {}).get("chromedriver", [])
                for d in downloads:
                    if d.get("platform") == "win64":
                        download_url = d["url"]
                        print(f"Found download: {download_url}")
                        
                        # Download
                        print("Downloading ChromeDriver...")
                        zip_path = "chromedriver-win64.zip"
                        urllib.request.urlretrieve(download_url, zip_path)
                        print(f"Downloaded to {zip_path}")
                        
                        # Extract
                        import zipfile
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            for name in zip_ref.namelist():
                                if name.endswith('chromedriver.exe'):
                                    zip_ref.extract(name, '.')
                                    print(f"Extracted: {name}")
                        
                        # Move to PATH location
                        dest = "C:\\Users\\yelmanso\\vs project\\leadgen\\LinkedIn-scraper\\chromedriver.exe"
                        os.rename(name, dest)
                        print("ChromeDriver installed: " + dest)
                        sys.exit(0)
                        
except Exception as e:
    print(f"Error: {e}")
    print("\nManual fix: Download ChromeDriver from:")
    print(f"https://googlechromelabs.github.io/chrome-for-testing/#stable")
    print(f"Place chromedriver.exe in: C:\Users\yelmanso\vs project\leadgen\LinkedIn-scraper\")
