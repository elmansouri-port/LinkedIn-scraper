# LinkedIn Scraper - Full Project Structure & Code Flow

This document provides a comprehensive overview of the project's architecture, component roles, and the flow of logic during execution.

---

## 📂 1. Directory Structure Overview

| Directory | Description |
| :--- | :--- |
| `core/` | **The Foundation.** Contains the `DriverManager` and a centralized `services/` layer that acts as the business logic engine. |
| `auth/` | **Authentication.** Manages login logic (cookies vs. credentials) via the `AuthManager` class. |
| `actions/` | **Atomic Actions.** Reusable Selenium-based tasks (e.g., `send_connection`, `search_profiles`). |
| `scraper/` | **Specialized Scrapers.** Complex, multi-step scraping logic (e.g., `group_scraper`, `google_search_profile_scraper`). |
| `api/` | **Web Interface.** FastAPI implementation including routes, dependencies, and models. |
| `config/` | **Settings.** Centralized configuration management using environment variables (`.env`). |
| `utils/` | **Helpers.** Utility functions for CSV processing, file handling, and cookie management. |
| `data/` | **Storage.** Local storage for output CSVs and execution logs. |
| `.auth/` | **Secure Storage.** Hidden directory for storing session cookies (`cookies.pkl`). |

---

## 🛠️ 2. Key Component Breakdown

### 🏗️ Core Layer (`core/`)
*   **`DriverManager`**: Handles the creation and configuration of the Selenium WebDriver. It includes anti-detection settings (User-Agent spoofing, automation flag removal) and manages temporary Chrome profiles.
*   **`Services`**: The bridge between the user interface (CLI/API) and the low-level actions.
    *   `ScraperService`: Orchestrates group member scraping and search-based profile scraping.
    *   `ConnectionService`: Manages single and mass connection requests.
    *   `MessagingService`: Handles group-based messaging campaigns.

### 🔑 Authentication Layer (`auth/`)
*   **`AuthManager`**: The single source of truth for authentication.
    1.  Attempts **Cookie Login** first using `.auth/cookies.pkl`.
    2.  Falls back to **Credential Login** (Email/Password from `.env`) if cookies are missing or expired.
    3.  **Saves Cookies** automatically upon successful credential login for future sessions.

### 🚀 Logic Layers (`actions/` & `scraper/`)
*   **Actions**: Focused on interaction. `connection_sender.py` handles the UI clicks to send a request, while `search_profiles.py` handles navigating search results.
*   **Scrapers**: Focused on data extraction. `group_scraper.py` implements complex scrolling and search-prefix strategies (Light/Medium/Robust) to bypass LinkedIn's member list limits.

---

## 🔄 3. Code Execution Flow

A typical operation (e.g., Scraping Group Members via CLI) follows this sequence:

1.  **User Input**: User runs `python cli.py` and selects "Scrape LinkedIn group members".
2.  **Configuration**: `cli.py` loads credentials from `.env` via `config/settings.py`.
3.  **Driver Setup**: `DriverManager` initializes a new Chrome instance with anti-detection headers.
4.  **Authentication**:
    *   `AuthManager.login(driver)` is called.
    *   It checks `.auth/cookies.pkl`. If valid, it injects them and refreshes.
    *   If invalid, it navigates to the login page, enters credentials, and solves any challenges (if manual).
5.  **Service Call**: `cli.py` calls `ScraperService.scrape_group_members()`.
6.  **Scraper Execution**: `ScraperService` calls `scraper.group_scraper.scraper()`.
    *   The scraper scrolls through the list, extracts data (Name, Headline, Profile Link).
    *   Data is saved incrementally using `utils/group_data_saver.py`.
7.  **Finalization**: Output is saved to `data/csv/`, logs are closed, and `DriverManager.cleanup_driver()` shuts down the browser.

---

## 📊 4. Data Flow & Persistence

*   **Credentials**: Stored in `.env` (Excluded from Git for security).
*   **Session State**: Persistent cookies are stored in `.auth/cookies.pkl`.
*   **Output Data**: Generated CSVs are placed in `data/csv/`. Files are typically timestamped or tagged with the Group ID.
*   **Logs**: Detailed execution logs are stored in `data/logs/` to help debug failed actions or tracking progress.

---

## 🔐 5. Security & Anti-Detection

The project implements several layers of protection to avoid LinkedIn account restrictions:
*   **Randomized Delays**: Wait times between actions (15-35s) mimic human behavior.
*   **User-Agent Randomization**: Rotating headers to make the scraper appear as a normal browser.
*   **Credential Masking**: Using environment variables and hidden folders for sensitive data.
*   **Incremental Saving**: Saving data frequently so a crash or block doesn't lose all progress.

---

📖 *For more information on the API, see `API_EXAMPLES.md`. For setup instructions, see `README.md`.*
