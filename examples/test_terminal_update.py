#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Test script to verify terminal update behavior.
This helps debug ANSI escape code compatibility across different terminals.
"""

import time


def test_save_restore_cursor():
    """Test save/restore cursor method (less compatible)"""
    print("Test 1: Save/Restore Cursor Method")
    print("=" * 50)
    print("Header line 1")
    print("Header line 2")
    print()
    
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"
    CLEAR_FROM_CURSOR = "\033[0J"
    
    print(SAVE_CURSOR, end="", flush=True)
    
    for i in range(5):
        print(RESTORE_CURSOR + CLEAR_FROM_CURSOR, end="", flush=True)
        print(f"Update {i}: {time.strftime('%H:%M:%S')}")
        print(f"Counter: {i}")
        time.sleep(1)
    
    print("\n")


def test_cursor_positioning():
    """Test cursor positioning method (more compatible)"""
    print("Test 2: Cursor Positioning Method")
    print("=" * 50)
    print("Header line 1")
    print("Header line 2")
    print()
    
    # Calculate starting line (current line number)
    # We've printed 4 lines of header
    header_lines = 4
    
    for i in range(5):
        # Move to line after header and clear to end
        print(f"\033[{header_lines + 1};0H\033[0J", end="", flush=True)
        print(f"Update {i}: {time.strftime('%H:%M:%S')}")
        print(f"Counter: {i}")
        time.sleep(1)
    
    print("\n")


def test_clear_screen():
    """Test clear screen and home method (most compatible)"""
    print("Test 3: Clear Screen Method")
    print("=" * 50)
    
    for i in range(5):
        # Clear screen and move to home
        print("\033[2J\033[H", end="", flush=True)
        print("Test 3: Clear Screen Method")
        print("=" * 50)
        print(f"Update {i}: {time.strftime('%H:%M:%S')}")
        print(f"Counter: {i}")
        time.sleep(1)
    
    print("\n")


def main():
    """Run all tests"""
    print("Terminal Update Compatibility Test")
    print("=" * 50)
    print("This script tests different ANSI escape code methods.")
    print("Observe which method updates in place on your terminal.")
    print()
    input("Press Enter to start Test 1 (Save/Restore)...")
    
    test_save_restore_cursor()
    
    input("Press Enter to start Test 2 (Cursor Positioning)...")
    test_cursor_positioning()
    
    input("Press Enter to start Test 3 (Clear Screen)...")
    test_clear_screen()
    
    print("Tests completed!")
    print("\nWhich test worked best on your terminal?")
    print("Test 1: Save/Restore Cursor")
    print("Test 2: Cursor Positioning")
    print("Test 3: Clear Screen")


if __name__ == "__main__":
    main()
