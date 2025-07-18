# Mattress Price Tracker 🛏️

This Streamlit application automates the process of checking and tracking the price of a specific mattress from the Dreams.co.uk website. It uses Selenium to navigate the product page, select user-defined options (size, comfort, etc.), and retrieve the accurate price.

The app features both manual and scheduled price checks, logs the price history to a local CSV file, and sends push notifications for scheduled updates. The entire scheduling and checking process is handled within the Streamlit framework.

## Features

* **Automated Browser Interaction**: Uses Selenium to select specific product options (e.g., size, comfort grade) to get the correct price.
* **Manual Price Check**: Instantly check the current price with the click of a button.
* **User-Configurable Scheduling**: Set a daily time for the app to automatically check the price.
* **Enable/Disable Schedule**: Easily toggle the daily scheduled check on or off from the UI (it's on by default).
* **Easy Notification Setup**: The app provides the direct subscription URL for notifications in the UI.
* **Price History Logging**: Saves every price check with a timestamp to a `price_history.csv` file.
* **Push Notifications**: Sends a notification to your phone or desktop via the free `ntfy.sh` service after each price check.
* **Simple Web Interface**: Built with Streamlit for an easy-to-use interface accessible from your browser.

## How to Use

#### 1. Prerequisites

* Python 3.9+
* Google Chrome browser installed

#### 2. Install Dependencies

Install the required dependencies from the `requirements.txt` file:

```
pip install -r requirements.txt
```

#### 3. Configure the App

Open the Python `app.py` script and modify the following variables at the top of the file (if needed):

* `PRODUCT_URL`: The URL of the product page you want to track.
* `NTFY_TOPIC`: A unique topic name for your `ntfy.sh` push notifications.
* `DESIRED_SIZE`, `DESIRED_COMFORT`, `DESIRED_ZIPPED`: The specific product options.

#### 4. Run the Application

You can run the application in two ways:

**Option A: From the Terminal (Standard)**

Execute the following command in your terminal:

```
streamlit run app.py
```

**Option B: For Debugging in an IDE (e.g., PyCharm)**

To run the app in a way that allows you to use your IDE's debugger, run `run_debug.py` from your IDE. This will start the Streamlit server and allow you to set breakpoints and debug your `app.py` script as you would with any other Python program.

Your web browser will open a new tab at `http://localhost:8501`.

#### 5. Set Up Notifications & Schedule

1.  Once the app is running, look at the sidebar.
2.  Under **Notifications**, you will find the full URL to subscribe to. Click the link or use the URL in the ntfy app (iOS/Android/Web) to receive alerts.
3.  Under **Scheduler Settings**, enable the daily check and set your desired time.

## How It Works

* **Web Scraping**: Selenium and `webdriver-manager` are used to launch a headless Chrome browser, navigate to the product page, accept cookies, and click the buttons corresponding to the desired mattress options.
* **Scheduling**: The app uses a Streamlit `@st.fragment(run_every="10s")`. This function runs every 10 seconds, and if scheduling is enabled, it compares the current time with the user-defined schedule. If the times match, it triggers the price check job. `st.session_state` is used to ensure the job only runs once per scheduled minute.
* **Data Persistence**: `pandas` is used to manage the price history in `price_history.csv`. The daily schedule (time and enabled status) is persisted in `schedule.json`.
* **Frontend**: `streamlit` provides the web interface, including the "Check Price Now" button, the schedule controls, the notification link, and the data table displaying the price history.
