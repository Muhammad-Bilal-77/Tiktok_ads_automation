# TikTok Ads Automation Tool

This tool automates the process of creating TikTok Ads campaigns, including account selection, campaign objective setup (Sales), and budget configuration.

## Features
- **Account Selection**: Automatically finds and selects Ads Manager accounts.
- **Shadow DOM Support**: Pierces through TikTok's complex UI to interact with hidden elements.
- **Visual Feedback**: Shows a red cursor overlay in the browser so you can see exactly what the automation is doing.
- **Resilient Navigation**: Handles page loads, popups, and redirects automatically.

---

## Installation & Setup

### 1. Prerequisites
- **Python 3.10+**: [Download here](https://www.python.org/downloads/)
- **Google Chrome**: Ensure you have the latest version of Chrome installed.

### 2. Install Dependencies
Open your terminal or command prompt in the project folder and run:
```bash
pip install -r requirements.txt
```

### 3. Configuration
The tool uses your existing Chrome profile to keep you logged in.
- Open `config.py`.
- Ensure `CHROME_PROFILE` matches your Chrome profile name (usually `"Default"` or `"Profile 1"`, `"Profile 2"`, etc.).
- You can find your profile name by typing `chrome://version` in your Chrome address bar and looking at the "Profile Path".

---

## How to Run

### Step 1: Login & Navigation
Run the main script to start Chrome and log in:
```bash
python main.py
```
1. Chrome will open.
2. Log in to your TikTok Ads account manually if not already logged in.
3. Once logged in, go back to the terminal and type `yes`.
4. Follow the on-screen instructions to select your Ads Manager account.

### Step 2: Campaign Automation
Once you reach the Campaigns page in Step 1, the script will ask if you want to start `create_campaign.py`.
- Type `yes` to start the automation.
- **Do not close the browser window.** The script will control the same window you just used.

---

## Project Structure
- `main.py`: The entry point. Handles browser launch, login verification, and account selection.
- `create_campaign.py`: Handles the detailed automation of creating a campaign.
- `browser.py`: Manages Chrome driver setup and speed optimizations.
- `config.py`: Central configuration for URLs, timeouts, and profile paths.
- `logger.py`: Provides colorful and informative terminal output.
- `budget.txt`: Set your desired budgets here.

---

## Troubleshooting
- **Chrome doesn't open**: Close all existing Chrome windows before running the script, as Chrome doesn't allow multiple instances with the same profile.
- **Element not found**: If the UI changes, the script might need an update. Try increasing `EXPLICIT_WAIT` in `config.py` if your internet is slow.
- **Shadow DOM Errors**: These are usually handled automatically, but ensure you are on the "Full Version" of TikTok Ads Manager as the script expects that layout.
