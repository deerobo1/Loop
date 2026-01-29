"""
UI2 Package - Skype-Inspired Modern Design
Clean, minimal aesthetic with generous whitespace and smooth animations
"""

from .main_window import EnhancedMainWindow
from .login_dialog import EnhancedLoginDialog
from .private_chat import PrivateChatManager, PrivateChatWidget
from .styles import MAIN_STYLESHEET, LOGIN_STYLESHEET

__all__ = [
    'EnhancedMainWindow',
    'EnhancedLoginDialog',
    'PrivateChatManager',
    'PrivateChatWidget',
    'MAIN_STYLESHEET',
    'LOGIN_STYLESHEET',
]
