"""
Logger Utility for TikTok Ads Automation
=========================================
Provides timestamped console logging with live progress indicator.
"""

import sys
import io
import time
import threading
from datetime import datetime

# Fix Windows terminal encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def _timestamp():
    return datetime.now().strftime("%H:%M:%S")


def log_info(message: str):
    print(f"[{_timestamp()}] [INFO]    {message}")


def log_warning(message: str):
    print(f"[{_timestamp()}] [WARNING] {message}")


def log_error(message: str):
    print(f"[{_timestamp()}] [ERROR]   {message}")


def log_step(step_number: int, message: str):
    print(f"[{_timestamp()}] [STEP {step_number}]  {message}")


def log_success(message: str):
    print(f"[{_timestamp()}] [SUCCESS] {message}")


class LoadingSpinner:
    """
    Shows a live spinning animation in the terminal so the user
    knows the script is working and not stuck.
    
    Usage:
        spinner = LoadingSpinner("Loading page")
        spinner.start()
        # ... do work ...
        spinner.stop("Done!")
    """
    def __init__(self, message="Working"):
        self.message = message
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        frames = ["|", "/", "-", "\\"]
        idx = 0
        elapsed = 0
        while self._running:
            frame = frames[idx % len(frames)]
            sys.stdout.write(f"\r[{_timestamp()}] [{frame}] {self.message}... ({elapsed}s)  ")
            sys.stdout.flush()
            time.sleep(0.3)
            elapsed = round(elapsed + 0.3, 1)
            idx += 1

    def stop(self, final_message=None):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        # Clear the spinner line
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        if final_message:
            log_info(final_message)
