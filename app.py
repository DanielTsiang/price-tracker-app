import json
import logging
import time as thread_time  # Use alias for sleep
from datetime import datetime, time

import pandas as pd
import requests
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- Basic Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
PRODUCT_URL: str = "https://www.dreams.co.uk/flaxby-oxtons-guild-pocket-sprung-mattress/p/131-01043-configurable"
CSV_FILE: str = "price_history.csv"
SCHEDULE_FILE: str = "schedule.json"
NTFY_TOPIC: str = "mattress-price-tracker-flaxby"

# Desired mattress specifications
DESIRED_SIZE: str = "5'0 King"
DESIRED_COMFORT: str = "Very Firm"
DESIRED_ZIPPED: str = "Non Zipped"


# --- Schedule Persistence ---
def save_schedule(time_obj: time, enabled: bool) -> None:
    """Saves the schedule state (time and enabled status) to a JSON file."""
    try:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump({'time': time_obj.strftime("%H:%M"), 'enabled': enabled}, f)
        logger.info(f"Schedule saved: {time_obj.strftime('%H:%M')}, Enabled: {enabled}")
    except Exception as e:
        st.error(f"Failed to save schedule: {e}")
        logger.error(f"Failed to save schedule: {e}")


def load_schedule() -> tuple[time, bool]:
    """Loads schedule from JSON file, returns defaults if not found."""
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
            time_str = data.get('time', '09:00')
            enabled = data.get('enabled', True)  # Default to True if not found
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            return time_obj, enabled
    except (FileNotFoundError, json.JSONDecodeError):
        return time(9, 0), True  # Default to 9 AM, enabled


# --- Web Scraping with Selenium ---
def get_mattress_price() -> float | None:
    """
    Scrapes the Dreams website to get the price of the specified mattress
    by selecting the correct options using Selenium.
    """
    driver: webdriver.Chrome | None = None
    logger.info("Starting browser to check price...")
    try:
        # --- WebDriver Setup ---
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        service: Service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(PRODUCT_URL)
        wait: WebDriverWait = WebDriverWait(driver, 20)

        # 1. Accept cookies
        try:
            cookie_button = wait.until(
                expected_conditions.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_button.click()
            logger.info("Accepted cookies.")
        except TimeoutException:
            logger.info("Cookie banner not found, skipping.")
            pass

        # 2. Select options
        logger.info("Selecting mattress options...")
        size_button = wait.until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, f'//button[.//span[normalize-space(.) = "{DESIRED_SIZE}"]]')))
        driver.execute_script("arguments[0].click();", size_button)
        thread_time.sleep(0.5)

        comfort_button = wait.until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, f'//button[.//span[normalize-space(.) = "{DESIRED_COMFORT}"]]')))
        driver.execute_script("arguments[0].click();", comfort_button)
        thread_time.sleep(0.5)

        zipped_button = wait.until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, f'//button[.//span[normalize-space(.) = "{DESIRED_ZIPPED}"]]')))
        driver.execute_script("arguments[0].click();", zipped_button)
        thread_time.sleep(0.5)
        logger.info("Mattress options selected successfully.")

        # 3. Get Price
        price_element = wait.until(
            expected_conditions.visibility_of_element_located(
                (By.CSS_SELECTOR, '.heading.dreams-product-price__price')))
        price_str: str = price_element.text.strip().replace('£', '').replace(',', '')
        logger.info(f"Successfully scraped price: £{price_str}")

        return float(price_str)

    except Exception as e:
        st.error(f"An error occurred during scraping: {e}")
        logger.error(f"An error occurred during scraping: {e}", exc_info=True)
        return None
    finally:
        if driver:
            driver.quit()
        logger.info("Browser closed.")


# --- CSV Handling ---
def update_price_history(price: float) -> bool:
    """Updates the CSV file with the new price and timestamp."""
    try:
        now: datetime = datetime.now()
        new_entry: pd.DataFrame = pd.DataFrame([[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), price]],
                                               columns=['Date', 'Time', 'Price'])
        try:
            df: pd.DataFrame = pd.read_csv(CSV_FILE)
            df = pd.concat([df, new_entry], ignore_index=True)
        except FileNotFoundError:
            df = new_entry
        df.to_csv(CSV_FILE, index=False)
        logger.info(f"Updated price history with new price: £{price}")
        return True
    except Exception as e:
        st.error(f"Error updating CSV: {e}")
        logger.error(f"Error updating CSV: {e}")
        return False


# --- Notification ---
def send_nfty_notification(price: float) -> None:
    """Sends a push notification using ntfy.sh."""
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
                      data=f"The mattress price is now £{price:.2f}".encode(encoding='utf-8'),
                      headers={"Title": "Mattress Price Alert", "Priority": "high", "Tags": "bed,money"})
        logger.info("Sent ntfy.sh notification.")
    except Exception as e:
        st.error(f"Failed to send notification: {e}")
        logger.error(f"Failed to send notification: {e}")


# --- Core Job Logic ---
def run_price_check_job() -> None:
    """
    This is the main job: it gets the price, updates the history,
    and sends a notification.
    """
    logger.info("Starting price check job...")
    price: float | None = get_mattress_price()
    if price is not None:
        if update_price_history(price):
            send_nfty_notification(price)
            st.toast(f"✅ Price updated: £{price:.2f}. Notification sent!")
            logger.info(f"Job completed: price £{price:.2f} added to CSV and notification sent.")
        else:
            st.toast("🚨 Failed to update CSV file.")
            logger.error(f"Failed to update CSV for price £{price:.2f}")
    else:
        st.toast("🚨 Failed to retrieve price.")
        logger.error("Failed to retrieve price during job execution.")


# --- Streamlit App UI and Logic ---

@st.fragment
def display_price_history():
    """UI fragment to display the price history table."""
    try:
        df: pd.DataFrame = pd.read_csv(CSV_FILE)
        df_sorted: pd.DataFrame = df.sort_values(by=['Date', 'Time'], ascending=False)
        st.dataframe(df_sorted.style.format({'Price': '£{:.2f}'}), use_container_width=True)
    except FileNotFoundError:
        st.info("No price history found. Check the price to start tracking.")
    except Exception as e:
        st.error(f"Could not load price history: {e}")
        logger.error(f"Could not load price history: {e}")


@st.fragment(run_every="10s")
def scheduled_check_fragment():
    """
    This fragment runs every 10 seconds to check if the scheduled time has been reached.
    It uses session_state to ensure the job only runs once per scheduled time.
    """
    # Exit early if the schedule is disabled in the session state
    if not st.session_state.get('schedule_enabled', True):
        return

    scheduled_time = st.session_state.schedule_time
    now = datetime.now()

    # A unique key for the current day and scheduled time
    run_key = f"{now.date()}-{scheduled_time.strftime('%H:%M')}"

    # Check if the time matches and if we haven't already run for this key
    if (now.hour == scheduled_time.hour and
            now.minute == scheduled_time.minute and
            st.session_state.get('last_run_key') != run_key):
        logger.info(f"Scheduled time {scheduled_time.strftime('%H:%M')} reached. Running job.")
        run_price_check_job()
        st.session_state['last_run_key'] = run_key  # Mark as run to prevent re-execution
        st.rerun()  # Rerun the app to update the history table immediately


def main() -> None:
    """The main function for the Streamlit application."""
    st.set_page_config(page_title="Mattress Price Tracker", page_icon="🛏️", layout="wide")
    st.title("Mattress Price Tracker")

    # Initialize session state if not already done
    if 'schedule_time' not in st.session_state:
        scheduled_time, schedule_enabled = load_schedule()
        st.session_state.schedule_time = scheduled_time
        st.session_state.schedule_enabled = schedule_enabled
        st.session_state.last_run_key = None

    # --- Scheduler UI in Sidebar ---
    with st.sidebar:
        st.header("Scheduler Settings")

        def on_schedule_settings_change():
            """Callback to save schedule settings when they are changed."""
            new_time = st.session_state.time_input_widget
            new_enabled_status = st.session_state.schedule_enabled_widget

            # Update session state from widgets
            st.session_state.schedule_time = new_time
            st.session_state.schedule_enabled = new_enabled_status

            # Persist changes to file
            save_schedule(new_time, new_enabled_status)
            st.toast("Schedule settings saved!")

        st.toggle(
            "Enable daily check",
            value=st.session_state.schedule_enabled,
            key="schedule_enabled_widget",
            on_change=on_schedule_settings_change,
            help="Toggle the automatic daily price check on or off."
        )

        st.time_input(
            "Daily check time (24h)",
            value=st.session_state.schedule_time,
            key="time_input_widget",
            on_change=on_schedule_settings_change,
            help="Set the time for the automatic daily price check.",
            disabled=not st.session_state.schedule_enabled
        )

        st.divider()

        st.header("Notifications")
        ntfy_url = f"https://ntfy.sh/{NTFY_TOPIC}"
        st.markdown(f"Subscribe to notifications on your phone or desktop at:")
        st.markdown(f"[{ntfy_url}]({ntfy_url})")

        if st.button("Send Notification Now", help="Sends a notification with the last known price."):
            try:
                df = pd.read_csv(CSV_FILE)
                if not df.empty:
                    last_price = df['Price'].iloc[-1]
                    send_nfty_notification(last_price)
                    st.sidebar.success(f"Notification sent for price: £{last_price:.2f}")
                else:
                    st.sidebar.warning("Price history is empty.")
            except (FileNotFoundError, IndexError):
                st.sidebar.warning("No price history found. Check price first.")

    # --- Main Page Content ---
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"Tracking price for [Flaxby Oxtons Guild Pocket Sprung Mattress]({PRODUCT_URL}).")
        st.write(f"**Specs:** {DESIRED_SIZE}, {DESIRED_COMFORT}, {DESIRED_ZIPPED}")

        if st.button("Check Price Now", type="primary"):
            with st.spinner("Scraping website for current price..."):
                price: float | None = get_mattress_price()
                if price is not None:
                    st.success(f"The current price is £{price:.2f}")
                    update_price_history(price)
                    st.rerun()  # Rerun to update the history table
                else:
                    st.error("Failed to retrieve the price.")

    with col2:
        st.subheader("Price History")
        display_price_history()

    # This fragment will run in the background to check the schedule
    scheduled_check_fragment()


if __name__ == "__main__":
    main()
