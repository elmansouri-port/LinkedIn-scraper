"""
Authentication Module
Provides unified authentication management for LinkedIn
"""
from .auth_manager import AuthManager

# Legacy imports for backward compatibility
from .login_with_cookies import login_with_cookies
from .login_with_credentials import login_with_credentials

__all__ = [
    'AuthManager',
    'login_with_cookies',  # Legacy
    'login_with_credentials',  # Legacy
]
