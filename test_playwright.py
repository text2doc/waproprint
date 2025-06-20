#!/usr/bin/env python3
# Test script to verify Playwright installation

try:
    import pkg_resources
    import playwright
    from playwright.sync_api import sync_playwright
    print("Successfully imported playwright.sync_api")
    
    # Get version using pkg_resources
    try:
        version = pkg_resources.get_distribution('playwright').version
        print(f"Playwright package version: {version}")
    except Exception as e:
        print(f"Could not determine Playwright version: {e}")
    
    # Test creating a browser instance
    print("Testing browser launch...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Successfully launched browser and created page")
        browser.close()
        
except ImportError as e:
    print(f"Failed to import playwright: {e}")
    print("Python path:")
    import sys
    print("\n".join(sys.path))
except Exception as e:
    print(f"Error during Playwright test: {e}")
    import traceback
    traceback.print_exc()
