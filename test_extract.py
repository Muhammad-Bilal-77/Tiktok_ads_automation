import time
import json
from selenium.webdriver.common.by import By
from browser import connect_browser

def main():
    driver = connect_browser()
    
    # Switch to home tab
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "i18n/home" in driver.current_url:
            break
            
    print("Connected to:", driver.current_url)
    
    # Check window state
    state = driver.execute_script("return window.__INITIAL_STATE__ || window.__TCM_INITIAL_STATE__ || null;")
    if state:
        with open("page_state.json", "w") as f:
            json.dump(state, f)
        print("Dumped state to page_state.json")

    # Scrape directly from DOM via JS (the robust way if state isn't clear)
    js_extract = """
    let results = [];
    let items = document.querySelectorAll('div');
    for (let div of items) {
        if (div.textContent && div.textContent.includes('Ads Manager (')) {
            // Find the container below it
            let parent = div.parentElement;
            if (parent) {
                let text = parent.innerText;
                let idMatches = text.match(/ID:\\s*(\\d+)/g);
                if (idMatches) {
                    return text; // Return raw text to parse in python
                }
            }
        }
    }
    return "Not found";
    """
    raw_text = driver.execute_script(js_extract)
    with open("raw_text.txt", "w", encoding='utf-8') as f:
        f.write(raw_text)
    print("Dumped raw text to raw_text.txt")
        
    driver.quit()

if __name__ == "__main__":
    main()
