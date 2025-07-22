import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, expect

app_url = os.getenv("APP_URL")
if app_url is None:
    raise ValueError("APP_URL environment variable is not set or empty.")


def visit_url(url: str):
    """Uses Playwright to visit a single URL and check for expected text content."""
    print(f"Attempting to visit: {url}")
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Navigate to the page
            response = page.goto(url, timeout=120000)  # 2-minute timeout for navigation

            # Check if the HTTP response itself was successful
            if not response or not response.ok:
                print(
                    f"❌ Received a non-OK HTTP status: {response.status if response else 'N/A'} for {url}"
                )
                # Exit this attempt if the page didn't load correctly
                sys.exit(1)

            # Use expect to wait for the body to contain the target text.
            # This is robust as it polls the page until the text appears or the timeout is reached.
            expect(page.locator("body")).to_contain_text(
                '"latestPrice"', timeout=60000  # 1-minute timeout for text presence
            )

            print(f"✅ Successfully loaded and found indicator on: {url}")

        except PlaywrightTimeoutError as e:
            print(f"❌ Timed out waiting for 'latestPrice' text on: {url}. Error: {e}")
            # Save artifacts for debugging this specific failure case
            page.screenshot(path=f"debug_screenshot_{url.split('/')[2]}.png")
            with open(
                f"debug_page_{url.split('/')[2]}.html", "w", encoding="utf-8"
            ) as f:
                f.write(page.content())
            print("   Saved debug screenshot and HTML file for inspection.")
            sys.exit(1)  # Exit with an error code to make the GitHub Action fail clearly
        except Exception as e:
            print(f"❌ An unexpected error occurred for {url}: {e}")
            sys.exit(1)  # Exit with an error code
        finally:
            if browser:
                browser.close()


if __name__ == "__main__":
    visit_url(app_url)
