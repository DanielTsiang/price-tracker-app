import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Get the URLs from an environment variable, split by comma
app_urls_str = os.getenv("APP_URLS")
if not app_urls_str:
    raise ValueError("APP_URLS environment variable is not set or empty.")

APP_URLS = [url.strip() for url in app_urls_str.split(',')]

# The specific element to wait for, indicating the page has loaded
LOAD_INDICATOR_SELECTOR = 'span:has-text("latestPrice")'

def visit_url(url: str):
    """Uses Playwright to visit a single URL and check for a load indicator."""
    print(f"Attempting to visit: {url}")
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=120000)  # 2-minute timeout for navigation

            # Wait for the specific span element to be visible
            page.wait_for_selector(LOAD_INDICATOR_SELECTOR, state='visible', timeout=60000) # 1-minute timeout
            
            print(f"✅ Successfully loaded and found indicator on: {url}")

        except PlaywrightTimeoutError:
            print(f"❌ Timed out waiting for load indicator on: {url}")
        except Exception as e:
            print(f"❌ An unexpected error occurred for {url}: {e}")
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    for app_url in APP_URLS:
        visit_url(app_url)
