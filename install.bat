@echo off
setlocal enabledelayedexpansion

echo ==============================================================
echo  LinkedIn Scraper Installer (Windows)
echo ==============================================================
echo.

:: Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Git is not installed.
    echo [*] Attempting to install Git via winget...
    winget install --id Git.Git -e --source winget
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Git automatically.
        echo Please download and install Git from https://git-scm.com/download/win
        pause
        exit /b 1
    )
    echo [OK] Git installed successfully.
    :: Refresh environment variables for current session to use git
    for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set syspath=%%B
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set userpath=%%B
    set PATH=!syspath!;!userpath!;%PATH%
)

echo [*] Cloning repository...
git clone -b master https://github.com/elmansouri-port/LinkedIn-scraper.git
if %errorlevel% neq 0 (
    echo [ERROR] Failed to clone the repository.
    pause
    exit /b 1
)

cd LinkedIn-scraper
echo [OK] Repository downloaded.
echo.
echo [*] Starting LinkedIn Scraper setup...
call "LinkedIn Scraper.bat"
