# Refactoring LinkedIn Scraper to Component-Based Architecture

I need to refactor my LinkedIn scraper project to follow a **Component-Based Architecture** and **Single Responsibility Principle**. The goal is to separate the "finding of elements" (Components) from the "business logic" (Scrapers/Actions) to make the code easier to maintain, debug, and extend.

## 🎯 Objectives
1.  **Isolate Selenium Logic**: Create a `components/` directory to hold all Selenium logic for finding and interacting with page elements.
2.  **Refactor Workflows**: [scraper/](cci:1://file:///c:/Users/yelmanso/vs%20project/leadgen/linkedIn%20scraper/LinkedIn-scraper/scraper/group_scraper.py:410:0-587:32) and `actions/` should only contain high-level business logic (workflows) and call the components.
3.  **Clean Utils**: `utils/` should only contain non-browser logic (CSV handling, logging, data cleaning).
4.  **Preserve Auth**: `auth/` should remain separate for login/session management.

---

## 📂 Target Project Structure

Please reorganize the project files to match this structure:

```text
LinkedIn-scraper/
│
├── components/                 # [NEW] Pure Selenium logic (Input: Driver -> Output: Data/Action)
│   ├── __init__.py
│   ├── common/                 # Logic shared across pages
│   │   ├── navigation.py       # navigate_to(url), refresh_page()
│   │   ├── popups.py           # close_google_popup(), handle_messaging_overlay()
│   │   └── scrolling.py        # scroll_to_bottom(), scroll_to_element()
│   │
│   ├── profile/                # Specific to Profile Page
│   │   ├── header.py           # extract_name(), extract_headline()
│   │   ├── experience.py       # extract_experience_list()
│   │   └── about.py            # extract_about_section()
│   │
│   ├── search/                 # Specific to Search Results
│   │   ├── filters.py          # set_people_filter()
│   │   └── results.py          # extract_profiles_from_list(), click_next_page()
│   │
│   └── inputs/                 # Specific for typing/clicking interactions
│       └── message_box.py      # type_connection_note(), send_message()
│
├── scraper/                    # [REFACTOR] High-level "Process Managers"
│   ├── workflows/              # Business logic scripts
│   │   ├── profile_enrichment.py   # Calls components.profile.* -> Saves to CSV
│   │   ├── group_scraping.py       # Calls components.common.scrolling
│   │   └── search_scraping.py
│   │
│   └── enrichment/             # Pure Python Logic (No Selenium)
│       ├── email_generator.py
│       └── domain_finder.py
│
├── actions/                    # [REFACTOR] Interaction Workflows
│   ├── workflows/
│       ├── connection_sender.py
│       └── message_sender.py
│
├── utils/                      # [CLEANUP] Non-browser utilities
│   ├── csv_handler.py          # Universal CSV reader/writer
│   ├── logger.py               # Centralized logging setup
│   └── data_cleaner.py         # Text cleaning, emoji removal
│
└── auth/                       # [KEEP] Authentication logic
    └── auth_manager.py