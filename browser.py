"""
Browser Manager for TikTok Ads Automation
===========================================
FAST Chrome setup with your profile. Uses 'eager' page load strategy
so Selenium doesn't wait for images/scripts — only the DOM.
"""

import shutil
import os
import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from config import CHROME_USER_DATA_DIR, CHROME_PROFILE, PAGE_LOAD_TIMEOUT, IMPLICIT_WAIT
from logger import log_info, log_step, log_warning

TEMP_PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chrome_profile_copy"
)

def _get_local_driver_path():
    """Ensure chromedriver.exe is in the project root to bypass security policies."""
    local_driver = os.path.join(os.getcwd(), "chromedriver.exe")
    if os.path.exists(local_driver):
        return local_driver
    
    try:
        log_info("Ensuring local chromedriver.exe...")
        downloaded_path = ChromeDriverManager().install()
        # Use shutil.copy2 to preserve metadata, might help with some policies
        shutil.copy2(downloaded_path, local_driver)
        log_info(f"Copied driver to: {local_driver}")
        return local_driver
    except Exception as e:
        log_warning(f"Failed to copy local driver: {e}")
        return None


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
    
    # Keep browser open after script exits
    chrome_options.add_experimental_option("detach", True)

    log_step(3, "Launching Chrome...")
    driver_path = _get_local_driver_path()
    service = Service(driver_path) if driver_path else Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)
    
    try:
        driver.maximize_window()
    except Exception:
        pass

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

    service = Service(_get_local_driver_path() or ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)

    # Try to maximize and focus
    try:
        driver.maximize_window()
        driver.execute_script("window.focus();")
    except Exception:
        pass

    # List all handles for debugging
    log_info(f"Checking {len(driver.window_handles)} window handles...")
    handles_info = []
    
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            title = driver.title or ""
            url = driver.current_url or ""
            size = driver.get_window_size()
            
            # Score the window based on how "real" it looks
            score = 0
            if "tiktok.com" in url.lower(): score += 100
            if title and "New Tab" not in title: score += 50
            if size['width'] > 500: score += 20
            if size['height'] > 400: score += 20
            
            handles_info.append({
                'handle': handle,
                'title': title,
                'url': url,
                'size': size,
                'score': score
            })
            log_info(f"  - Window: '{title[:30]}' | URL: {url[:40]}... | Score: {score}")
        except Exception as e:
            continue
            
    # Sort by score descending
    handles_info.sort(key=lambda x: x['score'], reverse=True)
    
    if handles_info and handles_info[0]['score'] > 0:
        target = handles_info[0]
        driver.switch_to.window(target['handle'])
        log_info(f"Targeting best window: '{target['title']}' (Score: {target['score']})")
        found_tiktok = "tiktok.com" in target['url'].lower()
    else:
        found_tiktok = False

    if not found_tiktok:
        log_info("No suitable TikTok window found. Opening a FRESH window...")
        try:
            # Force a completely new top-level window
            driver.execute_script("window.open('https://ads.tiktok.com/i18n/login?lang=en', '_blank', 'width=1400,height=1000,menubar=yes,location=yes,resizable=yes,scrollbars=yes');")
            time.sleep(2)
            # Find the new handle
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if "tiktok.com" in driver.current_url.lower():
                    break
        except Exception as e:
            log_warning(f"Could not open new window: {e}")
            if len(driver.window_handles) > 0:
                driver.switch_to.window(driver.window_handles[-1])

    # Final attempt to focus and maximize
    try:
        driver.maximize_window()
        # Bring to front
        driver.execute_script("window.focus();")
        # Click on body to force focus (sometimes works)
        try:
            driver.find_element(By.TAG_NAME, "body").click()
        except:
            pass
    except Exception:
        pass

    log_info(f"Connected! Final URL: {driver.current_url}")
    return driver


def disconnect_browser(driver):
    """Disconnect from Chrome WITHOUT closing it. Chrome stays open."""
    try:
        if driver:
            driver.service.stop()
            log_info("Disconnected from Chrome (browser stays open).")
    except Exception:
        pass

def smart_click(driver, element_or_coords, description="element"):
    """
    Highly robust click utility.
    Handles scrolling, visibility, and click interceptions with multiple fallbacks.
    """
    from selenium.webdriver.common.action_chains import ActionChains
    import time
    
    try:
        # If coordinates provided
        if isinstance(element_or_coords, (list, tuple, dict)):
            x = element_or_coords.get('x') if isinstance(element_or_coords, dict) else element_or_coords[0]
            y = element_or_coords.get('y') if isinstance(element_or_coords, dict) else element_or_coords[1]
            
            # For absolute coordinates, use JS or move to 0,0 first
            driver.execute_script(f"""
                var el = document.elementFromPoint({x}, {y});
                if (el) el.click();
            """)
            return True
            
        # If element provided
        el = element_or_coords
        
        # 1. Scroll into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", el)
        time.sleep(0.3)
        
        # 2. Try standard Selenium click
        try:
            el.click()
            return True
        except Exception:
            pass
            
        # 3. Try ActionChains click
        try:
            ActionChains(driver).move_to_element(el).click().perform()
            return True
        except Exception:
            pass
            
        # 4. Try JS click (Final Fallback)
        driver.execute_script("arguments[0].click();", el)
        return True
        
    except Exception as e:
        log_warning(f"Smart click failed for {description}: {e}")
        return False


def close_browser(driver):
    """Close browser completely."""
    try:
        if driver:
            driver.quit()
            log_info("Browser closed.")
    except Exception:
        pass
