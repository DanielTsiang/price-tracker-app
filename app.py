import logging
import os
from datetime import datetime, time

import pandas as pd
import requests
import streamlit as st
from sqlalchemy import Engine, create_engine, text

# --- Basic Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Constants ---
PRODUCT_URL: str = "https://www.dreams.co.uk/flaxby-oxtons-guild-pocket-sprung-mattress/p/135-01363/variant-selector?changedCategoryCode=b2c_comfort_grade&changedCategoryValue=VERY_FIRM&previousProductCode=135-01361"
NTFY_TOPIC: str = "mattress-price-tracker-flaxby"
DATABASE_URL = os.getenv("DATABASE_URL")

# Desired mattress specifications
DESIRED_SIZE: str = "5'0 King"
DESIRED_COMFORT: str = "Very Firm"
DESIRED_ZIPPED: str = "Non Zipped"


# --- Database Setup ---
@st.cache_resource
def get_database_engine() -> Engine:
    """Creates and caches a SQLAlchemy engine."""
    if not DATABASE_URL:
        st.error("DATABASE_URL environment variable is not set. Please configure it.")
        st.stop()
    try:
        return create_engine(DATABASE_URL)
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        st.error(
            f"Could not connect to the database. Please check the DATABASE_URL. Error: {e}"
        )
        st.stop()


def init_database(engine):
    """Initializes the database tables if they don't exist."""
    try:
        with engine.connect() as connection:
            # Create price history table
            connection.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    "Date" DATE NOT NULL,
                    "Time" TIME NOT NULL,
                    "Price" NUMERIC(10, 2) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
                )
            )
            # Create schedule settings table
            connection.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS schedule_settings (
                    id INT PRIMARY KEY,
                    check_time TIME NOT NULL,
                    is_enabled BOOLEAN NOT NULL
                );
            """
                )
            )
            # Ensure a default schedule setting exists
            connection.execute(
                text(
                    """
                INSERT INTO schedule_settings (id, check_time, is_enabled)
                VALUES (1, '09:00:00', TRUE)
                ON CONFLICT (id) DO NOTHING;
            """
                )
            )
            connection.commit()
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        st.error(f"Failed to create tables in the database. Error: {e}")
        st.stop()


# --- Schedule Persistence in database ---
def save_schedule(engine: Engine, time_obj: time, enabled: bool) -> None:
    """Saves the schedule state to the database."""
    try:
        with engine.connect() as connection:
            insert_schedule_statement = text(
                """
                INSERT INTO schedule_settings (id, check_time, is_enabled)
                VALUES (1, :check_time, :is_enabled)
                ON CONFLICT (id) DO UPDATE
                SET check_time = EXCLUDED.check_time,
                    is_enabled = EXCLUDED.is_enabled;
            """
            )
            connection.execute(
                insert_schedule_statement,
                {"check_time": time_obj, "is_enabled": enabled},
            )
            connection.commit()
        logger.info(
            f"Schedule saved to database: {time_obj.strftime('%H:%M')}, Enabled: {enabled}"
        )
    except Exception as e:
        st.error(f"Failed to save schedule to database: {e}")
        logger.error(f"Failed to save schedule to database: {e}")


def load_schedule(engine: Engine) -> tuple[time, bool]:
    """Loads schedule from the database."""
    try:
        with engine.connect() as connection:
            if schedule_setting := connection.execute(
                text(
                    "SELECT check_time, is_enabled FROM schedule_settings WHERE id = 1"
                )
            ).first():
                return schedule_setting.check_time, schedule_setting.is_enabled
            logger.info("No schedule found in the database, using defaults.")
            return time(9, 0), True
    except Exception as e:
        logger.error(f"Failed to load schedule from database: {e}")
        st.error("Could not load schedule from the database. Using defaults.")
        return time(9, 0), True


def get_mattress_price() -> float | None:
    """
    Fetches the price of the specified mattress directly from the Dreams API."""
    logger.info("Calling Dreams API to check price...")

    try:
        response = requests.get(PRODUCT_URL, timeout=15)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        price = data["productData"]["price"]["value"]
        price_float = float(price)

        logger.info(f"Successfully fetched price from API: £{price_float:.2f}")
        return price_float

    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        logger.error(f"API request failed: {e}", exc_info=True)
        return None
    except (KeyError, ValueError) as e:
        st.error(f"Failed to parse price from API response: {e}")
        logger.error(f"Failed to parse price from API response: {e}", exc_info=True)
        return None


# --- Database Handling ---
def update_price_history(price: float, engine: Engine) -> bool:
    """Writes the new price and timestamp to the database."""
    try:
        now: datetime = datetime.now()
        new_entry: pd.DataFrame = pd.DataFrame(
            {
                "Date": [now.strftime("%Y-%m-%d")],
                "Time": [now.strftime("%H:%M:%S")],
                "Price": [price],
            }
        )
        new_entry.to_sql("price_history", con=engine, if_exists="append", index=False)
        logger.info(f"Updated price history in database with new price: £{price}")
        return True
    except Exception as e:
        st.error(f"Error updating database: {e}")
        logger.error(f"Error updating database: {e}")
        return False


# --- Notification ---
def send_nfty_notification(price: float) -> None:
    """Sends a push notification using ntfy.sh."""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=f"The mattress price is now £{price:.2f}".encode(encoding="utf-8"),
            headers={
                "Title": "Mattress Price Alert",
                "Priority": "high",
                "Tags": "bed,money",
            },
        )
        logger.info("Sent ntfy.sh notification.")
    except Exception as e:
        st.error(f"Failed to send notification: {e}")


# --- Core Job Logic ---
def run_price_check_job(engine: Engine) -> None:
    """
    This is the main job: it gets the price, updates the history,
    and sends a notification.
    """
    logger.info("Starting price check job...")
    price: float | None = get_mattress_price()
    if price is None:
        st.toast("🚨 Failed to retrieve price.")

    elif update_price_history(price, engine):
        send_nfty_notification(price)
        st.toast(f"✅ Price updated: £{price:.2f}. Notification sent!")
    else:
        st.toast("🚨 Failed to update database.")


# --- Streamlit App UI and Logic ---
@st.fragment
def display_price_history(engine: Engine):
    """UI fragment to display the price history table from the database."""
    try:
        df = pd.read_sql(
            'SELECT "Date", "Time", "Price" FROM price_history ORDER BY "Date" DESC, "Time" DESC',
            engine,
        )
        st.dataframe(df.style.format({"Price": "£{:.2f}"}), use_container_width=True)
    except Exception as e:
        st.info("No price history found in the database, or an error occurred.")
        logger.error(f"Could not load price history from database: {e}")


@st.fragment(run_every="10s")
def scheduled_check_fragment(engine: Engine):
    """
    This fragment runs every 10 seconds to check if the scheduled time has been reached.
    It uses session_state to ensure the job only runs once per scheduled time.
    """
    # Exit early if the schedule is disabled in the session state
    if not st.session_state.get("schedule_enabled", True):
        return

    scheduled_time = st.session_state.schedule_time
    now = datetime.now()

    # A unique key for the current day and scheduled time
    run_key = f"{now.date()}-{scheduled_time.strftime('%H:%M')}"

    # Check if the time matches and if we haven't already run for this key
    if (
        now.hour == scheduled_time.hour
        and now.minute == scheduled_time.minute
        and st.session_state.get("last_run_key") != run_key
    ):
        logger.info(
            f"Scheduled time {scheduled_time.strftime('%H:%M')} reached. Running job."
        )
        run_price_check_job(engine)
        st.session_state[
            "last_run_key"
        ] = run_key  # Mark as run to prevent re-execution
        st.rerun()  # Rerun the app to update the history table immediately


def main() -> None:
    """The main function for the Streamlit application."""
    # --- Health Check Endpoint ---
    # If the 'endpoint' query parameter is set to 'health', return a JSON response and exit.
    if st.query_params.get("endpoint") == "health":
        st.json({"health": "green"})
        return

    st.set_page_config(
        page_title="Mattress Price Tracker", page_icon="🛏️", layout="wide"
    )

    # Get DB engine and initialize the table
    engine = get_database_engine()
    init_database(engine)

    st.title("Mattress Price Tracker")

    # Initialise session state if not already done
    if "schedule_time" not in st.session_state:
        scheduled_time, schedule_enabled = load_schedule(engine)
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

            # Persist changes
            save_schedule(engine, new_time, new_enabled_status)
            st.toast("Schedule settings saved!")

        st.toggle(
            "Enable daily check",
            value=st.session_state.schedule_enabled,
            key="schedule_enabled_widget",
            on_change=on_schedule_settings_change,
            help="Toggle the automatic daily price check on or off.",
        )

        st.time_input(
            "Daily check time (24h)",
            value=st.session_state.schedule_time,
            key="time_input_widget",
            on_change=on_schedule_settings_change,
            help="Set the time for the automatic daily price check.",
            disabled=not st.session_state.schedule_enabled,
        )

        st.divider()

        st.header("Notifications")
        ntfy_url = f"https://ntfy.sh/{NTFY_TOPIC}"
        st.markdown("Subscribe to notifications on your phone or desktop at:")
        st.markdown(f"[{ntfy_url}]({ntfy_url})")

        if st.button(
            "Send Notification Now",
            help="Sends a notification with the last known price.",
        ):
            try:
                last_price_df = pd.read_sql(
                    'SELECT "Price" FROM price_history ORDER BY created_at DESC LIMIT 1',
                    engine,
                )
                if not last_price_df.empty:
                    last_price = last_price_df["Price"].iloc[0]
                    send_nfty_notification(last_price)
                    st.sidebar.success(
                        f"Notification sent for price: £{last_price:.2f}"
                    )
                else:
                    st.sidebar.warning("Price history is empty.")
            except Exception as e:
                st.sidebar.error(f"Database Error: {e}")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"Tracking price for [Flaxby Oxtons Guild]({PRODUCT_URL}).")
        st.write(f"**Specs:** {DESIRED_SIZE}, {DESIRED_COMFORT}, {DESIRED_ZIPPED}")

        if st.button("Check Price Now", type="primary"):
            with st.spinner("Scraping website for current price..."):
                price = get_mattress_price()
                if price is not None:
                    update_price_history(price, engine)
                    st.rerun()  # Rerun to update the history table
                else:
                    st.error("Failed to retrieve the price.")

    with col2:
        st.subheader("Price History")
        display_price_history(engine)

    # This fragment will run in the background to check the schedule
    scheduled_check_fragment(engine)


if __name__ == "__main__":
    main()
