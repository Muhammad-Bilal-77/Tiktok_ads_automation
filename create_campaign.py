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

import re
import time
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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

                # ── already_set: JS click already worked, nothing more to do ──
                if data.get("status") == "already_set":
                    log_success(f"[JS-CLICK] '{description}' was set directly by JavaScript.")
                    return True

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

JS_FIND_WEBSITE_RADIO = """
    // Finds the Website sales-destination radio label.
    // data-testid is deliberately NOT used — it was mapping to TikTok Shop (wrong element).
    // Priority order ensures we never match TikTok Shop or Website and app.

    function findWebsiteLabel() {
        // P1: data-tea-sales_destination="website" — most semantically accurate
        var el = document.querySelector('label[data-tea-sales_destination="website"]');
        if (el && el.getBoundingClientRect().width > 0) return el;

        // P2: exact span text "Website" inside a radio label (not "Website and app")
        var spans = document.querySelectorAll('label[role="radio"] span');
        for (var i = 0; i < spans.length; i++) {
            if (spans[i].childElementCount === 0 && spans[i].textContent.trim() === 'Website') {
                var lbl = spans[i].closest('label[role="radio"]') || spans[i].closest('label');
                if (lbl && lbl.getBoundingClientRect().width > 0) return lbl;
            }
        }

        // P3: combined data-tea-objective_type="3" + data-tea-objective_name="Sales"
        el = document.querySelector('label[data-tea-objective_type="3"][data-tea-objective_name="Sales"]');
        if (el && el.getBoundingClientRect().width > 0) return el;

        return null;
    }

    var label = findWebsiteLabel();
    if (!label) return null;
    var rect = label.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;

    // Already checked?
    if (label.getAttribute('aria-checked') === 'true' || label.classList.contains('is-checked')) {
        return {el: label, status: 'already_set'};
    }

    // JS click on the 16x16 inner dot (Vue's real event target)
    var innerDot = label.querySelector('span.vi-radio__inner');
    if (innerDot) { innerDot.click(); } else { label.click(); }
    // Return the inner dot coords for ActionChains fallback
    var clickEl = innerDot || label;
    clickEl.scrollIntoView({block: 'center'});
    var cr = clickEl.getBoundingClientRect();
    return {
        el: clickEl,
        status: 'needs_click',
        x: Math.round(cr.x + cr.width / 2),
        y: Math.round(cr.y + cr.height / 2)
    };
"""


JS_FIND_SET_BUDGET = """
    // Finds the "Set campaign budget" toggle (vi-switch).
    // Target: data-tea="create_campaign_budget_checkbox" or
    //         a vi-switch near a label/span with text "Set campaign budget".

    // P1: exact data-tea attribute (most reliable)
    var sw = document.querySelector('[data-tea="create_campaign_budget_checkbox"]');
    if (!sw) {
        // P2: any vi-switch near text "Set campaign budget"
        var allSwitch = document.querySelectorAll('[role="switch"]');
        for (var i = 0; i < allSwitch.length; i++) {
            var parent = allSwitch[i].closest('div') || allSwitch[i].parentElement;
            var txt = parent ? (parent.textContent || '') : '';
            if (txt.includes('Set campaign budget')) { sw = allSwitch[i]; break; }
        }
    }
    if (!sw) return null;

    // Already ON?
    if (sw.getAttribute('aria-checked') === 'true') {
        return {el: sw, status: 'already_set'};
    }

    // Click the visual core span (40x22 pill)
    var core = sw.querySelector('span.vi-switch__core') || sw;
    core.scrollIntoView({block: 'center'});
    var r = core.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    return {
        el: core,
        status: 'needs_click',
        x: Math.round(r.x + r.width / 2),
        y: Math.round(r.y + r.height / 2)
    };
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

        # ── Extract aadvid NOW (before any navigation happens) ──────────────
        _m = re.search(r'aadvid=(\d+)', current_url)
        aadvid = _m.group(1) if _m else None
        if aadvid:
            log_success(f"[AADVID] Captured account ID early: {aadvid}")
        else:
            log_warning("[AADVID] Could not find aadvid in campaigns URL — fallback navigation may not work.")

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
            log_warning("URL didn't change as expected — navigating directly using stored aadvid.")
            if aadvid:
                create_url = f"https://ads.tiktok.com/i18n/nb_creation/create/objectives?aadvid={aadvid}&enter_from=campaign_list"
                log_info(f"Navigating directly via URL: {create_url}")
                driver.get(create_url)
                time.sleep(3)
                log_success(f"Reached creation URL: {driver.current_url}")
            else:
                log_error("No aadvid available — cannot navigate to creation page.")
                return

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
            log_success(f"Reached full-version creation URL automatically!")
        else:
            log_warning(f"Not on full-version URL ({final_url}). Navigating directly...")
            if aadvid:
                full_version_url = (
                    f"https://ads.tiktok.com/i18n/creation/1nn/create/campaign"
                    f"?aadvid={aadvid}&enter_from=campaign_list"
                    f"&newbie_enable_back=1&creation_type=create_new"
                )
                log_info(f"Navigating to: {full_version_url}")
                driver.get(full_version_url)
                # Poll until the campaign creation page has loaded (up to 15 s)
                for _ in range(15):
                    time.sleep(1)
                    if "creation/1nn/create/campaign" in driver.current_url.lower():
                        break
                log_success(f"Loaded: {driver.current_url}")
            else:
                log_error("No aadvid — cannot navigate to full-version URL.")
                return

        # Give the React app a moment to render the objective list
        time.sleep(2)
        
        log_step(8, "Selecting 'Sales' objective...")
        inject_cursor(driver)
        sales_clicked = interact_with_element_by_js(
            driver, JS_FIND_SALES, "Sales Objective", retries=15, must_succeed=True
        )
        if not sales_clicked:
            log_error("Could not select 'Sales' — cannot proceed to Website radio.")
            return

        # Poll for the Website radio to appear in the DOM (TikTok renders it async)
        log_step(9, "Waiting for 'Website' radio button to appear in DOM...")
        set_label(driver, "STEP 9: Waiting for Website radio...")
        website_appeared = False
        for _wait in range(20):          # up to 20 s
            time.sleep(1)
            check = driver.execute_script("""
                var el = document.querySelector('[data-testid="sales-destination-index-6AFaYw"]') ||
                         document.querySelector('label[data-tea-sales_destination="website"]');
                if (el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                var labels = document.querySelectorAll('label[role="radio"]');
                for (var i = 0; i < labels.length; i++) {
                    var t = labels[i].textContent || '';
                    if (t.includes('Website') && !t.includes('Website and app')) {
                        var r2 = labels[i].getBoundingClientRect();
                        return r2.width > 0 && r2.height > 0;
                    }
                }
                return false;
            """)
            if check:
                log_success(f"Website radio appeared after {_wait + 1}s.")
                website_appeared = True
                break

        if not website_appeared:
            log_error("Website radio never appeared — Sales submenu may not have opened.")
        else:
            log_step(9, "Clicking 'Website' radio (triple-attempt)...")
            set_label(driver, "STEP 9: Clicking Website radio...")
            website_done = False

            for _attempt in range(8):
                # ── Attempt A: JS click on innerDot ────────────────────────
                result_a = driver.execute_script("""
                    function findWebsiteLabel() {
                        // P1: semantic attribute (most reliable)
                        var el = document.querySelector('label[data-tea-sales_destination="website"]');
                        if (el && el.getBoundingClientRect().width > 0) return el;
                        // P2: exact span text "Website" inside a radio label
                        var spans = document.querySelectorAll('label[role="radio"] span');
                        for (var i = 0; i < spans.length; i++) {
                            if (spans[i].childElementCount === 0 && spans[i].textContent.trim() === 'Website') {
                                var lbl = spans[i].closest('label[role="radio"]') || spans[i].closest('label');
                                if (lbl && lbl.getBoundingClientRect().width > 0) return lbl;
                            }
                        }
                        // P3: objective_type=3 + Sales on a label
                        el = document.querySelector('label[data-tea-objective_type="3"][data-tea-objective_name="Sales"]');
                        if (el && el.getBoundingClientRect().width > 0) return el;
                        return null;
                    }
                    var lbl = findWebsiteLabel();
                    if (!lbl) return null;
                    lbl.scrollIntoView({block: 'center'});
                    var dot = lbl.querySelector('span.vi-radio__inner') || lbl;
                    dot.click();
                    lbl.click();
                    var r = dot.getBoundingClientRect();
                    return {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
                """)

                time.sleep(1.2)
                if "objective_type=3" in driver.current_url:
                    log_success(f"[ATTEMPT A] Website selected! URL: {driver.current_url}")
                    website_done = True
                    break

                # ── Attempt B: ActionChains physical click on innerDot coords
                if result_a and "x" in result_a:
                    cx, cy = result_a["x"], result_a["y"]
                    log_info(f"[ATTEMPT B] ActionChains click at ({cx}, {cy})")
                    move_mouse_to(driver, cx, cy)
                    time.sleep(0.3)
                    ActionChains(driver).click().perform()
                    time.sleep(1.2)
                    if "objective_type=3" in driver.current_url:
                        log_success(f"[ATTEMPT B] Website selected! URL: {driver.current_url}")
                        website_done = True
                        break

                # ── Attempt C: dispatchEvent (MouseEvent) ───────────────────
                driver.execute_script("""
                    function findWebsiteLabel() {
                        var el = document.querySelector('label[data-tea-sales_destination="website"]');
                        if (el && el.getBoundingClientRect().width > 0) return el;
                        var spans = document.querySelectorAll('label[role="radio"] span');
                        for (var i = 0; i < spans.length; i++) {
                            if (spans[i].childElementCount === 0 && spans[i].textContent.trim() === 'Website') {
                                var lbl = spans[i].closest('label[role="radio"]') || spans[i].closest('label');
                                if (lbl && lbl.getBoundingClientRect().width > 0) return lbl;
                            }
                        }
                        el = document.querySelector('label[data-tea-objective_type="3"][data-tea-objective_name="Sales"]');
                        if (el && el.getBoundingClientRect().width > 0) return el;
                        return null;
                    }
                    var lbl = findWebsiteLabel();
                    if (!lbl) return;
                    var dot = lbl.querySelector('span.vi-radio__inner') || lbl;
                    ['mousedown','mouseup','click'].forEach(function(evtType) {
                        dot.dispatchEvent(new MouseEvent(evtType, {bubbles:true, cancelable:true, view:window}));
                    });
                    ['mousedown','mouseup','click'].forEach(function(evtType) {
                        lbl.dispatchEvent(new MouseEvent(evtType, {bubbles:true, cancelable:true, view:window}));
                    });
                """)
                time.sleep(1.2)
                if "objective_type=3" in driver.current_url:
                    log_success(f"[ATTEMPT C] Website selected! URL: {driver.current_url}")
                    website_done = True
                    break

                time.sleep(0.5)

            if not website_done:
                log_error("All 8 attempts to click Website radio failed.")
            else:
                log_success(f"'Website' selected. Final URL: {driver.current_url}")

        time.sleep(1)

        # ── STEP 10: Click 'Set campaign budget' toggle ─────────────────
        log_step(10, "Scrolling to 'Set campaign budget' toggle and turning it ON...")
        set_label(driver, "STEP 10: Enabling Set campaign budget...")

        # Scroll to very bottom first so Settings section is rendered
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.5)

        budget_toggled = False

        for _attempt in range(6):
            # ── Single JS call: find switch, check state, return coords ──
            info = driver.execute_script("""
                // Find the vi-switch for "Set campaign budget"
                var sw = document.querySelector('[data-tea="create_campaign_budget_checkbox"]');
                if (!sw) {
                    // Fallback: look for any [role=switch] near the text
                    var switches = document.querySelectorAll('[role="switch"]');
                    for (var i = 0; i < switches.length; i++) {
                        var region = switches[i].closest('div.switch-container') ||
                                     switches[i].closest('div') ||
                                     switches[i].parentElement;
                        if (region && region.textContent.includes('Set campaign budget')) {
                            sw = switches[i];
                            break;
                        }
                    }
                }

                if (!sw) return {found: false};

                // Scroll the switch into view INSTANTLY (not smooth — smooth is async,
                // getBoundingClientRect would read pre-scroll coordinates)
                sw.scrollIntoView({block: 'center', behavior: 'instant'});

                // Determine ON/OFF: vi-switch uses is-checked class or input.checked
                var inp = sw.querySelector('input[type="checkbox"]');
                var isOn = sw.classList.contains('is-checked') ||
                           (inp != null && inp.checked) ||
                           sw.getAttribute('data-tea-campaign_budget_status') === 'true';

                // Return the coordinates of the core pill for ActionChains click
                var core = sw.querySelector('span.vi-switch__core') || sw;
                var r = core.getBoundingClientRect();
                return {
                    found: true,
                    on:    isOn,
                    x:     Math.round(r.left + r.width  / 2),
                    y:     Math.round(r.top  + r.height / 2)
                };
            """)

            if not info or not info.get("found"):
                log_info(f"[BUDGET] Switch not found in DOM (attempt {_attempt+1}), retrying in 2s...")
                time.sleep(2)
                continue

            if info.get("on"):
                log_success("[BUDGET] Toggle is already ON — done.")
                budget_toggled = True
                break

            # ── Toggle is OFF → one physical click via ActionChains ──────
            cx = info["x"]
            cy = info["y"]
            log_info(f"[BUDGET] Toggle is OFF. Physical click at ({cx}, {cy}) attempt {_attempt+1}...")
            move_mouse_to(driver, cx, cy)
            time.sleep(0.5)
            ActionChains(driver).click().perform()

            # Wait for Vue to update its reactive state
            time.sleep(2.5)

            # Re-check state (separate JS call)
            is_now_on = driver.execute_script("""
                var sw = document.querySelector('[data-tea="create_campaign_budget_checkbox"]');
                if (!sw) return false;
                var inp = sw.querySelector('input[type="checkbox"]');
                return sw.classList.contains('is-checked') ||
                       (inp != null && inp.checked) ||
                       sw.getAttribute('data-tea-campaign_budget_status') === 'true';
            """)

            if is_now_on:
                log_success(f"[BUDGET] Toggle is ON after click at ({cx}, {cy}).")
                budget_toggled = True
                break

            log_info(f"[BUDGET] Still OFF after attempt {_attempt+1}.")

        if not budget_toggled:
            log_error("Could not enable 'Set campaign budget' toggle — continuing.")
        else:
            log_success("'Set campaign budget' is ON!")

        # ── STEP 11: Type 1000 in the campaign budget input ─────────────
        # Exact DOM path from DevTools:
        #   x-input-number-*[class*="budgetInput"]   ← light DOM, findable
        #     └─ #shadow-root
        #         └─ x-input-*                       ← inner host
        #             └─ #shadow-root
        #                 └─ input[type="text"]      ← REAL INPUT
        log_step(11, "Setting campaign budget to 1000...")
        set_label(driver, "STEP 11: Typing budget 1000...")

        # Scroll to bottom first to ensure budget section is rendered
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        budget_input_done = False

        for _bi in range(6):
            # ── Find the custom element that HAS a shadowRoot + budget context ──
            coords = driver.execute_script("""
                // Scan ALL elements — find one with .shadowRoot whose class/tag/ancestor
                // indicates it's the budget amount input host.
                var outerHost = null;
                var allEls = document.querySelectorAll('*');

                // Pass 1: tag starts with x-input-number AND has shadowRoot
                for (var i = 0; i < allEls.length; i++) {
                    var el = allEls[i];
                    if (!el.shadowRoot) continue;
                    var tag = el.tagName.toLowerCase();
                    if (tag.startsWith('x-input-number')) {
                        // Confirm it's near the budget section
                        var par = el.parentElement;
                        var parText = par ? (par.textContent || '') : '';
                        var cls = (el.className || '').toLowerCase();
                        if (parText.includes('USD') || cls.includes('budget') ||
                            parText.toLowerCase().includes('budget')) {
                            outerHost = el; break;
                        }
                    }
                }

                // Pass 2: any element with shadowRoot and 'budget' in class
                if (!outerHost) {
                    for (var j = 0; j < allEls.length; j++) {
                        if (!allEls[j].shadowRoot) continue;
                        var cls2 = (allEls[j].className || '').toLowerCase();
                        if (cls2.includes('budget')) { outerHost = allEls[j]; break; }
                    }
                }

                // Pass 3: any x-input-number-* with shadowRoot (no text check)
                if (!outerHost) {
                    for (var k = 0; k < allEls.length; k++) {
                        if (!allEls[k].shadowRoot) continue;
                        if (allEls[k].tagName.toLowerCase().startsWith('x-input-number')) {
                            outerHost = allEls[k]; break;
                        }
                    }
                }

                if (!outerHost) return {err: 'outer host with shadowRoot not found'};

                // Pierce shadow root 1 — find inner x-input host
                var sr1 = outerHost.shadowRoot;
                var innerHost = null;
                var sr1All = sr1.querySelectorAll('*');
                for (var m = 0; m < sr1All.length; m++) {
                    if (sr1All[m].shadowRoot) { innerHost = sr1All[m]; break; }
                }
                if (!innerHost) return {err: 'inner host not found in sr1'};

                // Pierce shadow root 2 — find the actual <input>
                var sr2 = innerHost.shadowRoot;
                var inp = sr2.querySelector('input[type="text"]') ||
                          sr2.querySelector('input[type="number"]') ||
                          sr2.querySelector('input');
                if (!inp) return {err: 'input not found in sr2'};

                // Scroll the OUTER light-DOM element (not the shadow input)
                outerHost.scrollIntoView({block: 'center', behavior: 'instant'});

                var r = inp.getBoundingClientRect();
                if (r.width === 0) return {err: 'input has zero width (not rendered yet)'};

                return {
                    x:   Math.round(r.left + r.width  / 2),
                    y:   Math.round(r.top  + r.height / 2),
                    val: inp.value,
                    ph:  inp.placeholder,
                    w:   Math.round(r.width),
                    h:   Math.round(r.height)
                };
            """)

            if not coords or coords.get("err"):
                err = coords.get("err", "null") if coords else "null"
                log_info(f"[BUDGET-INPUT] Not ready (attempt {_bi+1}): {err} — retrying in 2s...")
                time.sleep(2)
                continue

            cx, cy = coords["x"], coords["y"]
            log_info(f"[BUDGET-INPUT] Input at ({cx},{cy}) {coords['w']}×{coords['h']} "
                     f"ph='{coords.get('ph','')}' val='{coords.get('val','')}'")

            # Safety: reject coordinates that are off-screen
            if cy < 0 or cy > 900 or cx < 0:
                log_info(f"[BUDGET-INPUT] Coords look off-screen, scrolling and retrying...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                continue

            # ── Click the input and type ──────────────────────────────────
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.3)
            move_mouse_to(driver, cx, cy)
            time.sleep(0.4)
            ActionChains(driver).click().perform()
            time.sleep(0.4)

            # Clear + type
            ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            time.sleep(0.2)
            ActionChains(driver).send_keys(Keys.DELETE).perform()
            time.sleep(0.2)
            ActionChains(driver).send_keys("1000").perform()
            time.sleep(0.5)

            # ── Force value via native setter + fire composed events ───────
            driver.execute_script("""
                var outerHost = null;
                var allE = document.querySelectorAll('*');
                for (var i = 0; i < allE.length; i++) {
                    if (!allE[i].shadowRoot) continue;
                    var t = allE[i].tagName.toLowerCase();
                    var c = (allE[i].className||'').toLowerCase();
                    if (t.startsWith('x-input-number') || c.includes('budget')) {
                        outerHost = allE[i]; break;
                    }
                }
                if (!outerHost) return;

                var innerHost = null;
                var sr1A = outerHost.shadowRoot.querySelectorAll('*');
                for (var j = 0; j < sr1A.length; j++) {
                    if (sr1A[j].shadowRoot) { innerHost = sr1A[j]; break; }
                }
                if (!innerHost || !innerHost.shadowRoot) return;

                var inp = innerHost.shadowRoot.querySelector('input[type="text"]') ||
                          innerHost.shadowRoot.querySelector('input');
                if (!inp) return;

                var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
                setter.call(inp, '1000');
                inp.dispatchEvent(new InputEvent('input',  {bubbles:true, composed:true, data:'1000'}));
                inp.dispatchEvent(new Event('change', {bubbles:true, composed:true}));
            """)
            time.sleep(0.6)

            # ── Verify ────────────────────────────────────────────────────
            actual = driver.execute_script("""
                var outerHost2 = null;
                var allV = document.querySelectorAll('*');
                for (var i = 0; i < allV.length; i++) {
                    if (!allV[i].shadowRoot) continue;
                    var t2 = allV[i].tagName.toLowerCase();
                    var c2 = (allV[i].className||'').toLowerCase();
                    if (t2.startsWith('x-input-number') || c2.includes('budget')) {
                        outerHost2 = allV[i]; break;
                    }
                }
                if (!outerHost2) return null;
                var innerH = null;
                var sr1V = outerHost2.shadowRoot.querySelectorAll('*');
                for (var j = 0; j < sr1V.length; j++) {
                    if (sr1V[j].shadowRoot) { innerH = sr1V[j]; break; }
                }
                if (!innerH || !innerH.shadowRoot) return null;
                var inp2 = innerH.shadowRoot.querySelector('input');
                return inp2 ? inp2.value : null;
            """)
            log_info(f"[BUDGET-INPUT] Value after typing: '{actual}'")

            if actual and "1000" in str(actual).replace(",", ""):
                log_success(f"[BUDGET-INPUT] Budget = '{actual}' ✓")
                budget_input_done = True
                break

            log_info(f"[BUDGET-INPUT] Mismatch on attempt {_bi+1}, retrying...")
            time.sleep(1)

        if not budget_input_done:
            log_error("Could not set budget to 1000 — continuing.")
        else:
            log_success("Campaign budget = 1000.")

        # ── Click Continue button ────────────────────────────────────────────
        log_info("[CONTINUE] Looking for Continue button...")
        time.sleep(1.5)

        continue_clicked = False
        for _ct in range(5):
            try:
                # Try direct querySelector by data-testid (light DOM)
                btn = driver.execute_script("""
                    return document.querySelector('ks-button-91g[data-testid="common_next_button"]')
                        || document.querySelector('[data-testid="common_next_button"]');
                """)
                if btn:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.4)
                    driver.execute_script("arguments[0].click();", btn)
                    log_success("[CONTINUE] Clicked Continue via JS!")
                    continue_clicked = True
                    break
                else:
                    # Fallback: scan all ks-button-91g elements for text "Continue"
                    btn2 = driver.execute_script("""
                        var btns = document.querySelectorAll('ks-button-91g');
                        for (var i = 0; i < btns.length; i++) {
                            if ((btns[i].innerText || '').trim() === 'Continue') return btns[i];
                        }
                        return null;
                    """)
                    if btn2:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn2)
                        time.sleep(0.4)
                        driver.execute_script("arguments[0].click();", btn2)
                        log_success("[CONTINUE] Clicked Continue via text-scan fallback!")
                        continue_clicked = True
                        break
                    log_info(f"[CONTINUE] Button not found on attempt {_ct+1}, retrying...")
                    time.sleep(1)
            except Exception as ce:
                log_error(f"[CONTINUE] Error on attempt {_ct+1}: {ce}")
                time.sleep(1)

        if not continue_clicked:
            log_error("[CONTINUE] Could not find/click Continue button.")
        else:
            time.sleep(2)
            log_success(f"[CONTINUE] URL after click: {driver.current_url}")

        # ── Scroll to Budget & Schedule → click Timezone dropdown ──────────
        log_info("[TIMEZONE] Waiting for Ad Group page to render...")
        time.sleep(3)

        # Scroll down to the Budget & Schedule section
        log_info("[TIMEZONE] Scrolling to Budget & Schedule section...")
        driver.execute_script("""
            // Try to find the budget/schedule section header by text
            var allEls = document.querySelectorAll('*');
            for (var i = 0; i < allEls.length; i++) {
                var el = allEls[i];
                var txt = (el.innerText || el.textContent || '').trim();
                if (txt === 'Budget & schedule' || txt === 'Budget & Schedule') {
                    el.scrollIntoView({block: 'center', behavior: 'smooth'});
                    break;
                }
            }
        """)
        time.sleep(1.5)

        # Also do a raw page scroll down to make sure the section is visible
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(1)

        # ── Fill Ad Group Budget input with 100 ──────────────────────────────
        log_info("[ADGROUP BUDGET] Looking for budget input above Time zone...")
        budget_filled = False
        for _ab in range(5):
            try:
                budget_inp = driver.execute_script("""
                    // The budget input is inside a Web Component with shadow DOM
                    // Wrapper: class contains 'input_wrapper'
                    // Inner: <input part="input" class="input" type="text">
                    // Strategy 1: find via shadow roots
                    function findInShadow(root) {
                        var inputs = root.querySelectorAll('input[part="input"][type="text"], input.input[type="text"]');
                        for (var i = 0; i < inputs.length; i++) {
                            var r = inputs[i].getBoundingClientRect();
                            if (r.width > 50 && r.height > 0) return inputs[i];
                        }
                        var all = root.querySelectorAll('*');
                        for (var j = 0; j < all.length; j++) {
                            if (all[j].shadowRoot) {
                                var found = findInShadow(all[j].shadowRoot);
                                if (found) return found;
                            }
                        }
                        return null;
                    }

                    // First try light DOM: Budget section has a label "Budget" nearby
                    // find the .vi-form-item that contains "Budget" label text
                    var formItems = document.querySelectorAll('.vi-form-item');
                    for (var k = 0; k < formItems.length; k++) {
                        var txt = (formItems[k].innerText || '').toLowerCase();
                        if (txt.includes('budget') && !txt.includes('time zone') && !txt.includes('schedule')) {
                            // Look inside for shadow root inputs
                            var allInItem = formItems[k].querySelectorAll('*');
                            for (var m = 0; m < allInItem.length; m++) {
                                if (allInItem[m].shadowRoot) {
                                    var f = findInShadow(allInItem[m].shadowRoot);
                                    if (f) return f;
                                }
                            }
                            // Also try regular input[type=number] or input[type=text]
                            var directInp = formItems[k].querySelector('input[type="number"], input[type="text"]:not([readonly])');
                            if (directInp) return directInp;
                        }
                    }

                    // Strategy 2: find ANY shadow-root input visible in viewport
                    return findInShadow(document);
                """)

                if budget_inp:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", budget_inp)
                    time.sleep(0.4)
                    # Click the input to focus it
                    driver.execute_script("arguments[0].click();", budget_inp)
                    time.sleep(0.3)
                    ActionChains(driver).move_to_element(budget_inp).click().perform()
                    time.sleep(0.3)
                    # Select all and delete existing value
                    ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                    time.sleep(0.2)
                    ActionChains(driver).send_keys(Keys.DELETE).perform()
                    time.sleep(0.2)
                    # Type 100
                    ActionChains(driver).send_keys("100").perform()
                    time.sleep(0.3)
                    log_success(f"[ADGROUP BUDGET] Typed '100' in budget input (attempt {_ab+1})!")
                    budget_filled = True
                    break
                else:
                    log_info(f"[ADGROUP BUDGET] Input not found on attempt {_ab+1}, scrolling up...")
                    driver.execute_script("window.scrollBy(0, -200);")
                    time.sleep(0.8)
            except Exception as ab_err:
                log_error(f"[ADGROUP BUDGET] Error on attempt {_ab+1}: {ab_err}")
                time.sleep(0.8)

        if not budget_filled:
            log_error("[ADGROUP BUDGET] Could not fill budget input.")
        else:
            time.sleep(0.5)


        log_info("[TIMEZONE] Looking for timezone dropdown...")
        timezone_clicked = False
        for _tz in range(8):
            try:
                # Return the WRAPPER div (vi-input vi-input--suffix) not the readonly input
                # The wrapper is the clickable element that opens the dropdown
                tz_el = driver.execute_script("""
                    // Primary: walk all elements looking for a label/span with "Time zone" text,
                    // then return the .vi-input wrapper inside the same .vi-form-item
                    var allEls = document.querySelectorAll('*');
                    for (var i = 0; i < allEls.length; i++) {
                        var el = allEls[i];
                        // Only look at leaf-ish text nodes to avoid matching huge parents
                        if (el.children.length > 5) continue;
                        var t = (el.innerText || el.textContent || '').trim().toLowerCase();
                        if (t === 'time zone') {
                            // Walk up to find .vi-form-item ancestor
                            var formItem = el.closest('.vi-form-item');
                            if (!formItem) formItem = el.parentElement;
                            if (formItem) {
                                // Return the vi-input--suffix wrapper div (the clickable dropdown)
                                var wrapper = formItem.querySelector('.vi-input.vi-input--suffix, .vi-input--suffix');
                                if (wrapper) return wrapper;
                                // Fallback: return the readonly input itself
                                var inp = formItem.querySelector('input[readonly]');
                                if (inp) return inp;
                            }
                        }
                    }

                    // Fallback B: scan all .vi-input--suffix wrappers and pick the one
                    // whose ancestor contains "time zone" text
                    var wrappers = document.querySelectorAll('.vi-input--suffix');
                    for (var j = 0; j < wrappers.length; j++) {
                        var ancestor = wrappers[j].closest('.vi-form-item');
                        if (ancestor) {
                            var aText = (ancestor.innerText || '').toLowerCase();
                            if (aText.includes('time zone') || aText.includes('timezone')) {
                                return wrappers[j];
                            }
                        }
                    }

                    // Fallback C: any vi-input--suffix that is currently visible in viewport
                    for (var k = 0; k < wrappers.length; k++) {
                        var r = wrappers[k].getBoundingClientRect();
                        if (r.top > 50 && r.bottom < window.innerHeight - 50 && r.width > 100) {
                            return wrappers[k];
                        }
                    }
                    return null;
                """)

                if tz_el:
                    # Scroll it into view and click the wrapper
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tz_el)
                    time.sleep(0.6)
                    # Click 1 — JS click
                    driver.execute_script("arguments[0].click();", tz_el)
                    time.sleep(0.3)
                    # Click 2 — ActionChains move + click
                    try:
                        ActionChains(driver).move_to_element(tz_el).click().perform()
                    except Exception:
                        pass
                    time.sleep(0.3)
                    # Click 3 — ActionChains click again for triple reliability
                    try:
                        ActionChains(driver).move_to_element(tz_el).click().perform()
                    except Exception:
                        pass
                    time.sleep(0.3)
                    log_success(f"[TIMEZONE] Triple-clicked timezone dropdown (attempt {_tz+1})!")
                    timezone_clicked = True
                    break
                else:
                    log_info(f"[TIMEZONE] Wrapper not found on attempt {_tz+1}, scrolling more...")
                    driver.execute_script("window.scrollBy(0, 250);")
                    time.sleep(1)
            except Exception as tze:
                log_error(f"[TIMEZONE] Error on attempt {_tz+1}: {tze}")
                time.sleep(1)

        if not timezone_clicked:
            log_error("[TIMEZONE] Could not find/click timezone dropdown.")
        else:
            time.sleep(1.5)
            log_success("[TIMEZONE] Timezone dropdown opened.")

            # ── Search for Pakistan in the timezone dropdown ──────────────
            log_info("[TIMEZONE] Looking for Search input in dropdown...")
            search_typed = False
            for _s in range(5):
                try:
                    search_inp = driver.execute_script("""
                        // Find the visible search input inside the dropdown popup
                        // It has placeholder="Search" and class="vi-input__inner"
                        var inputs = document.querySelectorAll('input[placeholder="Search"]');
                        for (var i = 0; i < inputs.length; i++) {
                            var r = inputs[i].getBoundingClientRect();
                            if (r.width > 0 && r.height > 0) return inputs[i];
                        }
                        return null;
                    """)
                    if search_inp:
                        # Click the search input
                        driver.execute_script("arguments[0].click();", search_inp)
                        time.sleep(0.3)
                        ActionChains(driver).move_to_element(search_inp).click().perform()
                        time.sleep(0.3)
                        # Clear any existing text then type Pakistan
                        search_inp.clear()
                        time.sleep(0.2)
                        ActionChains(driver).move_to_element(search_inp).click().send_keys("Pakistan").perform()
                        log_success("[TIMEZONE] Typed 'Pakistan' in search box!")
                        search_typed = True
                        break
                    else:
                        log_info(f"[TIMEZONE] Search input not visible on attempt {_s+1}, waiting...")
                        time.sleep(0.8)
                except Exception as se:
                    log_error(f"[TIMEZONE] Search input error on attempt {_s+1}: {se}")
                    time.sleep(0.8)

            if not search_typed:
                log_error("[TIMEZONE] Could not find/type in timezone search input.")
            else:
                # Wait for results to filter
                time.sleep(1.2)
                # Click the first matching result in the dropdown list
                log_info("[TIMEZONE] Clicking first Pakistan result...")
                for _r in range(4):
                    try:
                        option_clicked = driver.execute_script("""
                            // Find dropdown option items containing 'Pakistan'
                            var opts = document.querySelectorAll(
                                '.vi-select-dropdown__item, .vi-option, [class*="option"], [class*="dropdown-item"]'
                            );
                            for (var i = 0; i < opts.length; i++) {
                                var txt = (opts[i].innerText || opts[i].textContent || '').toLowerCase();
                                if (txt.includes('pakistan')) {
                                    opts[i].scrollIntoView({block:'center'});
                                    opts[i].click();
                                    return true;
                                }
                            }
                            // Fallback: any visible li/div whose text has 'pakistan'
                            var all = document.querySelectorAll('li, [role="option"]');
                            for (var j = 0; j < all.length; j++) {
                                var t = (all[j].innerText || '').toLowerCase();
                                if (t.includes('pakistan')) {
                                    all[j].scrollIntoView({block:'center'});
                                    all[j].click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        if option_clicked:
                            log_success("[TIMEZONE] Selected Pakistan timezone!")
                            break
                        else:
                            log_info(f"[TIMEZONE] Pakistan option not found on attempt {_r+1}, waiting...")
                            time.sleep(0.8)
                    except Exception as re_err:
                        log_error(f"[TIMEZONE] Option click error on attempt {_r+1}: {re_err}")
                        time.sleep(0.8)


        # ── Wait for user to confirm Pixel setup, then click Continue ─────────
        log_info("[PIXEL] Checking if Pixel setup is complete...")
        pixel_ready = False
        while not pixel_ready:
            try:
                answer = input("\n>>> Is your Pixel setup done? (yes/no): ").strip().lower()
            except EOFError:
                answer = "yes"   # non-interactive fallback

            if answer in ("yes", "y"):
                pixel_ready = True
            else:
                log_info("[PIXEL] Waiting 30 seconds, then asking again...")
                time.sleep(30)

        log_info("[PIXEL] Pixel setup confirmed. Clicking 'Continue'...")
        continue_clicked = False
        for _c in range(5):
            try:
                clicked = driver.execute_script("""
                    // Find <ks-button-91g data-testid="common_next_button">
                    // Try both the shadow element and light DOM
                    var btns = document.querySelectorAll('[data-testid="common_next_button"]');
                    for (var i = 0; i < btns.length; i++) {
                        var r = btns[i].getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) {
                            btns[i].scrollIntoView({block: 'center'});
                            btns[i].click();
                            return true;
                        }
                    }
                    // Fallback: any button whose text is 'Continue'
                    var allBtns = document.querySelectorAll('button, ks-button-91g, [role="button"]');
                    for (var j = 0; j < allBtns.length; j++) {
                        var t = (allBtns[j].innerText || allBtns[j].textContent || '').trim();
                        if (t === 'Continue') {
                            allBtns[j].scrollIntoView({block: 'center'});
                            allBtns[j].click();
                            return true;
                        }
                    }
                    return false;
                """)
                if clicked:
                    log_success("[PIXEL] Clicked Continue button!")
                    continue_clicked = True
                    time.sleep(2)
                    break
                else:
                    log_info(f"[PIXEL] Continue button not found on attempt {_c+1}, retrying...")
                    time.sleep(1)
            except Exception as cont_err:
                log_error(f"[PIXEL] Continue click error on attempt {_c+1}: {cont_err}")
                time.sleep(1)

        if not continue_clicked:
            log_error("[PIXEL] Could not click Continue button.")

        set_label(driver, "CREATE READY - Done!")

        # ── Load video codes from CSV ─────────────────────────────────────────
        import csv, os
        default_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_codes.csv")
        print(f"\n[VIDEO CODES] Default CSV path: {default_csv}")
        csv_path_input = input(">>> CSV file path (press Enter to use default): ").strip()
        csv_path = csv_path_input if csv_path_input else default_csv

        post_id_input = input(">>> Enter the Post ID whose video codes you want to use: ").strip()

        video_codes = []
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if str(row.get("id", "")).strip() == post_id_input:
                        code = str(row.get("video_code", "")).strip()
                        if code:
                            video_codes.append(code)
            if video_codes:
                log_success(f"[VIDEO CODES] Loaded {len(video_codes)} code(s) for ID '{post_id_input}'.")
            else:
                log_error(f"[VIDEO CODES] No codes found for ID '{post_id_input}' in {csv_path}.")
        except FileNotFoundError:
            log_error(f"[VIDEO CODES] CSV file not found: {csv_path}")
        except Exception as csv_err:
            log_error(f"[VIDEO CODES] Error reading CSV: {csv_err}")

        # ── Scroll to Ad details → click "Add videos or images" ──────────────
        log_info("[AD CREATIVE] Waiting for Ad creation page to load...")
        time.sleep(3)

        # Scroll down to the Ad details section
        log_info("[AD CREATIVE] Scrolling to 'Ad details' section...")
        driver.execute_script("""
            var allEls = document.querySelectorAll('*');
            for (var i = 0; i < allEls.length; i++) {
                var t = (allEls[i].innerText || allEls[i].textContent || '').trim();
                if (t === 'Ad details' || t === 'Ad creative') {
                    allEls[i].scrollIntoView({block: 'center', behavior: 'smooth'});
                    break;
                }
            }
        """)
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(1)

        # Click "Add videos or images"
        log_info("[AD CREATIVE] Looking for 'Add videos or images' button...")
        add_video_clicked = False
        for _av in range(6):
            try:
                clicked = driver.execute_script("""
                    // Primary: data-tea-std-component-name="hybrid_creative_add_button"
                    var btn = document.querySelector('[data-tea-std-component-name="hybrid_creative_add_button"]');
                    if (btn) {
                        var r = btn.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) {
                            btn.scrollIntoView({block: 'center'});
                            btn.click();
                            return 'primary';
                        }
                    }
                    // Secondary: button whose span text is "Add videos or images"
                    var allBtns = document.querySelectorAll('button');
                    for (var i = 0; i < allBtns.length; i++) {
                        var t = (allBtns[i].innerText || allBtns[i].textContent || '').trim();
                        if (t.toLowerCase().includes('add videos or images')) {
                            allBtns[i].scrollIntoView({block: 'center'});
                            allBtns[i].click();
                            return 'text-match';
                        }
                    }
                    return false;
                """)
                if clicked:
                    log_success(f"[AD CREATIVE] Clicked 'Add videos or images' ({clicked})!")
                    add_video_clicked = True
                    time.sleep(2)
                    break
                else:
                    log_info(f"[AD CREATIVE] Button not found on attempt {_av+1}, scrolling...")
                    driver.execute_script("window.scrollBy(0, 200);")
                    time.sleep(0.8)
            except Exception as av_err:
                log_error(f"[AD CREATIVE] Click error on attempt {_av+1}: {av_err}")
                time.sleep(0.8)

        if not add_video_clicked:
            log_error("[AD CREATIVE] Could not find/click 'Add videos or images' button.")
        else:
            log_info("[AD CREATIVE] Right-side creative sidebar should now be open.")
            time.sleep(1.5)

            # ── Click the "TikTok posts" tab in the sidebar ───────────────────
            log_info("[TIKTOK POSTS] Clicking 'TikTok posts' tab...")
            tiktok_tab_clicked = False
            for _tt in range(5):
                try:
                    clicked = driver.execute_script("""
                        // Primary: id="tab-tiktok_mixed_post"
                        var tab = document.getElementById('tab-tiktok_mixed_post');
                        if (tab) {
                            tab.scrollIntoView({block: 'center'});
                            tab.click();
                            return 'id-match';
                        }
                        // Fallback: tab whose text is "TikTok posts"
                        var tabs = document.querySelectorAll('[role="tab"], .vi-tabs__item, .vi-tab');
                        for (var i = 0; i < tabs.length; i++) {
                            var t = (tabs[i].innerText || tabs[i].textContent || '').trim().toLowerCase();
                            if (t === 'tiktok posts') {
                                tabs[i].scrollIntoView({block: 'center'});
                                tabs[i].click();
                                return 'text-match';
                            }
                        }
                        return false;
                    """)
                    if clicked:
                        log_success(f"[TIKTOK POSTS] Clicked TikTok posts tab ({clicked})!")
                        tiktok_tab_clicked = True
                        time.sleep(1.5)
                        break
                    else:
                        log_info(f"[TIKTOK POSTS] Tab not found on attempt {_tt+1}, waiting...")
                        time.sleep(0.8)
                except Exception as tt_err:
                    log_error(f"[TIKTOK POSTS] Error on attempt {_tt+1}: {tt_err}")
                    time.sleep(0.8)

            if not tiktok_tab_clicked:
                log_error("[TIKTOK POSTS] Could not click TikTok posts tab.")
            else:
                # ── Click "Add post" button (middle-right of sidebar) ─────────
                log_info("[ADD POST] Looking for 'Add post' button...")
                add_post_clicked = False
                for _ap in range(6):
                    try:
                        clicked = driver.execute_script("""
                            // Primary: vi-button--dark whose text is "Add post"
                            var darkBtns = document.querySelectorAll('button.vi-button--dark');
                            for (var i = 0; i < darkBtns.length; i++) {
                                var t = (darkBtns[i].innerText || darkBtns[i].textContent || '').trim();
                                if (t.toLowerCase() === 'add post') {
                                    darkBtns[i].scrollIntoView({block: 'center'});
                                    darkBtns[i].click();
                                    return 'dark-btn';
                                }
                            }
                            // Fallback: any button whose text is "Add post"
                            var allBtns = document.querySelectorAll('button');
                            for (var j = 0; j < allBtns.length; j++) {
                                var t2 = (allBtns[j].innerText || allBtns[j].textContent || '').trim();
                                if (t2.toLowerCase() === 'add post') {
                                    allBtns[j].scrollIntoView({block: 'center'});
                                    allBtns[j].click();
                                    return 'text-match';
                                }
                            }
                            return false;
                        """)
                        if clicked:
                            log_success(f"[ADD POST] Clicked 'Add post' button ({clicked})!")
                            add_post_clicked = True
                            time.sleep(1.5)
                            break
                        else:
                            log_info(f"[ADD POST] Button not found on attempt {_ap+1}, waiting...")
                            time.sleep(0.8)
                    except Exception as ap_err:
                        log_error(f"[ADD POST] Error on attempt {_ap+1}: {ap_err}")
                        time.sleep(0.8)

                if not add_post_clicked:
                    log_error("[ADD POST] Could not click 'Add post' button.")
                elif video_codes:
                    # ── Type video codes into the dialog textarea ─────────────
                    log_info("[VIDEO CODES] Waiting for 'Authorize TikTok posts' dialog...")
                    time.sleep(2)
                    codes_text = "\n".join(video_codes)
                    typed_codes = False
                    for _tc in range(6):
                        try:
                            # Find the dialog textarea specifically (NOT the ad-text textarea behind it)
                            ta_el = None
                            for sel in [
                                'textarea[placeholder*="TikTok post code"]',
                                'textarea[autofocus]',
                                '[data-testid*="native-batch-authorize"] textarea',
                                '.vi-dialog textarea',
                            ]:
                                try:
                                    candidates = driver.find_elements(By.CSS_SELECTOR, sel)
                                    for c in candidates:
                                        placeholder = (c.get_attribute('placeholder') or '').lower()
                                        if c.is_displayed() and 'post code' in placeholder:
                                            ta_el = c
                                            break
                                    if ta_el:
                                        break
                                except Exception:
                                    pass

                            if ta_el:
                                # JS focus to bypass click-interception, then real send_keys for Vue reactivity
                                driver.execute_script('arguments[0].scrollIntoView({block:"center"});', ta_el)
                                driver.execute_script('arguments[0].focus();', ta_el)
                                time.sleep(0.3)
                                ta_el.send_keys(Keys.CONTROL + 'a')
                                ta_el.send_keys(Keys.DELETE)
                                time.sleep(0.2)
                                ta_el.send_keys(codes_text)
                                time.sleep(0.5)
                                log_success(f'[VIDEO CODES] Typed {len(video_codes)} code(s) into textarea (send_keys).')
                                typed_codes = True
                                break
                            else:
                                log_info(f'[VIDEO CODES] Textarea not found on attempt {_tc+1}, waiting...')
                                time.sleep(0.8)
                        except Exception as tc_err:
                            log_error(f'[VIDEO CODES] Textarea error on attempt {_tc+1}: {tc_err}')
                            time.sleep(0.8)


                    if not typed_codes:
                        log_error("[VIDEO CODES] Could not type codes into textarea.")
                    else:
                        # ── Click 'Continue' in the dialog ────────────────────
                        log_info("[VIDEO CODES] Clicking 'Continue' in the dialog...")
                        time.sleep(0.5)
                        for _dc in range(5):
                            try:
                                dlg_cont = driver.execute_script("""
                                    // Dialog footer Continue button
                                    var footer = document.querySelector('.vi-dialog__footer, [role="dialog"]');
                                    if (footer) {
                                        var btns = footer.querySelectorAll('button');
                                        for (var i = 0; i < btns.length; i++) {
                                            var t = (btns[i].innerText || btns[i].textContent || '').trim();
                                            if (t === 'Continue') {
                                                btns[i].click();
                                                return 'footer-btn';
                                            }
                                        }
                                    }
                                    // Fallback: any visible Continue button
                                    var all = document.querySelectorAll('button');
                                    for (var j = 0; j < all.length; j++) {
                                        var t2 = (all[j].innerText || all[j].textContent || '').trim();
                                        if (t2 === 'Continue') {
                                            all[j].click();
                                            return 'global-btn';
                                        }
                                    }
                                    return false;
                                """)
                                if dlg_cont:
                                    log_success(f'[DIALOG1] Clicked Continue in Authorize dialog ({dlg_cont})!')
                                    time.sleep(2)
                                    break
                                else:
                                    log_info(f"[VIDEO CODES] Continue not found in dialog on attempt {_dc+1}...")
                                    time.sleep(0.8)
                            except Exception as dc_err:
                                log_error(f"[VIDEO CODES] 'Add TikTok posts' error: {dc_err}")
                                time.sleep(0.8)



                        # -- Dialog 2: Confirm TikTok posts -> click 'Add TikTok posts' --
                        log_info('[DIALOG2] Waiting for Confirm TikTok posts dialog...')
                        time.sleep(2.5)
                        d2_clicked = False
                        for _d2 in range(8):
                            try:
                                # Strategy A: Selenium XPath + JS click (no offsetParent issue)
                                btn_el = None
                                for xp in [
                                    "//button[normalize-space(.)='Add TikTok posts']",
                                    "//button[contains(.,'Add TikTok posts')]",
                                    "//button[contains(@data-testid,'native-batch-authorize') and contains(@class,'vi-button--primary')]",
                                ]:
                                    try:
                                        for el in driver.find_elements(By.XPATH, xp):
                                            r = driver.execute_script('var r=arguments[0].getBoundingClientRect();return r.width>0&&r.height>0;', el)
                                            if r:
                                                btn_el = el
                                                break
                                        if btn_el:
                                            break
                                    except Exception:
                                        pass

                                if btn_el:
                                    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', btn_el)
                                    time.sleep(0.2)
                                    driver.execute_script('arguments[0].click();', btn_el)
                                    log_success('[DIALOG2] Clicked Add TikTok posts (Selenium XPath JS-click)!')
                                    d2_clicked = True
                                    time.sleep(2)
                                    break

                                # Strategy B: pure JS with getBoundingClientRect visibility check
                                sel_str = '[data-testid*="native-batch-authorize"][class*="vi-button--primary"],button.vi-button--primary'
                                d2_js = driver.execute_script(
                                    'var btns=document.querySelectorAll(arguments[0]);'
                                    'for(var i=0;i<btns.length;i++){'
                                    '  var r=btns[i].getBoundingClientRect();'
                                    '  if(r.width>0&&r.height>0){btns[i].click();return "rect-primary";}'
                                    '}'
                                    'var all=document.querySelectorAll("button");'
                                    'for(var j=0;j<all.length;j++){'
                                    '  var t=(all[j].innerText||"").trim().toLowerCase();'
                                    '  var r2=all[j].getBoundingClientRect();'
                                    '  if(t.indexOf("add tiktok")!==-1&&r2.width>0){all[j].click();return "text-match";}'
                                    '}'
                                    'return false;',
                                    sel_str
                                )
                                if d2_js:
                                    log_success(f'[DIALOG2] Clicked Add TikTok posts ({d2_js})!')
                                    d2_clicked = True
                                    time.sleep(2)
                                    break
                                else:
                                    log_info(f'[DIALOG2] Button not found attempt {_d2+1}, retrying...')
                                    time.sleep(1)
                            except Exception as d2_err:
                                log_error(f'[DIALOG2] Error attempt {_d2+1}: {d2_err}')
                                time.sleep(1)

                        if not d2_clicked:
                            log_error('[DIALOG2] Could not click Add TikTok posts after 8 attempts.')

                        # -- Sidebar Confirm button (hybrid-drawer-footer-submit-button) --
                        if d2_clicked:
                            log_info('[CONFIRM] Waiting for sidebar Confirm button...')
                            time.sleep(2)
                            confirmed = False
                            for _cf in range(6):
                                try:
                                    cf_el = None
                                    # Strategy A: exact data-testid via Selenium
                                    try:
                                        for el in driver.find_elements(By.CSS_SELECTOR,
                                                '[data-testid="hybrid-drawer-footer-submit-button"]'):
                                            r = driver.execute_script(
                                                'var r=arguments[0].getBoundingClientRect();'
                                                'return r.width>0&&r.height>0;', el)
                                            if r:
                                                cf_el = el
                                                break
                                    except Exception:
                                        pass

                                    # Strategy B: XPath in footer-operation div
                                    if not cf_el:
                                        try:
                                            xp = '//*[contains(@class,"footer-operation")]//button[normalize-space(.)="Confirm"]'
                                            for el in driver.find_elements(By.XPATH, xp):
                                                r = driver.execute_script(
                                                    'var r=arguments[0].getBoundingClientRect();'
                                                    'return r.width>0&&r.height>0;', el)
                                                if r:
                                                    cf_el = el
                                                    break
                                        except Exception:
                                            pass

                                    if cf_el:
                                        driver.execute_script(
                                            'arguments[0].scrollIntoView({block:"nearest"});', cf_el)
                                        time.sleep(0.2)
                                        driver.execute_script('arguments[0].click();', cf_el)
                                        log_success('[CONFIRM] Clicked sidebar Confirm button!')
                                        confirmed = True
                                        time.sleep(2)
                                        break
                                    else:
                                        log_info(f'[CONFIRM] Confirm not found attempt {_cf+1}...')
                                        time.sleep(1)
                                except Exception as cf_err:
                                    log_error(f'[CONFIRM] Error attempt {_cf+1}: {cf_err}')
                                    time.sleep(1)

                            if not confirmed:
                                log_error('[CONFIRM] Could not click sidebar Confirm after 6 attempts.')

                        # -- Scroll to 'Call to action' and click clear (right-icon) --
                        if confirmed:
                            log_info('[CTA] Scrolling to Call to action section...')
                            time.sleep(1.5)
                            try:
                                # Scroll the page down to expose the CTA section
                                driver.execute_script("window.scrollBy(0, 400);")
                                time.sleep(1)
                            except Exception:
                                pass

                            cta_cleared = False
                            for _cta in range(6):
                                try:
                                    cta_el = None
                                    # Strategy A: i.right-icon that is NOT the arrow-down (= clear btn)
                                    # inside the vi-select-tree-inside-container
                                    selectors = [
                                        'i.right-icon:not(.vi-icon-arrow-down)',
                                        '[data-testid*="select-tree-container-inside"].right-icon',
                                        'i[data-testid*="select-tree-container-inside"]',
                                    ]
                                    for sel in selectors:
                                        try:
                                            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                                                r = driver.execute_script(
                                                    'var r=arguments[0].getBoundingClientRect();'
                                                    'return r.width>=0&&r.height>=0&&r.top>=0;', el)
                                                if r:
                                                    cta_el = el
                                                    break
                                        except Exception:
                                            pass
                                        if cta_el:
                                            break

                                    if cta_el:
                                        driver.execute_script(
                                            'arguments[0].scrollIntoView({block:"center"});', cta_el)
                                        time.sleep(0.3)
                                        driver.execute_script('arguments[0].click();', cta_el)
                                        log_success('[CTA] Clicked Call to action clear icon!')
                                        cta_cleared = True
                                        time.sleep(1)
                                        break
                                    else:
                                        log_info(f'[CTA] Clear icon not found attempt {_cta+1}...')
                                        time.sleep(0.8)
                                except Exception as cta_err:
                                    log_error(f'[CTA] Error attempt {_cta+1}: {cta_err}')
                                    time.sleep(0.8)

                            if not cta_cleared:
                                log_error('[CTA] Could not click Call to action clear icon.')


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
