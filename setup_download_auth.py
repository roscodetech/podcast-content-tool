#!/usr/bin/env python3
"""
Setup script for NotebookLM artifact downloads.
Run this once to log in and save the browser profile.
After setup, downloads will work automatically.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import sys
import time

def main():
    profile_dir = Path.home() / '.notebooklm-mcp' / 'playwright_profile'
    profile_dir.mkdir(parents=True, exist_ok=True)

    print("NotebookLM Download Authentication Setup")
    print("=" * 50)
    print(f"Profile directory: {profile_dir}")
    print()

    with sync_playwright() as p:
        print("Launching browser...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            timeout=120000
        )

        page = context.new_page()

        # Go to NotebookLM
        print("Navigating to NotebookLM...")
        try:
            page.goto('https://notebooklm.google.com', wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f"Navigation note: {e}")

        time.sleep(2)
        current_url = page.url

        if 'accounts.google.com' in current_url or 'signin' in current_url.lower():
            print()
            print("=" * 50)
            print("Please log in to your Google account in the browser window.")
            print()
            print("After you see the NotebookLM home page, come back here")
            print("and press Enter to save the profile and continue...")
            print("=" * 50)

            try:
                input()
            except EOFError:
                print("Waiting 60 seconds for login...")
                time.sleep(60)

            time.sleep(2)

        # Check current state
        try:
            current_url = page.url
            print(f"Current URL: {current_url[:60]}...")
        except:
            pass

        print()
        print("Profile saved!")
        print("Closing browser...")

        try:
            context.close()
        except:
            pass

    print()
    print("=" * 50)
    print("Setup complete!")
    print("You can now run the podcast automation script.")
    print("=" * 50)


if __name__ == '__main__':
    main()
