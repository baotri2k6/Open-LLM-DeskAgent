import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "python-services"))

from tools.screen_reader import ocr_screenshot

def main():
    print("Calling ocr_screenshot() directly...")
    res = ocr_screenshot()
    print("Result:", res)

if __name__ == "__main__":
    main()
