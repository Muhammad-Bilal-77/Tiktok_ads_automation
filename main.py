"""
TikTok Ads Manager Automation - Main Script
=============================================
Uses REAL mouse movement with a visible cursor overlay.
Reliable account selection and campaign navigation.

Usage:
    python main.py
"""

import time
import re
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoAlertPresentException,
    StaleElementReferenceException,
)

from config import (
    TIKTOK_ADS_URL,
    TIKTOK_HOME_URL,
    TIKTOK_CAMPAIGN_URL_TEMPLATE,
    EXPLICIT_WAIT,
)
from browser import create_browser, close_browser, disconnect_browser
from logger import log_info, log_step, log_error, log_success, log_warning, LoadingSpinner, stop_all_spinners


# ─────────────────────────────────────────────────────────────
# VISIBLE CURSOR OVERLAY
# ─────────────────────────────────────────────────────────────

CURSOR_JS = """
(function() {
    // Don't inject twice
    if (document.getElementById('selenium-cursor')) return;

    // Red dot that follows the mouse
    var dot = document.createElement('div');
    dot.id = 'selenium-cursor';
    dot.style.cssText = 'width:20px;height:20px;border-radius:50%;background:rgba(255,0,0,0.7);' +
        'position:fixed;top:0;left:0;z-index:999999;pointer-events:none;' +
        'box-shadow:0 0 10px rgba(255,0,0,0.5),0 0 20px rgba(255,0,0,0.3);' +
        'transition:transform 0.05s ease;transform:translate(-50%,-50%)';
    document.body.appendChild(dot);

    // Click ripple effect
    var ripple = document.createElement('div');
    ripple.id = 'selenium-ripple';
    ripple.style.cssText = 'width:40px;height:40px;border-radius:50%;border:3px solid red;' +
        'position:fixed;z-index:999998;pointer-events:none;opacity:0;' +
        'transform:translate(-50%,-50%) scale(0);';
    document.body.appendChild(ripple);

    // Track mouse movement
    document.addEventListener('mousemove', function(e) {
        dot.style.left = e.clientX + 'px';
        dot.style.top = e.clientY + 'px';
    });

    // Click animation
    document.addEventListener('click', function(e) {
        ripple.style.left = e.clientX + 'px';
        ripple.style.top = e.clientY + 'px';
        ripple.style.opacity = '1';
        ripple.style.transform = 'translate(-50%,-50%) scale(0)';
        setTimeout(function() {
            ripple.style.transition = 'all 0.4s ease-out';
            ripple.style.transform = 'translate(-50%,-50%) scale(1.5)';
            ripple.style.opacity = '0';
        }, 10);
        setTimeout(function() {
            ripple.style.transition = 'none';
        }, 500);
    });

    // Label showing current action
    var label = document.createElement('div');
    label.id = 'selenium-label';
    label.style.cssText = 'position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:999999;' +
        'background:rgba(0,0,0,0.8);color:#0f0;padding:8px 20px;border-radius:20px;' +
        'font-family:monospace;font-size:14px;pointer-events:none;' +
        'box-shadow:0 2px 10px rgba(0,0,0,0.3);';
    label.textContent = 'AUTOMATION ACTIVE';
    document.body.appendChild(label);
})();
"""

CURSOR_UPDATE_LABEL_JS = """
var label = document.getElementById('selenium-label');
if (label) label.textContent = arguments[0];
"""


def inject_cursor(driver):
    """Inject visible cursor overlay into the current page."""
    try:
        driver.execute_script(CURSOR_JS)
    except Exception:
        pass


def update_cursor_label(driver, text):
    """Update the status label shown on the browser."""
    try:
        driver.execute_script(CURSOR_UPDATE_LABEL_JS, text)
    except Exception:
        pass


def mouse_click(driver, element, description="element"):
    """Move mouse to element and click — with visible cursor."""
    inject_cursor(driver)
    update_cursor_label(driver, f"Clicking: {description}")
    
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(0.3)
    actions.click()
    actions.perform()
    log_info(f"Mouse clicked: {description}")
    time.sleep(0.3)


# ─────────────────────────────────────────────────────────────
# Navigation helpers
# ─────────────────────────────────────────────────────────────

def fast_navigate(driver, url, description="page", max_retries=3):
    """Navigate with retry and live spinner."""
    for attempt in range(1, max_retries + 1):
        spinner = LoadingSpinner(f"Loading {description} (attempt {attempt}/{max_retries})")
        spinner.start()
        try:
            dismiss_dialogs(driver)
            driver.get(url)
            dismiss_dialogs(driver)
            current = driver.current_url
            if current and "blank" not in current and "newtab" not in current:
                spinner.stop(f"{description} loaded!")
                inject_cursor(driver)
                return True
            spinner.stop("Blank page, retrying...")
        except TimeoutException:
            spinner.stop(f"Timeout, retrying...")
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
        except WebDriverException as e:
            spinner.stop(f"Error: {str(e)[:50]}")
    log_error(f"Failed to load {description}.")
    return False


def dismiss_dialogs(driver):
    """Dismiss alerts and modals."""
    try:
        driver.switch_to.alert.accept()
    except (NoAlertPresentException, WebDriverException):
        pass
    try:
        for text in ["Confirm", "Leave", "OK", "Yes", "Discard", "Got it"]:
            btns = driver.find_elements(By.XPATH,
                f"//button[contains(text(),'{text}')] | //span[contains(text(),'{text}')]/ancestor::button")
            for btn in btns:
                if btn.is_displayed():
                    btn.click()
                    return
    except Exception:
        pass


def extract_aadvid(url):
    """Extract the aadvid (account ID) from a TikTok Ads URL."""
    match = re.search(r'aadvid=(\d+)', url)
    return match.group(1) if match else None


# ─────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────

def wait_for_login(driver):
    print("\n" + "=" * 50)
    print("  LOGIN: Log in to TikTok in the browser,")
    print("  then type 'yes' here.")
    print("=" * 50 + "\n")
    while True:
        answer = input(">>> Logged in? (yes/no): ").strip().lower()
        if answer in ("yes", "y"):
            log_success("Login confirmed!")
            return
        elif answer in ("no", "n"):
            print("    Take your time.")
        else:
            print("    Type 'yes' or 'no'.")


# ─────────────────────────────────────────────────────────────
# Select Ads Manager Account (MOUSE + coordinate-based)
# ─────────────────────────────────────────────────────────────

def select_ads_manager_account(driver):
    """
    RELIABLE account selection using JavaScript to find the exact
    Ads Manager card element, then mouse-click it.
    """
    log_step(5, "Opening account selection page...")
    fast_navigate(driver, TIKTOK_HOME_URL, "account selection")
    inject_cursor(driver)
    update_cursor_label(driver, "Looking for Ads Manager account...")

    # Wait for the page to fully render
    spinner = LoadingSpinner("Waiting for accounts to appear")
    spinner.start()
    try:
        WebDriverWait(driver, EXPLICIT_WAIT).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Ads Manager')]"))
        )
        spinner.stop("Accounts visible!")
    except TimeoutException:
        spinner.stop("Slow load, trying anyway...")

    time.sleep(1)  # Let React finish rendering

    log_step(6, "Finding Ads Manager account card...")

    # Use JavaScript to precisely identify the Ads Manager account card.
    # The page structure from screenshot:
    #   - "Business Center (1)" section on left
    #   - "Ads Manager (1)" section on right
    #   - Each has account cards below the heading
    # We need the CARD under "Ads Manager", NOT any random link on the page.

    card_info = driver.execute_script("""
        // Step 1: Find ALL elements that contain "Ads Manager" text (exact section header)
        var allEls = document.querySelectorAll('*');
        var adsManagerHeader = null;
        
        for (var el of allEls) {
            // Look for the section header — should contain "Ads Manager" but not too much other text
            var directText = '';
            for (var node of el.childNodes) {
                if (node.nodeType === 3) directText += node.textContent.trim();
            }
            // Also check for child spans
            if (!directText) {
                var spans = el.querySelectorAll(':scope > span');
                for (var s of spans) directText += s.textContent.trim();
            }
            
            if (directText.startsWith('Ads Manager') && directText.length < 25) {
                adsManagerHeader = el;
                break;
            }
        }
        
        if (!adsManagerHeader) {
            return JSON.stringify({error: 'Could not find Ads Manager header'});
        }
        
        // Step 2: Find the parent container of the Ads Manager section
        // Go up until we find a container that's roughly half the page width
        var section = adsManagerHeader.parentElement;
        while (section && section.getBoundingClientRect().width < 200) {
            section = section.parentElement;
        }
        
        // Step 3: Find the account card WITHIN this section
        // Account cards typically have: account name, ID number, and are clickable
        // They are NOT the header itself
        var card = null;
        
        // Look for elements with numeric IDs (like "ID: 763193719403...")
        var descendants = section.querySelectorAll('*');
        for (var d of descendants) {
            var text = d.textContent;
            // Skip the header itself
            if (d === adsManagerHeader) continue;
            // Look for elements that contain an ID pattern
            if (/ID:\\s*\\d{10,}/.test(text) && d.getBoundingClientRect().height > 30) {
                card = d;
                break;
            }
        }
        
        // Fallback: look for any clickable-looking card in the section
        if (!card) {
            var candidates = section.querySelectorAll('div, a');
            for (var c of candidates) {
                var rect = c.getBoundingClientRect();
                // Card should be sizable and below the header
                if (rect.height > 40 && rect.height < 200 && rect.width > 100 &&
                    rect.top > adsManagerHeader.getBoundingClientRect().bottom) {
                    card = c;
                    break;
                }
            }
        }
        
        if (!card) {
            return JSON.stringify({error: 'Could not find account card in Ads Manager section'});
        }
        
        // Step 4: Get the card's center coordinates
        var cardRect = card.getBoundingClientRect();
        return JSON.stringify({
            found: true,
            x: Math.round(cardRect.x + cardRect.width / 2),
            y: Math.round(cardRect.y + cardRect.height / 2),
            width: Math.round(cardRect.width),
            height: Math.round(cardRect.height),
            text: card.textContent.substring(0, 80).trim()
        });
    """)

    log_info(f"Card search result: {card_info}")
    data = json.loads(card_info)

    if data.get("error"):
        log_warning(data["error"])
        log_warning("Please click the Ads Manager account manually.")
        input(">>> ENTER after selecting account... ")
        aadvid = extract_aadvid(driver.current_url)
        return aadvid

    # Found the card! Click it with mouse at exact coordinates
    x, y = data["x"], data["y"]
    log_info(f"Account card at ({x}, {y}): {data.get('text', '')[:50]}")
    update_cursor_label(driver, f"Clicking account at ({x}, {y})")

    # Move mouse to center of card and click
    # ActionChains move_by_offset is relative to current mouse position
    # So we first move to body (0,0) then to the card
    body = driver.find_element(By.TAG_NAME, "body")
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(body, x - body.size['width']//2, y - body.size['height']//2)
    actions.pause(0.3)
    actions.click()
    actions.perform()
    log_info("Mouse clicked on Ads Manager account card!")

    # Wait for page to change
    spinner = LoadingSpinner("Waiting for account to load")
    spinner.start()

    aadvid = None
    for i in range(10):
        time.sleep(1)
        current_url = driver.current_url
        aadvid = extract_aadvid(current_url)
        if aadvid:
            spinner.stop(f"Account loaded! ID: {aadvid}")
            log_success(f"URL: {current_url}")
            return aadvid
        # Check if URL changed from home
        if "/home" not in current_url.split("?")[0]:
            spinner.stop(f"Navigated to: {current_url}")
            aadvid = extract_aadvid(current_url)
            return aadvid

    spinner.stop("URL didn't change - trying JS click...")

    # Fallback: JS click on the card element directly
    try:
        driver.execute_script("""
            var section = arguments[0];
            var descendants = document.querySelectorAll('*');
            var adsManagerHeader = null;
            for (var el of descendants) {
                var directText = el.textContent.trim();
                if (directText.startsWith('Ads Manager') && directText.length < 25 && el.children.length < 5) {
                    adsManagerHeader = el;
                    break;
                }
            }
            if (!adsManagerHeader) return;
            
            var parent = adsManagerHeader.parentElement;
            while (parent && parent.getBoundingClientRect().width < 200) parent = parent.parentElement;
            
            // Find and click any link in this section
            var links = parent.querySelectorAll('a');
            for (var link of links) {
                var rect = link.getBoundingClientRect();
                if (rect.top > adsManagerHeader.getBoundingClientRect().bottom && rect.height > 20) {
                    link.click();
                    return;
                }
            }
            
            // Click any card-like div
            var divs = parent.querySelectorAll('div');
            for (var div of divs) {
                var rect = div.getBoundingClientRect();
                if (rect.top > adsManagerHeader.getBoundingClientRect().bottom && 
                    rect.height > 40 && rect.height < 200) {
                    div.click();
                    return;
                }
            }
        """)
        log_info("JS click attempted on account card.")
        time.sleep(2)
        current = driver.current_url
        aadvid = extract_aadvid(current)
        if aadvid:
            log_success(f"Account loaded! ID: {aadvid} | URL: {current}")
            return aadvid
    except Exception as e:
        log_warning(f"JS click failed: {e}")

    # Manual fallback
    log_warning("Please click the Ads Manager account manually.")
    input(">>> ENTER after selecting account... ")
    aadvid = extract_aadvid(driver.current_url)
    return aadvid


# ─────────────────────────────────────────────────────────────
# Navigate to Campaigns (with correct aadvid)
# ─────────────────────────────────────────────────────────────

def go_to_campaigns(driver, aadvid=None):
    """
    Navigate to Campaign page with the correct account ID.
    If aadvid is provided, uses it in the URL.
    Otherwise extracts it from the current URL.
    """
    log_step(7, "Going to Campaigns page...")

    # Get aadvid from current URL if not provided
    if not aadvid:
        aadvid = extract_aadvid(driver.current_url)

    if not aadvid:
        log_warning("No account ID found. Extracting from page...")
        # Try to get it from the page
        try:
            aadvid = driver.execute_script("""
                var match = window.location.href.match(/aadvid=(\\d+)/);
                if (match) return match[1];
                // Try finding it in page content
                var text = document.body.textContent;
                var idMatch = text.match(/ID:\\s*(\\d{15,})/);
                if (idMatch) return idMatch[1];
                return null;
            """)
        except Exception:
            pass

    if aadvid:
        campaign_url = TIKTOK_CAMPAIGN_URL_TEMPLATE.format(aadvid=aadvid)
        log_info(f"Campaign URL: {campaign_url}")
    else:
        campaign_url = "https://ads.tiktok.com/i18n/manage/campaign?lang=en"
        log_warning("No aadvid found, using generic campaign URL")

    # Navigate with retries
    for attempt in range(1, 4):
        spinner = LoadingSpinner(f"Loading Campaigns (attempt {attempt}/3)")
        spinner.start()

        dismiss_dialogs(driver)

        try:
            driver.get(campaign_url)
        except (TimeoutException, WebDriverException):
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass

        time.sleep(1)
        dismiss_dialogs(driver)
        inject_cursor(driver)
        update_cursor_label(driver, "Loading Campaigns page...")

        current = driver.current_url
        if "manage/campaign" in current.lower():
            spinner.stop(f"Campaigns loaded! URL: {current}")
            log_success("On the Campaigns page!")
            return True

        # If we got redirected, try again
        if "/home" in current:
            spinner.stop("Redirected to home, retrying with account ID...")
            # Re-extract aadvid if available
            if aadvid:
                campaign_url = TIKTOK_CAMPAIGN_URL_TEMPLATE.format(aadvid=aadvid)
            continue

        spinner.stop(f"URL: {current}")
        if "campaign" in current.lower():
            return True

    log_warning(f"Final URL: {driver.current_url}")
    return "campaign" in driver.current_url.lower()


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def open_ads_manager():
    driver = None

    try:
        print("\n" + "=" * 50)
        print("  TikTok Ads Automation [MAIN LOGIN & ROUTING]")
        print("=" * 50 + "\n")

        # Try to connect first
        try:
            from browser import connect_browser
            driver = connect_browser()
            log_info("Successfully connected to existing Chrome.")
        except Exception:
            log_info("No existing Chrome found on port 9222. Launching new Chrome...")
            driver = create_browser()

        # Open login page
        log_step(1, "Opening TikTok Ads...")
        fast_navigate(driver, TIKTOK_ADS_URL, "TikTok Ads login")
        inject_cursor(driver)

        # Wait for login
        wait_for_login(driver)
        
        # Go to home to extract ads manager accounts
        log_step(2, "Navigating to Account Selection...")
        fast_navigate(driver, "https://ads.tiktok.com/i18n/home", "Account Selection")
        time.sleep(2) # Give the page a moment to render
        
        log_info("Extracting Ads Manager accounts from the page...")
        try:
            page_text = driver.execute_script("return document.body.innerText;")
            ads_section = page_text.split("Ads Manager (", 1)[1] if "Ads Manager (" in page_text else page_text
            
            accounts = []
            matches = re.finditer(r'(?:^|\n)([^\n]+?)\s*\nID:\s*(\d+)', ads_section, re.MULTILINE)
            for match in matches:
                accounts.append(f"{match.group(1).strip()} -> {match.group(2).strip()}")
                
            print("\nHow would you like to select your campaign?")
            print("  1) Choose from the extracted menu")
            print("  2) Select manually in the browser")
            method_choice = input(">>> (1/2): ").strip()
            
            if method_choice == '1' and accounts:
                print("\n" + "=" * 50)
                print("             ADS MANAGER ACCOUNTS")
                print("=" * 50)
                for i, acc in enumerate(accounts):
                    print(f"[{i+1}] {acc}")
                print("=" * 50)
                
                while True:
                    acc_choice = input(f"\n>>> Select an account number (1-{len(accounts)}): ").strip()
                    try:
                        idx = int(acc_choice) - 1
                        if 0 <= idx < len(accounts):
                            chosen_acc = accounts[idx]
                            chosen_id = chosen_acc.split("->")[1].strip()
                            print(f"\nYou selected: {chosen_acc}")
                            
                            target_url = f"https://ads.tiktok.com/i18n/manage/campaign?aadvid={chosen_id}"
                            print(f"Redirecting browser to: {target_url}")
                            if fast_navigate(driver, target_url, "Campaigns page"):
                                break
                            else:
                                print("Failed to redirect. Trying manual selection.")
                                method_choice = '2'
                                break
                        else:
                            print("Invalid number. Try again.")
                    except ValueError:
                        print("Please enter a valid number.")
            else:
                if method_choice == '1' and not accounts:
                    print("No accounts found to display in menu. Switching to manual mode.")
                while True:
                    done_manual = input("\n>>> Are you done manually going to the campaign page? (yes/no): ").strip().lower()
                    if done_manual in ['yes', 'y']:
                        break
                    else:
                        print("Waiting... Please manually click and navigate to the campaign page in Chrome.")
                        time.sleep(1)
        except Exception as extract_err:
            log_error(f"Failed to extract accounts: {extract_err}")

        # Ask if they want to start the campaign automation
        start_again = input(">>> Start adding campaign script (create_campaign.py)? (yes/no): ").strip().lower()
        if start_again in ['yes', 'y']:
            log_info("Starting create_campaign.py in a NEW terminal...")
            stop_all_spinners()
            
            import subprocess
            import sys
            # Launch in a NEW terminal window on Windows
            subprocess.Popen('start python create_campaign.py', shell=True)
            # Exit this terminal
            sys.exit(0)
        else:
            log_info("User selected NO. Exiting.")
            print("  ENTER to disconnect (Chrome stays open).")
            input(">>> ")

    except WebDriverException as e:
        log_error(f"WebDriver error: {e}")

    except KeyboardInterrupt:
        log_warning("Stopped (Ctrl+C)")

    except Exception as e:
        stop_all_spinners()
        log_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            from browser import disconnect_browser
            disconnect_browser(driver)
        log_info("Done.")


if __name__ == "__main__":
    open_ads_manager()
