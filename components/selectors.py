"""
Centralized Selectors Registry — Single Source of Truth.

When LinkedIn changes their HTML, update the selectors HERE.
Every component module imports from this file instead of hard-coding strings.

Naming convention:
    - CSS selectors are plain strings
    - XPath selectors are prefixed with XPATH_
    - Lists of fallback selectors end with _FALLBACKS
"""
from selenium.webdriver.common.by import By


# =============================================================================
# GROUP MEMBERS PAGE
# =============================================================================
class GroupSelectors:
    """Selectors for LinkedIn Group members page."""

    # --- Member list ---
    MEMBER_LIST_ITEMS = (
        By.CSS_SELECTOR,
        "ul.artdeco-list.groups-members-list__results-list li.artdeco-list__item"
    )
    MEMBER_ACTION_ROW = (By.CSS_SELECTOR, "div.ui-entity-action-row")

    # --- Individual member data ---
    MEMBER_NAME = (
        By.CSS_SELECTOR,
        ".artdeco-entity-lockup__title a, .artdeco-entity-lockup__title"
    )
    MEMBER_PROFILE_LINK = (By.CSS_SELECTOR, "a.ui-entity-action-row__link")
    MEMBER_HEADLINE = (By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle")
    MEMBER_IMAGE = (By.CSS_SELECTOR, ".presence-entity__image")
    MEMBER_BADGE = (By.CSS_SELECTOR, ".artdeco-entity-lockup__badge")

    # --- Search input (multilingual fallbacks) ---
    SEARCH_INPUT_FALLBACKS = [
        (By.CSS_SELECTOR, 'input[placeholder="Chercher des membres"]'),
        (By.CSS_SELECTOR, 'input[placeholder="Search members"]'),
        (By.CSS_SELECTOR, 'input[aria-label="Chercher des membres"]'),
        (By.CSS_SELECTOR, 'input[aria-label="Search members"]'),
        (By.XPATH, '//input[@aria-label="Chercher des membres"]'),
        (By.XPATH, '//input[@aria-label="Search members"]'),
    ]

    # --- Load more / pagination ---
    LOAD_MORE_BUTTON = (
        By.CSS_SELECTOR,
        "button.scaffold-finite-scroll__load-button"
    )
    LOAD_MORE_XPATH_FALLBACKS = [
        (By.XPATH, "//button[.//span[contains(text(), 'Afficher plus de résultats')]]"),
        (By.XPATH, "//button[.//span[text()='Afficher plus de résultats']]"),
        (By.XPATH, "//button[contains(text(), 'Show more results')]"),
        (By.XPATH, "//button[contains(text(), 'Load more')]"),
        (By.XPATH, "//button[.//span[contains(text(), 'Show more')]]"),
        (By.XPATH, "//button[.//span[contains(text(), 'Load more')]]"),
        (By.XPATH, "//button[@aria-label='Show more results']"),
        (By.XPATH, "//button[@aria-label='Load more results']"),
    ]

    # --- Group member messaging ---
    MEMBERS_LIST_RESULTS = (
        By.CSS_SELECTOR,
        "ul.artdeco-list.groups-members-list__results-list li"
    )
    MEMBER_NAME_LOCKUP = (By.CSS_SELECTOR, ".artdeco-entity-lockup__title")
    MESSAGE_BUTTON = (By.CSS_SELECTOR, "button.artdeco-button--secondary")


# =============================================================================
# PROFILE PAGE
# =============================================================================
class ProfileSelectors:
    """Selectors for individual LinkedIn profile pages."""

    # --- Name ---
    # LinkedIn now uses auto-generated hashed classes, so we rely on semantic
    # Structure-based: div > a[href*="/in/"] > h2 (most reliable for profile cards)
    NAME_FALLBACKS = [
        (By.XPATH, "//div//a[contains(@href, 'linkedin.com/in/')]//h2"),
        (By.XPATH, "//div//a[contains(@href, '/in/')]//h2"),
    ]

    # --- About & Experience sections ---
    # Both use JS extractors with semantic selectors (h2 heading text).
    # No hashed class selectors needed.
    ABOUT_HEADINGS = ["About", "À propos", "A propos"]
    EXPERIENCE_HEADINGS = ["Experience", "Expérience", "Experiences", "Expériences"]


# =============================================================================
# SEARCH RESULTS PAGE
# =============================================================================
class SearchSelectors:
    """Selectors for LinkedIn search results page."""

    RESULTS_LIST = (By.CSS_SELECTOR, "ul[role='list'] > li")
    PROFILE_LINKS = (By.CSS_SELECTOR, "ul[role='list'] li a[href*='/in/']")
    PROFILE_NAME = (By.CSS_SELECTOR, 'span[aria-hidden="true"]')

    # --- Pagination ---
    NEXT_BUTTON_FALLBACKS = [
        (By.CSS_SELECTOR, "button[aria-label='Next']"),
        (By.CSS_SELECTOR, ".artdeco-pagination__button--next"),
        (By.CSS_SELECTOR, "button.artdeco-pagination__button--next"),
    ]


# =============================================================================
# CONNECTION REQUEST
# =============================================================================
class ConnectionSelectors:
    """Selectors for sending connection requests on profile pages."""

    # --- Direct connect button ---
    CONNECT_BUTTONS = (
        By.CSS_SELECTOR,
        "div.pb5.ph5 button[id^='ember'][class*='ember-view']"
    )
    CONNECT_TEXTS = ["Se connecter", "Connect"]

    # --- Hidden connect via dropdown ---
    DROPDOWN_TRIGGER = (
        By.CSS_SELECTOR,
        "div.ph5.pb5 div[id^='ember'].artdeco-dropdown.artdeco-dropdown--placement-bottom "
        "button[id^='ember'][class*='artdeco-dropdown__trigger']"
    )
    DROPDOWN_ITEMS = (
        By.CSS_SELECTOR,
        "div.ph5.pb5 div[id^='ember'].artdeco-dropdown.artdeco-dropdown--placement-bottom "
        "ul li div[id^='ember']"
    )

    # --- Connection modal ---
    MODAL_BUTTONS = (
        By.CSS_SELECTOR,
        "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button[id^='ember']"
    )
    MODAL_ALL_BUTTONS = (
        By.CSS_SELECTOR,
        "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__actionbar button"
    )
    NOTE_TEXTAREA = (
        By.CSS_SELECTOR,
        "div[id='artdeco-modal-outlet'] div[id^='ember'].artdeco-modal__content textarea"
    )

    # --- Button texts ---
    ADD_NOTE_TEXTS = ["Ajouter une note", "Add a note"]
    SEND_TEXTS = ["Envoyer", "Send"]
    SEND_WITHOUT_NOTE_TEXTS = ["Envoyer sans note", "Send without a note"]


# =============================================================================
# MESSAGING
# =============================================================================
class MessagingSelectors:
    """Selectors for LinkedIn messaging overlay / compose box."""

    COMPOSE_BOX = (By.CSS_SELECTOR, ".msg-form__contenteditable")
    SEND_BUTTON = (By.CSS_SELECTOR, ".msg-form__send-button")


# =============================================================================
# GOOGLE SEARCH (for Google LinkedIn Profile Scraper)
# =============================================================================
class GoogleSelectors:
    """Selectors for Google search pages when scraping LinkedIn profiles."""

    SEARCH_RESULTS_CONTAINER = (By.CSS_SELECTOR, "#search")
    RESULT_LINKS = (By.CSS_SELECTOR, "div#search a[href]")
    NEXT_PAGE = (By.CSS_SELECTOR, "a#pnnext")

    # --- Google consent popup ---
    CONSENT_BUTTON_FALLBACKS = [
        (By.CSS_SELECTOR, "button[id*='accept']"),
        (By.CSS_SELECTOR, "button[aria-label*='Accept']"),
        (By.XPATH, "//button[contains(text(), 'Accept')]"),
        (By.XPATH, "//button[contains(text(), 'Accepter')]"),
        (By.XPATH, "//button[contains(text(), 'I agree')]"),
        (By.XPATH, "//div[contains(@class, 'QS5gu')]//button[2]"),
    ]


# =============================================================================
# AUTH / LOGIN VERIFICATION
# =============================================================================
class AuthSelectors:
    """Selectors to verify successful LinkedIn login."""

    LOGIN_VERIFICATION_FALLBACKS = [
        (By.CSS_SELECTOR, "[data-test-id='nav-user-profile']"),
        (By.CSS_SELECTOR, ".global-nav__primary-link-me-menu-trigger"),
    ]
