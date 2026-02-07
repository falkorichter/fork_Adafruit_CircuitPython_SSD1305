#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
End-to-end test for WebSocket terminal streaming using Playwright.

This script:
1. Starts the WebSocket demo server
2. Opens the HTML viewer in a browser
3. Captures screenshots of the streaming terminal output
4. Verifies that data is being streamed correctly
"""

import asyncio
import subprocess
import sys
import time
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: Playwright not installed")
    print("=" * 60)
    print("\nThis test requires Playwright for browser automation.")
    print("\nTo install Playwright, run:")
    print("    pip install playwright")
    print("    playwright install chromium")
    print("=" * 60 + "\n")
    sys.exit(1)


async def test_websocket_e2e():  # noqa: PLR0914 - Test function with multiple steps
    """End-to-end test of WebSocket terminal streaming"""
    print("=" * 70)
    print("WebSocket Terminal Streaming - End-to-End Test with Screenshots")
    print("=" * 70)
    
    # Start the demo server in the background
    print("\n[1/5] Starting WebSocket demo server...")
    server_process = subprocess.Popen(
        [sys.executable, "examples/demo_websocket_streaming.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Wait for server to start
    print("      Waiting for server to initialize...")
    time.sleep(3)
    
    try:
        # Check if server is still running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"Server failed to start:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            return False
        
        print("      ✓ Server started successfully")
        
        # Launch browser and test
        print("\n[2/5] Launching browser with Playwright...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 1024}
            )
            page = await context.new_page()
            
            print("      ✓ Browser launched")
            
            # Navigate to the HTML viewer
            print("\n[3/5] Opening WebSocket terminal viewer...")
            html_path = Path(__file__).parent.parent / "examples/websocket_terminal_viewer.html"
            file_url = f"file://{html_path.absolute()}?ws_host=localhost&ws_port=8765"
            
            await page.goto(file_url)
            print(f"      ✓ Loaded: {html_path.name}")
            
            # Wait for connection
            print("\n[4/5] Waiting for WebSocket connection and data...")
            await asyncio.sleep(2)
            
            # Take initial screenshot
            screenshots_dir = Path(__file__).parent.parent / "screenshots"
            screenshots_dir.mkdir(exist_ok=True)
            
            screenshot1_path = screenshots_dir / "websocket_initial.png"
            await page.screenshot(path=str(screenshot1_path))
            print(f"      ✓ Screenshot 1: {screenshot1_path.name}")
            
            # Wait for some data to stream
            await asyncio.sleep(3)
            
            # Take screenshot after data streaming
            screenshot2_path = screenshots_dir / "websocket_streaming.png"
            await page.screenshot(path=str(screenshot2_path))
            print(f"      ✓ Screenshot 2: {screenshot2_path.name}")
            
            # Check for status indicator
            print("\n[5/5] Verifying WebSocket connection status...")
            status_text = await page.text_content("#statusText")
            print(f"      Status: {status_text}")
            
            # Check if connected
            status_indicator = await page.query_selector("#statusIndicator.connected")
            if status_indicator:
                print("      ✓ WebSocket connected successfully")
            else:
                print("      ✗ WebSocket not connected")
                return False
            
            # Check terminal output
            terminal_output = await page.text_content("#output")
            if terminal_output and len(terminal_output.strip()) > 100:
                print(f"      ✓ Terminal output received ({len(terminal_output)} characters)")
                
                # Take final screenshot with full output
                screenshot3_path = screenshots_dir / "websocket_full_output.png"
                await page.screenshot(path=str(screenshot3_path), full_page=True)
                print(f"      ✓ Screenshot 3: {screenshot3_path.name} (full page)")
                
                # Print a sample of the output
                sample = terminal_output[:200].replace('\n', ' ')
                print(f"      Sample output: {sample}...")
            else:
                print("      ✗ No terminal output received")
                return False
            
            await browser.close()
        
        print("\n" + "=" * 70)
        print("✓ End-to-End Test PASSED")
        print("=" * 70)
        print(f"\nScreenshots saved to: {screenshots_dir.absolute()}")
        print("  1. websocket_initial.png - Initial connection")
        print("  2. websocket_streaming.png - After 3 seconds of streaming")
        print("  3. websocket_full_output.png - Full page with complete output")
        print("=" * 70)
        
        return True
        
    finally:
        # Clean up server process
        print("\nCleaning up...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("✓ Server stopped")
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("✓ Server killed")


async def main():
    """Main entry point"""
    try:
        success = await test_websocket_e2e()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
