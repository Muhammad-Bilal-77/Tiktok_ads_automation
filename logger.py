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
import colorama

# Fix Windows terminal encoding first
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Initialize colorama AFTER wrapping sys.stdout, and force it to handle ANSI on Windows
colorama.init(autoreset=True, wrap=True, convert=True)

# Lock for terminal output to prevent overlapping between threads
_stdout_lock = threading.Lock()
_active_spinner = None

def _reset_terminal():
    """Force a clean terminal state by clearing common buffers."""
    # Move to start of line and clear all
    sys.stdout.write("\r\033[2J\033[H") # ANSI clear screen and move home
    sys.stdout.flush()

# Call reset on initial import
_reset_terminal()

def _timestamp():
    return datetime.now().strftime("%H:%M:%S")

def _clear_line():
    """Clear the current line and move cursor back to start."""
    # \r = move to start, \033[K = clear line
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

import builtins
_original_input = builtins.input

def _safe_input(prompt=""):
    """
    Overridden built-in input() that stops spinners and clears the line first.
    """
    stop_all_spinners()
    with _stdout_lock:
        _clear_line()
        # Remove any leading newlines from the prompt to prevent vertical gaps
        if isinstance(prompt, str):
            prompt = prompt.lstrip('\n')
        # Tiny delay to let the terminal's cursor state stabilize
        time.sleep(0.1)
        return _original_input(prompt)

# Patch the global input
builtins.input = _safe_input

def stop_all_spinners():
    """Emergency stop for any running spinner (e.g. on crash)."""
    global _active_spinner
    if _active_spinner:
        _active_spinner.stop()

def log_info(message: str):
    with _stdout_lock:
        _clear_line()
        print(f"[{_timestamp()}] [INFO]    {message}")

def log_warning(message: str):
    with _stdout_lock:
        _clear_line()
        print(f"[{_timestamp()}] [WARNING] {message}")

def log_error(message: str):
    with _stdout_lock:
        _clear_line()
        print(f"[{_timestamp()}] [ERROR]   {message}")

def log_step(step_number: int, message: str):
    with _stdout_lock:
        _clear_line()
        print(f"[{_timestamp()}] [STEP {step_number}]  {message}")

def log_success(message: str):
    with _stdout_lock:
        _clear_line()
        print(f"[{_timestamp()}] [SUCCESS] {message}")

class LoadingSpinner:
    """
    Shows a live spinning animation in the terminal.
    Thread-safe and aware of other logging calls.
    """
    def __init__(self, message="Working"):
        self.message = message
        self._running = False
        self._thread = None

    def start(self):
        global _active_spinner
        self._running = True
        _active_spinner = self
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        frames = ["|", "/", "-", "\\"]
        idx = 0
        elapsed = 0
        while self._running:
            frame = frames[idx % len(frames)]
            with _stdout_lock:
                if self._running:
                    sys.stdout.write(f"\r[{_timestamp()}] [{frame}] {self.message}... ({elapsed}s)  ")
                    sys.stdout.flush()
            time.sleep(0.3)
            elapsed = round(elapsed + 0.3, 1)
            idx += 1

    def stop(self, final_message=None):
        global _active_spinner
        self._running = False
        _active_spinner = None
        if self._thread:
            self._thread.join(timeout=1)
        
        with _stdout_lock:
            _clear_line()
        
        if final_message:
            log_info(final_message)
