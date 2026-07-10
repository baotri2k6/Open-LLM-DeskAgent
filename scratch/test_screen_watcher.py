import sys
import os
import time

# Add python-services to sys.path so we can import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "python-services"))

from core.screen_watcher import ScreenWatcher
from core.config import config

def main():
    print("=== Testing ScreenWatcher ===")
    
    # Enable screenAwareness for testing
    config.set("features.screenAwareness", True)
    
    watcher = ScreenWatcher(change_threshold=0.15)
    print("Starting watcher background thread...")
    watcher.start()
    
    try:
        for i in range(3):
            print(f"\n[Check #{i+1}] Waiting for OCR updates from background thread...")
            time.sleep(6)
            
            context = watcher.get_current_context()
            activity = watcher.get_current_activity()
            
            print(f"Detected Activity: {activity}")
            print(f"Captured OCR Text Length: {len(context)} characters")
            if context:
                # Print ASCII safe representation
                print(f"Snippet: {repr(context[:200])}")
            else:
                print("No text captured yet. (Make sure pytesseract is installed and configured).")
                
    finally:
        print("\nStopping watcher background thread...")
        watcher.stop()
        print("Test stopped successfully!")

if __name__ == "__main__":
    main()
