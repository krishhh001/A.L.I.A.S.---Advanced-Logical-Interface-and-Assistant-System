#!/usr/bin/env python3
"""
Friday AI (PyQt6)
Run this to launch the sleek black-and-white Friday chat UI.
"""
import sys

def main() -> int:
    try:
        from qt_friday_ui import show_friday_qt
    except Exception as e:
        print("Failed to import UI:", e)
        return 1
    try:
        return show_friday_qt()
    except Exception as e:
        print("Runtime error:", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())


