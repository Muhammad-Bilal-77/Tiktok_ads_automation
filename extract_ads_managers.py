import re
from browser import connect_browser

def main():
    print("Connecting to Chrome browser...")
    driver = None
    try:
        driver = connect_browser()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # Switch to the right tab
    found = False
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "i18n/home" in driver.current_url:
            found = True
            break
            
    if not found:
        print("Could not find the TikTok ads home page (https://ads.tiktok.com/i18n/home) in any open tabs.")
        print("Please navigate to it first and then run this script.")
        return
        
    print(f"Connected to: {driver.current_url}")
    print("Extracting account data from page...")
    
    # Get all text from body
    page_text = driver.execute_script("return document.body.innerText;")
    
    # Split the text to find the Ads Manager section
    if "Ads Manager (" in page_text:
        # Keep only the text after "Ads Manager ("
        # This prevents us from extracting the "Business Center" IDs
        ads_section = page_text.split("Ads Manager (", 1)[1]
    else:
        print("Warning: Could not find 'Ads Manager (' header. Extracting ALL IDs found on page.")
        ads_section = page_text
        
    # Extract IDs using regex. The format on page is typically:
    # Account Name
    # ID: 1234567890
    
    # Find all IDs
    ids_only = re.findall(r'ID:\s*(\d+)', ads_section)
    
    # Try to grab the name above the ID as well for a full list
    accounts = []
    matches = re.finditer(r'(?:^|\n)([^\n]+?)\s*\nID:\s*(\d+)', ads_section, re.MULTILINE)
    for match in matches:
        name = match.group(1).strip()
        acc_id = match.group(2).strip()
        accounts.append(f"{name} -> {acc_id}")
        
    print(f"\nExtracted {len(ids_only)} Ads Manager IDs!")
    
    # Save the simple list of IDs
    with open("ads_manager_ids.txt", "w", encoding="utf-8") as f:
        for acc_id in ids_only:
            f.write(acc_id + "\n")
            
    # Save the mapped list (Name -> ID)
    with open("ads_manager_names_and_ids.txt", "w", encoding="utf-8") as f:
        for acc in accounts:
            f.write(acc + "\n")
            
    print("\nFiles created:")
    print(" 1. ads_manager_ids.txt")
    print(" 2. ads_manager_names_and_ids.txt")
    
    # --- Interactive Menu ---
    print("\n" + "=" * 50)
    print("             ADS MANAGER ACCOUNTS")
    print("=" * 50)
    
    for i, acc in enumerate(accounts):
        print(f"[{i+1}] {acc}")
        
    print("=" * 50)
    
    while True:
        choice = input(f"\n>>> Select an account number (1-{len(accounts)}), or 'q' to quit: ").strip()
        if choice.lower() in ['q', 'quit', 'exit']:
            print("Exiting.")
            break
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                chosen_acc = accounts[idx]
                # format is "Name -> 123456789"
                chosen_id = chosen_acc.split("->")[1].strip()
                
                print(f"\nYou selected: {chosen_acc}")
                target_url = f"https://ads.tiktok.com/i18n/manage/campaign?aadvid={chosen_id}"
                
                print(f"Redirecting browser to: {target_url}")
                driver.get(target_url)
                
                print("\nSuccessfully redirected! You can now run `python create_campaign.py` to start adding a campaign here.")
                break
            else:
                print("Invalid number. Try again.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    main()
