# Mattress Price Tracker 🛏️

This Streamlit application automates the process of checking and tracking the price of a specific mattress from the Dreams.co.uk website. It uses Selenium to navigate the product page, select user-defined options (size, comfort, etc.), and retrieve the accurate price.

The app features both manual and scheduled price checks, logs the price history to a local CSV file, and sends push notifications for scheduled updates. The entire scheduling and checking process is handled within the Streamlit framework.

## Features

* **Automated Browser Interaction**: Uses Selenium to select specific product options (e.g., size, comfort grade) to get the correct price.
* **Manual Price Check**: Instantly check the current price with the click of a button.
* **User-Configurable Scheduling**: Set a daily time for the app to automatically check the price. The schedule is configured directly in the web UI and saved locally.
* **Price History Logging**: Saves every price check with a timestamp to a `price_history.csv` file.
* **Push Notifications**: Sends a notification to your phone or desktop via the free `ntfy.sh` service after each price check.
* **Simple Web Interface**: Built with Streamlit for an easy-to-use interface accessible from your browser.

## How to Use

#### 1. Prerequisites

* Python 3.9+
* Google Chrome browser installed

#### 2. Install Dependencies

Install the required dependencies:

```
pip install -r requirements.txt
```

#### 3. Configure the App

Open app.py and modify the following variables at the top of the file if needed:

* `PRODUCT_URL`: The URL of the product page you want to track.
* `NTFY_TOPIC`: A unique topic name for your `ntfy.sh` push notifications. Make it something private and memorable.
* `DESIRED_SIZE`, `DESIRED_COMFORT`, `DESIRED_ZIPPED`: The specific product options you want the script to select.

#### 4. Set Up Notifications

1. Download the **ntfy** app on your phone (iOS or Android) or visit `https://ntfy.sh/` on your desktop.
2. Subscribe to the same topic name you set for `NTFY_TOPIC` in app.py.

#### 5. Run the Application

Execute the following command in your terminal:

```
streamlit run app.py
```

Your web browser will open a new tab at `http://localhost:8501`. Use the sidebar in the app to set your desired daily check-in time.

## How It Works

* **Web Scraping**: Selenium and `webdriver-manager` are used to launch a headless Chrome browser, navigate to the product page, accept cookies, and click the buttons corresponding to the desired mattress options.
* **Scheduling**: The app uses a Streamlit `@st.fragment(run_every="10s")`. This function runs every 10 seconds to compare the current time with the user-defined schedule saved in `schedule.json`. If the times match, it triggers the price check job. `st.session_state` is used to ensure the job only runs once per scheduled minute.
* **Data Persistence**: `pandas` is used to manage the price history, reading from and appending to `price_history.csv`. The daily schedule is persisted in `schedule.json`.
* **Frontend**: `streamlit` provides the web interface, including the "Check Price Now" button, the schedule time input, and the data table displaying the price history.
