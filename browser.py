"""
Browser Manager for TikTok Ads Automation
===========================================
FAST Chrome setup with your profile. Uses 'eager' page load strategy
so Selenium doesn't wait for images/scripts — only the DOM.
"""

import shutil
import os
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from config import CHROME_USER_DATA_DIR, CHROME_PROFILE, PAGE_LOAD_TIMEOUT, IMPLICIT_WAIT
from logger import log_info, log_step, log_warning

TEMP_PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chrome_profile_copy"
)


def _prepare_profile_copy():
    """Copy essential profile files and patch preferences for clean start."""
    source_profile = os.path.join(CHROME_USER_DATA_DIR, CHROME_PROFILE)
    dest_profile = os.path.join(TEMP_PROFILE_DIR, CHROME_PROFILE)

    if os.path.exists(TEMP_PROFILE_DIR):
        shutil.rmtree(TEMP_PROFILE_DIR, ignore_errors=True)
    os.makedirs(dest_profile, exist_ok=True)

    # Copy parent-level files
    for f in ["Local State"]:
        src = os.path.join(CHROME_USER_DATA_DIR, f)
        if os.path.exists(src):
            try:
                shutil.copy2(src, os.path.join(TEMP_PROFILE_DIR, f))
            except Exception:
                pass

    # Copy essential profile files
    for filename in [
        "Cookies", "Cookies-journal", "Login Data", "Login Data-journal",
        "Web Data", "Web Data-journal", "Preferences", "Secure Preferences", "Bookmarks",
    ]:
        src = os.path.join(source_profile, filename)
        if os.path.exists(src):
            try:
                shutil.copy2(src, os.path.join(dest_profile, filename))
            except Exception:
                pass

    # Copy Network directory (cookies in newer Chrome)
    network_src = os.path.join(source_profile, "Network")
    if os.path.isdir(network_src):
        try:
            shutil.copytree(network_src, os.path.join(dest_profile, "Network"), dirs_exist_ok=True)
        except Exception:
            pass

    # Patch preferences to prevent "Restore pages" popup
    _patch_preferences(dest_profile)
    return TEMP_PROFILE_DIR


def _patch_preferences(profile_dir):
    """Mark profile as cleanly exited to prevent restore dialog."""
    prefs_file = os.path.join(profile_dir, "Preferences")
    prefs = {}

    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            prefs = {}

    prefs.setdefault("profile", {})
    prefs["profile"]["exit_type"] = "Normal"
    prefs["profile"]["exited_cleanly"] = True
    prefs.setdefault("session", {})
    prefs["session"]["restore_on_startup"] = 4
    prefs["session"]["startup_urls"] = []

    try:
        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f)
    except Exception:
        pass


def create_browser():
    """
    Open Chrome FAST with your profile.
    Uses pageLoadStrategy='eager' — don't wait for images/scripts, only DOM.
    """
    log_step(1, "Preparing profile...")
    temp_dir = _prepare_profile_copy()
    log_info("Profile ready.")

    log_step(2, "Configuring Chrome for SPEED...")
    chrome_options = Options()

    # Use copied profile
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    chrome_options.add_argument(f"--profile-directory={CHROME_PROFILE}")

    # === SPEED: Don't wait for full page load, only DOM ready ===
    chrome_options.page_load_strategy = "eager"

    # Prevent popups and restore dialogs
    chrome_options.add_argument("--disable-session-crashed-bubble")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--hide-crash-restore-bubble")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-features=InfiniteSessionRestore")

    # Stability
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-popup-blocking")

    # Enable remote debugging so other scripts can connect to this Chrome
    chrome_options.add_argument("--remote-debugging-port=9222")

    # Speed: disable unnecessary features
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")

    # Hide automation
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    log_step(3, "Launching Chrome...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)

    log_info("Chrome is READY! (Remote debugging on port 9222)")
    return driver


def connect_browser():
    """
    Connect to an ALREADY RUNNING Chrome (started by main.py).
    Uses port 9222 to attach Selenium to the existing browser.
    No new window opens — you control the same Chrome!

    Returns:
        webdriver.Chrome: Connected to existing Chrome
    """
    log_info("Connecting to existing Chrome on port 9222...")
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    chrome_options.page_load_strategy = "eager"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)

    # Make sure we are on the right tab! Remote debugging might attach to a background tab.
    found_tiktok = False
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "tiktok.com" in driver.current_url:
            found_tiktok = True
            break
            
    if not found_tiktok and len(driver.window_handles) > 0:
        # Fallback to the last tab if we couldn't find one explicitly with tiktok in the URL
        driver.switch_to.window(driver.window_handles[-1])

    log_info(f"Connected! Current URL: {driver.current_url}")
    log_info(f"Tabs open: {len(driver.window_handles)}")
    return driver


def disconnect_browser(driver):
    """Disconnect from Chrome WITHOUT closing it. Chrome stays open."""
    try:
        if driver:
            driver.service.stop()
            log_info("Disconnected from Chrome (browser stays open).")
    except Exception:
        pass


def close_browser(driver):
    """Close browser completely."""
    try:
        if driver:
            driver.quit()
            log_info("Browser closed.")
    except Exception:
        pass
