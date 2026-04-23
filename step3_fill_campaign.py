"""
TikTok Ads - Step 3: Setup Campaign Details
=======================================================
This script fills out the campaign form generated after clicking 'Create'.
It performs the following:
1. Switches to full version if in simplified mode
2. Selects 'Sales' objective
3. Selects 'Website' destination
4. Toggles 'Search campaign' 
5. Toggles 'Set campaign budget'
6. Enters '1000' into the budget field

Prerequisites:
    - create_campaign.py has successfully opened the new campaign form.

Usage:
    python step3_fill_campaign.py
"""

import time
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, NoAlertPresentException

from browser import connect_browser, disconnect_browser
from logger import log_info, log_step, log_error, log_success, log_warning, LoadingSpinner


# ─────────────────────────────────────────────────────────────
# Cursor overlay logic (consistent with previous scripts)
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
    try:
        driver.execute_script(CURSOR_JS)
    except Exception:
        pass


def set_label(driver, text):
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
    offset_x = x - vw // 2
    offset_y = y - vh // 2
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(body, offset_x, offset_y)
    actions.perform()


def smooth_move_mouse(driver, x, y):
    """Glide mouse cursor smoothly towards the target."""
    current_x = driver.execute_script("var dot=document.getElementById('sel-cursor'); return dot ? parseInt(dot.style.left) || window.innerWidth/2 : window.innerWidth/2;")
    current_y = driver.execute_script("var dot=document.getElementById('sel-cursor'); return dot ? parseInt(dot.style.top) || window.innerHeight/2 : window.innerHeight/2;")
    
    steps = 8
    for i in range(1, steps + 1):
        step_x = current_x + (x - current_x) * i // steps
        step_y = current_y + (y - current_y) * i // steps
        move_mouse_to(driver, step_x, step_y)
        time.sleep(0.04)


def click_at(driver, x, y, description=""):
    """Move mouse to coordinates and click."""
    set_label(driver, f"Clicking: {description}")
    smooth_move_mouse(driver, x, y)
    time.sleep(0.2)
    actions = ActionChains(driver)
    actions.click()
    actions.perform()
    log_info(f"[CLICK] Clicked at ({x}, {y}) - {description}")


# ─────────────────────────────────────────────────────────────
# JS Execution & Component Finders
# ─────────────────────────────────────────────────────────────

def interact_with_element_by_js(driver, js_find_code, description="", retries=10, must_succeed=True):
    """
    Executes JS code to find an element, scroll to it, and click it via screen coordinates.
    The JS must return {el: element, status: 'needs_click' | 'already_set'} or null.
    """
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
                
                if data.get("status") == "already_set":
                    log_success(f"[{description}] is already active/set.")
                    return True
                
                x, y = data["x"], data["y"]
                click_at(driver, x, y, description)
                time.sleep(1) # wait for animations
                return True
                
        except Exception as e:
            pass # suppress noisy JS errors
        time.sleep(1)
        
    spinner.stop(f"Could not find {description}.")
    if must_succeed:
        log_error(f"Required element '{description}' missing or unclickable.")
    return False


# JS Code Definitions for Specific Elements


JS_FIND_SALES = """
    // Finds Sales objective under Conversion section
    var labels = document.querySelectorAll('label, div');
    for (var l of labels) {
        if (l.getAttribute('data-tea-objective_name') === 'Sales') {
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

JS_FIND_WEBSITE = """
    // Finds Website radio destination
    var labels = document.querySelectorAll('label, div');
    for (var l of labels) {
        if (l.getAttribute('data-tea-sales_destination') === 'website') {
            if (l.classList.contains('is-checked') || l.getAttribute('aria-checked') === 'true') {
                return {el: l, status: 'already_set'};
            }
            return {el: l, status: 'needs_click'};
        }
    }
    var all = document.querySelectorAll('*');
    for (var a of all) {
        if (a.childElementCount === 0 && a.textContent.trim() === 'Website') {
            var p = a.parentElement;
            // Ensure not to confuse with page headers
            if (p.tagName === 'LABEL' || p.className.includes('radio')) {
                var isChecked = p.classList.contains('is-checked') || p.getAttribute('aria-checked') === 'true';
                if (isChecked) return {el: a, status: 'already_set'};
                return {el: a, status: 'needs_click'};
            }
        }
    }
    return null;
"""

JS_FIND_SEARCH_CAMPAIGN = """
    var elements = document.querySelectorAll('*');
    for (var el of elements) {
        if (el.childElementCount === 0 && el.textContent.trim() === 'Search campaign') {
            var parent = el.parentElement;
            while(parent && parent.tagName !== 'BODY') {
                var sw = parent.querySelector('[role="switch"], .vi-switch');
                if (sw) {
                    var isChecked = sw.getAttribute('aria-checked') === 'true' || sw.classList.contains('is-checked');
                    if (isChecked) return {el: sw, status: 'already_set'};
                    return {el: sw, status: 'needs_click'};
                }
                parent = parent.parentElement;
            }
        }
    }
    return null;
"""

JS_FIND_SET_BUDGET = """
    var elements = document.querySelectorAll('*');
    for (var el of elements) {
        if (el.childElementCount === 0 && (el.textContent.trim() === 'Set campaign budget' || el.textContent.trim().includes('Set campaign budget'))) {
            var parent = el.parentElement;
            while(parent && parent.tagName !== 'BODY') {
                var sw = parent.querySelector('[role="switch"], .vi-switch');
                if (sw) {
                    var isChecked = sw.getAttribute('aria-checked') === 'true' || sw.classList.contains('is-checked');
                    if (isChecked) return {el: sw, status: 'already_set'};
                    return {el: sw, status: 'needs_click'};
                }
                parent = parent.parentElement;
            }
        }
    }
    return null;
"""

JS_FIND_BUDGET_INPUT = """
    // Try to find the shadow-root input 
    var all = document.querySelectorAll('*');
    for (var el of all) {
        if (el.shadowRoot) {
            var inp = el.shadowRoot.querySelector('input');
            if (inp && (inp.placeholder.includes('50') || inp.type === 'text' || inp.type === 'number') && inp.classList.contains('input')) {
                var r = inp.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) return {el: inp, status: 'needs_click'};
            }
        }
    }
    // Fallback search
    var inputs = document.querySelectorAll('input[type="number"], input[placeholder*="50"]');
    for (var i of inputs) {
        var r = i.getBoundingClientRect();
        if (r.width > 0) return {el: i, status: 'needs_click'};
    }
    return null;
"""


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    driver = None

    try:
        print("\n" + "=" * 55)
        print("  STEP 3: Fill Campaign Details")
        print("=" * 55 + "\n")

        spinner = LoadingSpinner("Connecting to Chrome on port 9222")
        spinner.start()

        try:
            driver = connect_browser()
            spinner.stop("Connected to Chrome!")
        except Exception as e:
            spinner.stop("Connection failed.")
            log_error("Make sure Chrome is running and you are on the Campaign Create form.")
            return

        inject_cursor(driver)
        set_label(driver, "STEP 3: Setting Up Campaign")
        time.sleep(1)

        # Ensure we are inside campaign creation UI
        curr = driver.current_url.lower()
        if "create" not in curr and "aadvid" not in curr:
            log_warning("You don't appear to be on the Campaign Creation form.")

        log_step(1, "Selecting 'Sales' objective...")
        interact_with_element_by_js(driver, JS_FIND_SALES, "Sales Objective")
        time.sleep(1)

        log_step(2, "Selecting 'Website' destination...")
        interact_with_element_by_js(driver, JS_FIND_WEBSITE, "Website Destination Radio")

        log_step(3, "Toggling 'Search campaign' on...")
        interact_with_element_by_js(driver, JS_FIND_SEARCH_CAMPAIGN, "Search Campaign Toggle")

        log_step(4, "Toggling 'Set campaign budget' on...")
        interact_with_element_by_js(driver, JS_FIND_SET_BUDGET, "Set Campaign Budget Toggle")
        time.sleep(1) # wait for the input field to animate / appear

        log_step(5, "Entering Budget Value...")
        # First we click the input to focus it:
        if interact_with_element_by_js(driver, JS_FIND_BUDGET_INPUT, "Budget Input Field"):
            # Input successfully clicked & focused. Send the value!
            set_label(driver, "Typing: 1000")
            
            actions = ActionChains(driver)
            # Clear any default value (Ctrl+A, Backspace)
            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            # Type 1000
            actions.pause(0.2)
            actions.send_keys("1000")
            actions.perform()
            
            log_success("Typed '1000' into the budget field.")
            time.sleep(1)

        set_label(driver, "CAMPAIGN DETAILS FILLED!")
        log_success("Step 3 complete!")

        print("\n" + "=" * 55)
        print("  DONE! Campaign details have been filled.")
        print("  ENTER to disconnect (Chrome stays open).")
        print("=" * 55 + "\n")

        input(">>> ")

    except WebDriverException as e:
        log_error(f"WebDriver error: {e}")
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
