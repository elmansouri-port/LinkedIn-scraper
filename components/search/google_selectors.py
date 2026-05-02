"""
Google Search Selectors - Centralized selectors for Google search pages.

All CSS selectors for Google elements (pagination, popups, CAPTCHAs, results).
Edit here if Google changes their HTML structure.
"""


class GoogleSelectors:
    """CSS selectors for Google search page elements."""

    # --- Search results ---
    RESULT_CONTAINERS = [".MjjYud", ".g", "[data-sokoban-grid] [role='listitem']"]

    # --- Pagination ---
    # Primary next button selector (current Google structure)
    NEXT_BUTTON = "#pnnext"

    # Fallback selectors for next button
    NEXT_BUTTON_FALLBACKS = [
        "a#pnnext",
        "a[href*='start=']:nth-of-type(-1)",  # Last link with start param
        "a[aria-label^='Page'][href*='start=']:last-of-type",  # Last page link
        ".LLNLxf",  # Next button class
        "a[href*='start='][id]",  # Any link with start= and an id
    ]

    # Previous button
    PREV_BUTTON = "#pnprev"

    # Page number links (for finding next page URL)
    PAGE_NUMBER_LINKS = "a[aria-label^='Page'][class='fl']"

    # Pagination container
    PAGINATION_CONTAINER = "table.AaVjTc"

    # --- CAPTCHA / Sorry page ---
    CAPTCHA_INDICATORS = [
        ".g-recaptcha",
        "iframe[src*='google.com/recaptcha']",
        "div.g-recaptcha",
    ]

    SORRY_PAGE_INDICATORS = [
        "#sorry-container",
        ".sorry-container",
        "form[action='/sorry']",
        "a[href*='sorry']",
        "#recaptcha",
    ]

    # --- Consent popup ---
    CONSENT_POPUP_BUTTONS = [
        "#L2AGLb",
        "form[action^='https://consent.google.com'] button",
        "button[jsaction*='consent']",
        "#cxnB3b",
        "button[aria-label*='Accept']",
        "button[aria-label*='accept']",
        "button[aria-label*='Reject']",
    ]

    # --- Wait indicator ---
    SEARCH_RESULTS_CONTAINER = "#search"
