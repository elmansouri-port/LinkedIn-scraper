#!/usr/bin/env bash
set -e

echo "=============================================================="
echo " LinkedIn Scraper Installer (Mac/Linux)"
echo "=============================================================="
echo ""

# Check for git
if ! command -v git &> /dev/null; then
    echo "[!] Git is not installed."
    echo "[*] Attempting to install Git..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y git
    elif command -v brew &> /dev/null; then
        brew install git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    else
        echo "[ERROR] Could not install Git automatically."
        echo "Please install Git manually and run this script again."
        exit 1
    fi
    echo "[OK] Git installed successfully."
fi

echo "[*] Cloning repository..."
git clone -b master https://github.com/elmansouri-port/LinkedIn-scraper.git

cd LinkedIn-scraper
echo "[OK] Repository downloaded."
echo ""
echo "[*] Starting LinkedIn Scraper setup..."
chmod +x start.sh
./start.sh
