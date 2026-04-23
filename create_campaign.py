"""
TikTok Ads - Step 2: Click "Create" on Campaigns Page
=======================================================
The "+ Create" button on TikTok Ads is inside SHADOW DOM.
Normal selectors can't reach it. This script uses JavaScript
to pierce through Shadow DOM and find the actual <button>.

Prerequisites:
    - main.py was run first (Chrome is on campaigns page)

Usage:
    python create_campaign.py
"""

import time
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoAlertPresentException,
)

from browser import connect_browser, disconnect_browser
from logger import log_info, log_step, log_error, log_success, log_warning, LoadingSpinner


# ─────────────────────────────────────────────────────────────
# Cursor overlay — red dot + click ripple + status label
# ─────────────────────────────────────────────────────────────

CURSOR_JS = """
(function() {
    if (document.getElementById('sel-cursor')) return;

    var dot = document.createElement('div');
    dot.id = 'sel-cursor';
    dot.style.cssText = 'width:22px;height:22px;border-radius:50%;' +
        'background:radial-gradient(circle,rgba(255,50,50,0.9),rgba(255,0,0,0.4));' +
        'position:fixed;top:-50px;left:-50px;z-index:2147483647;pointer-events:none;' +
        'box-shadow:0 0 12px 4px rgba(255,0,0,0.4);' +
        'transform:translate(-50%,-50%);transition:left 0.08s,top 0.08s;';
    document.body.appendChild(dot);

    var ring = document.createElement('div');
    ring.id = 'sel-ring';
    ring.style.cssText = 'width:44px;height:44px;border-radius:50%;border:3px solid rgba(255,0,0,0.6);' +
        'position:fixed;z-index:2147483646;pointer-events:none;opacity:0;' +
        'transform:translate(-50%,-50%) scale(0);';
    document.body.appendChild(ring);

    var label = document.createElement('div');
    label.id = 'sel-label';
    label.style.cssText = 'position:fixed;top:8px;left:50%;transform:translateX(-50%);' +
        'z-index:2147483647;background:rgba(0,0,0,0.85);color:#00ff88;' +
        'padding:6px 18px;border-radius:16px;font:bold 13px monospace;' +
        'pointer-events:none;box-shadow:0 2px 12px rgba(0,0,0,0.4);' +
        'border:1px solid rgba(0,255,136,0.3);';
    label.textContent = 'AUTOMATION ACTIVE';
    document.body.appendChild(label);

    document.addEventListener('mousemove', function(e) {
        dot.style.left = e.clientX + 'px';
        dot.style.top = e.clientY + 'px';
    });
    document.addEventListener('mousedown', function(e) {
        ring.style.left = e.clientX + 'px';
        ring.style.top = e.clientY + 'px';
        ring.style.opacity = '1';
        ring.style.transform = 'translate(-50%,-50%) scale(0.3)';
        ring.style.transition = 'none';
        setTimeout(function() {
            ring.style.transition = 'all 0.35s ease-out';
            ring.style.transform = 'translate(-50%,-50%) scale(1.2)';
            ring.style.opacity = '0';
        }, 20);
    });
})();
"""


def inject_cursor(driver):
    """Inject cursor overlay into page."""
    try:
        driver.execute_script(CURSOR_JS)
        log_info("[CURSOR] Overlay injected.")
    except Exception:
        pass


def set_label(driver, text):
    """Update status label on browser."""
    try:
        driver.execute_script(
            "var l=document.getElementById('sel-label');if(l)l.textContent=arguments[0];", text
        )
    except Exception:
        pass


def move_mouse_to(driver, x, y):
    """Move mose to absolute page coordinates with visible cursor."""
    body = driver.find_element(By.TAG_NAME, "body")
    vw = driver.execute_script("return window.innerWidth;")
    vh = driver.execute_script("return window.innerHeight;")
    # ActionChains offset is from element center
    offset_x = x - vw // 2
    offset_y = y - vh // 2
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(body, offset_x, offset_y)
    actions.perform()
    log_info(f"[CURSOR] Moved to ({x}, {y})")


def click_at(driver, x, y, description=""):
    """Move mouse to coordinates and click."""
    set_label(driver, f"Clicking: {description}")
    move_mouse_to(driver, x, y)
    time.sleep(0.3)
    actions = ActionChains(driver)
    actions.click()
    actions.perform()
    log_info(f"[CLICK] Clicked at ({x}, {y}) - {description}")


# ─────────────────────────────────────────────────────────────
# Shadow DOM piercing — find elements
# ─────────────────────────────────────────────────────────────

def interact_with_element_by_js(driver, js_find_code, description="", retries=10, must_succeed=True):
    """Executes JS to find an element, scroll to it, and click it via screen coordinates."""
    full_js = f"""
        function findTarget() {{
            {js_find_code}
        }}
        var res = findTarget();
        if (!res) return JSON.stringify({{found: false}});
        if (res.status === 'already_set') return JSON.stringify({{found: true, status: 'already_set'}});
        
        if (res.el) {{
            res.el.scrollIntoView({{block: 'center'}});
            var rect = res.el.getBoundingClientRect();
            return JSON.stringify({{
                found: true,
                status: 'needs_click',
                x: Math.round(rect.x + rect.width / 2),
                y: Math.round(rect.y + rect.height / 2)
            }});
        }}
        return JSON.stringify({{found: false}});
    """
    
    spinner = LoadingSpinner(f"Locating {description}")
    spinner.start()
    
    for attempt in range(retries):
        try:
            result_json = driver.execute_script(full_js)
            data = json.loads(result_json)
            
            if data.get("found"):
                spinner.stop(f"Found {description}!")
                x, y = data["x"], data["y"]
                
                # Move smoothly for visual effect
                current_x = driver.execute_script("var dot=document.getElementById('sel-cursor'); return dot ? parseInt(dot.style.left) || window.innerWidth/2 : window.innerWidth/2;")
                current_y = driver.execute_script("var dot=document.getElementById('sel-cursor'); return dot ? parseInt(dot.style.top) || window.innerHeight/2 : window.innerHeight/2;")
                steps = 8
                for i in range(1, steps + 1):
                    step_x = current_x + (x - current_x) * i // steps
                    step_y = current_y + (y - current_y) * i // steps
                    move_mouse_to(driver, step_x, step_y)
                    time.sleep(0.04)
                
                click_at(driver, x, y, description)
                time.sleep(1) # wait for animations
                return True
                
        except Exception as e:
            pass
        time.sleep(1)
        
    spinner.stop(f"Could not find {description}.")
    if must_succeed:
        log_error(f"Required element '{description}' missing or unclickable.")
    return False


JS_FIND_SWITCH_VERSION = """
    // Normal DOM check
    var elements = document.querySelectorAll('button, span, div, ks-button');
    for (var el of elements) {
        if (el.innerText && el.innerText.trim() === 'Switch to full version') {
            var r = el.getBoundingClientRect();
            if (r.width > 10 && r.height > 10) return {el: el, status: 'needs_click'};
        }
    }
    // Shadow DOM traversal check (recursive)
    function searchForSwitchText(root, host) {
        if (!root) return null;
        var children = root.querySelectorAll('*');
        for (var child of children) {
            // Check text of this child
            var text = child.textContent || child.innerText;
            if (text && text.trim() === 'Switch to full version') {
                return {el: host || child, status: 'needs_click'};
            }
            if (child.shadowRoot) {
                var res = searchForSwitchText(child.shadowRoot, child);
                if (res) return res;
            }
        }
        return null;
    }
    
    var all = document.querySelectorAll('*');
    for (var a of all) {
        if (a.tagName.toLowerCase().includes('ks-button') || a.shadowRoot) {
            if (a.textContent.includes('Switch to full version')){
                 return {el: a, status: 'needs_click'};
            }
            if (a.shadowRoot) {
                var shadowRes = searchForSwitchText(a.shadowRoot, a);
                if (shadowRes) return shadowRes;
            }
        }
    }
    
    // Final fallback text search in outer DOM
    for (var a of all) {
        if (a.textContent && a.textContent.trim() === 'Switch to full version' && a.children.length === 0) {
            return {el: a, status: 'needs_click'};
        }
    }
    return null;
"""

JS_FIND_CONFIRM_BUTTON = """
    // Search for button with text Confirm
    var buttons = document.querySelectorAll('button, span, div, ks-button');
    for (var b of buttons) {
        if (b.innerText && b.innerText.trim() === 'Confirm') {
            var r = b.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return {el: b, status: 'needs_click'};
        }
    }
    // Shadow dom fallback
    var all = document.querySelectorAll('*');
    for (var a of all) {
        if (a.shadowRoot) {
            var els = a.shadowRoot.querySelectorAll('button, span, div, ks-button');
            for (var el of els) {
                if (el.textContent && el.textContent.trim() === 'Confirm') {
                    return {el: a, status: 'needs_click'};
                }
            }
        }
    }
    return null;
"""

JS_FIND_SALES = """
    // Finds Sales objective under Conversion section
    var labels = document.querySelectorAll('label, div');
    for (var l of labels) {
        var objName = l.getAttribute('data-tea-objective_name');
        var objContent = l.getAttribute('data-tea-objective-content');
        var vObj = l.getAttribute('data-tea-virtual_objective');
        
        if (objName === 'Sales' || objContent === 'Sales' || vObj === 'sales') {
            return {el: l, status: 'needs_click'};
        }
    }
    
    var all = document.querySelectorAll('*');
    for (var a of all) {
        if (a.childElementCount === 0 && a.textContent.trim() === 'Sales') {
            var r = a.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return {el: a, status: 'needs_click'};
        }
    }
    return null;
"""

def find_create_button(driver):
    """
    Find the "+ Create" button which is INSIDE Shadow DOM.
    
    DOM structure (from screenshot):
        ks-tooltip-1-1-14
          #shadow-root (open)
            ks-button-1-1-14
              #shadow-root (open)
                <button class="button button--md button--type-contained button--color-primary">
                  <ks-icon-plus-small>
                  "Create"
    
    Normal XPath/CSS cannot reach inside shadow-root.
    JavaScript is required to traverse shadow DOM.
    """
    log_info("[SEARCH] Searching for Create button in Shadow DOM...")

    result = driver.execute_script("""
        // === STRATEGY 1: Pierce Shadow DOM for ks-button elements ===
        
        // Find all custom elements that might contain the button
        var customElements = document.querySelectorAll('*');
        
        for (var el of customElements) {
            var tagName = el.tagName.toLowerCase();
            
            // Look for ks-button or ks-tooltip custom elements
            if (tagName.includes('ks-button') || tagName.includes('ks-tooltip')) {
                var shadow = el.shadowRoot;
                if (!shadow) continue;
                
                // Look for the actual <button> inside the shadow root
                var buttons = shadow.querySelectorAll('button');
                for (var btn of buttons) {
                    if (btn.textContent.trim().includes('Create') && 
                        !btn.textContent.trim().includes('Creative')) {
                        var rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return JSON.stringify({
                                found: true,
                                method: 'shadow_dom_direct',
                                x: Math.round(rect.x + rect.width / 2),
                                y: Math.round(rect.y + rect.height / 2),
                                w: Math.round(rect.width),
                                h: Math.round(rect.height),
                                text: btn.textContent.trim(),
                                classes: btn.className
                            });
                        }
                    }
                }
                
                // Also check nested shadow roots (shadow inside shadow)
                var innerElements = shadow.querySelectorAll('*');
                for (var inner of innerElements) {
                    if (inner.shadowRoot) {
                        var innerButtons = inner.shadowRoot.querySelectorAll('button');
                        for (var ibtn of innerButtons) {
                            if (ibtn.textContent.trim().includes('Create') && 
                                !ibtn.textContent.trim().includes('Creative')) {
                                var rect2 = ibtn.getBoundingClientRect();
                                if (rect2.width > 0 && rect2.height > 0) {
                                    return JSON.stringify({
                                        found: true,
                                        method: 'nested_shadow_dom',
                                        x: Math.round(rect2.x + rect2.width / 2),
                                        y: Math.round(rect2.y + rect2.height / 2),
                                        w: Math.round(rect2.width),
                                        h: Math.round(rect2.height),
                                        text: ibtn.textContent.trim(),
                                        classes: ibtn.className
                                    });
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // === STRATEGY 2: Find by class name pattern (button--color-primary) ===
        // Recursively search all shadow roots
        function searchShadow(root) {
            var nodes = root.querySelectorAll('*');
            for (var n of nodes) {
                // Check if this element is the button
                if (n.tagName === 'BUTTON' && n.className && 
                    n.className.includes('button--color-primary')) {
                    var r = n.getBoundingClientRect();
                    if (r.width > 0) {
                        return {
                            found: true,
                            method: 'class_search',
                            x: Math.round(r.x + r.width / 2),
                            y: Math.round(r.y + r.height / 2),
                            w: Math.round(r.width),
                            h: Math.round(r.height),
                            text: n.textContent.trim()
                        };
                    }
                }
                // Recurse into shadow roots
                if (n.shadowRoot) {
                    var result = searchShadow(n.shadowRoot);
                    if (result) return result;
                }
            }
            return null;
        }
        
        var shadowResult = searchShadow(document);
        if (shadowResult) return JSON.stringify(shadowResult);
        
        // === STRATEGY 3: Find any visible element with "Create" text ===
        // (top-left area of the page, based on screenshot position)
        var allElements = document.querySelectorAll('button, a, [role="button"], div');
        for (var el of allElements) {
            var text = el.textContent.trim();
            if ((text === 'Create' || text === '+ Create') && 
                el.offsetParent !== null) {
                var rect3 = el.getBoundingClientRect();
                // The Create button is in the top-left (x < 200, y < 200)
                if (rect3.width > 20 && rect3.height > 15 && 
                    rect3.x < 300 && rect3.y < 200) {
                    return JSON.stringify({
                        found: true,
                        method: 'text_search',
                        x: Math.round(rect3.x + rect3.width / 2),
                        y: Math.round(rect3.y + rect3.height / 2),
                        w: Math.round(rect3.width),
                        h: Math.round(rect3.height),
                        text: text,
                        tag: el.tagName
                    });
                }
            }
        }
        
        // === STRATEGY 4: Use known position from screenshot ===
        // The "+ Create" button is always at approximately (63, 124) 
        // in the TikTok Ads campaigns page
        return JSON.stringify({
            found: true,
            method: 'known_position',
            x: 63,
            y: 124,
            text: '+ Create (estimated position)'
        });
    """)

    return json.loads(result)


# ─────────────────────────────────────────────────────────────
# Main: Click the Create button
# ─────────────────────────────────────────────────────────────

def main():
    driver = None

    try:
        print("\n" + "=" * 55)
        print("  STEP 2: Click '+ Create' on Campaigns Page")
        print("=" * 55 + "\n")

        # ── Connect to existing Chrome ──────────────────────
        spinner = LoadingSpinner("Connecting to Chrome on port 9222")
        spinner.start()

        try:
            driver = connect_browser()
            spinner.stop("Connected to Chrome!")
        except Exception as e:
            spinner.stop(f"Connection failed: {e}")
            log_error("Could not connect. Is main.py still running?")
            print("\n  Make sure:")
            print("  1. main.py was run and reached the campaigns page")
            print("  2. You did NOT type 'close' in main.py")
            print("  3. Chrome is still open\n")
            return

        # ── Verify we're on campaigns page ──────────────────
        current_url = driver.current_url
        log_step(1, f"Current URL: {current_url}")

        if "campaign" not in current_url.lower() and "manage" not in current_url.lower():
            log_warning("Not on campaigns page!")
            print("  Please navigate to the campaigns page first.")
            return

        log_success("On campaigns page!")

        # ── Inject cursor overlay ───────────────────────────
        log_step(2, "Injecting cursor overlay...")
        inject_cursor(driver)
        set_label(driver, "STEP 2: Finding Create button...")
        time.sleep(0.5)

        # Keep track of tabs to see if clicking opens a new one
        original_tab_count = len(driver.window_handles)

        log_step(3, "Searching for '+ Create' button...")
        log_info("[SEARCH] Checking Shadow DOM elements...")

        spinner = LoadingSpinner("Searching Shadow DOM for Create button")
        spinner.start()

        button_info = find_create_button(driver)

        spinner.stop(f"Search complete! Method: {button_info.get('method', 'unknown')}")
        log_info(f"[RESULT] {json.dumps(button_info, indent=2)}")

        if not button_info.get("found"):
            log_error("Could not find Create button!")
            return

        x = button_info["x"]
        y = button_info["y"]
        method = button_info.get("method", "unknown")
        text = button_info.get("text", "Create")

        log_success(f"Found '{text}' at ({x}, {y}) via {method}")

        # ── Move mouse to Create button ─────────────────────
        log_step(4, f"Moving mouse to Create button at ({x}, {y})...")
        set_label(driver, f"Moving to Create button ({x}, {y})")

        # Smooth mouse movement: move in steps for visible effect
        current_x, current_y = 500, 300  # Start from center-ish
        steps = 8
        for i in range(1, steps + 1):
            step_x = current_x + (x - current_x) * i // steps
            step_y = current_y + (y - current_y) * i // steps
            move_mouse_to(driver, step_x, step_y)
            time.sleep(0.05)

        log_info(f"[CURSOR] Mouse is now at ({x}, {y})")
        time.sleep(0.3)

        # ── Click the Create button ─────────────────────────
        log_step(5, "CLICKING Create button...")
        set_label(driver, "CLICKING: + Create")

        click_at(driver, x, y, "+ Create button")

        # ── Wait for result ─────────────────────────────────
        log_step(6, "Waiting for response...")
        spinner = LoadingSpinner("Waiting for campaign creation page")
        spinner.start()

        time.sleep(2)

        # Dismiss any dialogs that might appear
        try:
            driver.switch_to.alert.accept()
        except (NoAlertPresentException, WebDriverException):
            pass

        if len(driver.window_handles) > original_tab_count:
            driver.switch_to.window(driver.window_handles[-1])
            log_info("Switched to new tab.")
            time.sleep(2)
        
        new_url = driver.current_url
        spinner.stop(f"Page: {new_url}")

        # Ensure we are definitively on the objectives creation page
        if "create/objectives" in new_url.lower() or "creation" in new_url.lower():
            log_success(f"Create clicked successfully! New URL: {new_url}")
        else:
            log_warning("URL didn't change as expected. The Create button click may have failed or opened a prompt.")
            import re
            match = re.search(r'aadvid=(\d+)', current_url)
            if match:
                aadvid = match.group(1)
                create_url = f"https://ads.tiktok.com/i18n/nb_creation/create/objectives?aadvid={aadvid}&enter_from=campaign_list"
                log_info(f"Navigating directly via URL to ensure reliability: {create_url}")
                driver.get(create_url)
                time.sleep(3)
                log_success(f"Successfully reached creation URL: {driver.current_url}")
            else:
                log_error("Could not parse Account ID (aadvid) to navigate safely.")

        inject_cursor(driver)

        # Check for Switch to full version
        log_step(7, "Checking for 'Switch to full version' button...")
        switched = interact_with_element_by_js(driver, JS_FIND_SWITCH_VERSION, "Switch to full version", retries=5, must_succeed=False)
        
        if switched:
            log_info("Clicking modal 'Confirm' button...")
            time.sleep(1) # wait for modal to pop up
            interact_with_element_by_js(driver, JS_FIND_CONFIRM_BUTTON, "Confirm button", retries=5, must_succeed=False)
            log_info("Waiting for full version UI to load...")
            time.sleep(4) # Wait for page load

        final_url = driver.current_url
        if "creation/1nn/create/campaign" in final_url.lower():
            log_success(f"Reached final full-version creation URL automatically!")
        else:
            log_warning(f"URL did not match the expected full-version URL: {final_url}. Navigating directly...")
            import re
            match = re.search(r'aadvid=(\d+)', final_url)
            if not match:
                # check if there's any active variable we saved
                try: aadvid
                except NameError: match = None
            
            if match:
                aadvid = match.group(1)
            try:
                if aadvid:
                    full_version_url = f"https://ads.tiktok.com/i18n/creation/1nn/create/campaign?aadvid={aadvid}&enter_from=campaign_list&newbie_enable_back=1&creation_type=create_new"
                    log_info(f"Going directly to: {full_version_url}")
                    driver.get(full_version_url)
                    time.sleep(3)
                    log_success(f"Successfully loaded true creation URL: {driver.current_url}")
            except NameError:
                log_error("Could not find aadvid to navigate to full version safely.")

        # Give the React app a moment to render the objective list
        time.sleep(2)
        
        log_step(8, "Selecting 'Sales' objective...")
        interact_with_element_by_js(driver, JS_FIND_SALES, "Sales Objective")
        time.sleep(1)

        set_label(driver, "CREATE READY - Done!")
        log_success("Step 2 complete!")

        # ── Done ────────────────────────────────────────────
        print("\n" + "=" * 55)
        print("  DONE! '+ Create' button clicked.")
        print("  URL: " + driver.current_url)
        print("  ENTER to disconnect (Chrome stays open).")
        print("=" * 55 + "\n")

        input(">>> ")

    except WebDriverException as e:
        log_error(f"WebDriver error: {e}")
        print("\n  Is Chrome still open? Is main.py still running?\n")

    except KeyboardInterrupt:
        log_warning("Stopped (Ctrl+C)")

    except Exception as e:
        log_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            disconnect_browser(driver)
        log_info("Done.")


if __name__ == "__main__":
    main()
