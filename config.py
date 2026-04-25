"""
Configuration file for TikTok Ads Automation
=============================================
"""

# ── Target URLs ─────────────────────────────────────────────
TIKTOK_ADS_URL = "https://ads.tiktok.com/i18n/login?lang=en"
TIKTOK_HOME_URL = "https://ads.tiktok.com/i18n/home?lang=en"

# Campaign URL template — {aadvid} gets replaced with actual account ID
TIKTOK_CAMPAIGN_URL_TEMPLATE = "https://ads.tiktok.com/i18n/manage/campaign?aadvid={aadvid}&lang=en"

# ── Timeouts (seconds) ──────────────────────────────────────
PAGE_LOAD_TIMEOUT = 60
IMPLICIT_WAIT = 3
EXPLICIT_WAIT = 10

# ── Chrome Profile Path ────────────────────────────────────
import os
import platform

if platform.system() == "Windows":
    # Auto-detect default Windows Chrome path
    CHROME_USER_DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
else:
    # Fallback/Placeholder for other OS
    CHROME_USER_DATA_DIR = ""

CHROME_PROFILE = "Default"

