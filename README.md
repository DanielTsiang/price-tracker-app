# Mattress Price Tracker 🛏️

This Streamlit application automates the process of checking and tracking the price of a specific mattress from the Dreams.co.uk website. It uses the `requests` library to call the website's internal API directly, making it a fast and efficient way to retrieve the accurate price for a specific product configuration.

The app features both manual and scheduled price checks, logs the price history to a PostgreSQL database, and sends push notifications for scheduled updates. The entire scheduling and checking process is handled within the Streamlit framework.

---
## 🚀 Live Application

You can view and use the live, deployed application at the following URLs:

* **Render:** **[https://price-tracker-app-5joo.onrender.com/](https://price-tracker-app-5joo.onrender.com/)**
* **Streamlit Community Cloud:** **[https://price-tracker-mattress.streamlit.app/](https://price-tracker-mattress.streamlit.app/)**

---
## Features

* **Direct API Integration**: Fetches prices directly from the website's backend API, eliminating the need for a browser and making the process faster and more reliable.
* **Manual Price Check**: Instantly check the current price with the click of a button.
* **Persistent Storage**: Uses a PostgreSQL database to store all price history and schedule settings.
* **User-Configurable Scheduling**: Set a daily time for the app to automatically check the price.
* **Enable/Disable Schedule**: Easily toggle the daily scheduled check on or off from the UI.
* **Push Notifications**: Sends a notification to your phone or desktop via the free `ntfy.sh` service after each price check.
* **Health Check Endpoint**: A simple API endpoint for monitoring the app's status.
* **Simple Web Interface**: Built with Streamlit for an easy-to-use interface accessible from your browser.

---
## How to Use

#### 1. Prerequisites

* Python 3.9+
* A PostgreSQL database

#### 2. Install Dependencies

Install the required dependencies from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

#### 3. Configure the App

* **Database URL**: You must set an environment variable named `DATABASE_URL` with the connection string for your PostgreSQL database.
    * Example: `postgresql://user:password@host:port/dbname`
* **App Constants (Optional)**: Open `app.py` and modify variables like `PRODUCT_URL` or `NTFY_TOPIC` if needed.

#### 4. Run the Application

You can run the application in two ways:

**Option A: From the Terminal (Standard)**

```
streamlit run app.py
```

**Option B: For Debugging in an IDE (e.g., PyCharm)**

To run the app in a way that allows you to use your IDE's debugger, run `run_debug.py` from your IDE. This will start the Streamlit server and allow you to set breakpoints and debug your `app.py` script as you would with any other Python program.

Your web browser will open a new tab at `http://localhost:8501`.

#### 5. Set Up Notifications & Schedule

1.  Once the app is running, look at the sidebar.
2.  Under **Notifications**, you will find the full URL to subscribe to. Click the link or use the URL in the ntfy app (iOS/Android/Web) to receive alerts.
3.  Under **Scheduler Settings**, enable the daily check and set your desired time. These settings will be saved to your database.

## How It Works

* **Database Backend**: The app connects to a PostgreSQL database using SQLAlchemy. It manages a `price_history` table for logging prices and a `schedule_settings` table for the UI configuration.
* **Health Check**: Accessing `/?endpoint=health` on the app's URL will return a `{"health": "green"}` JSON response, useful for automated monitoring.
* **Price Retrieval**: The script sends a GET request directly to an internal product API endpoint. It passes the desired mattress specifications as URL parameters and parses the returned JSON to extract the current price.
* **Scheduling**: A Streamlit `@st.fragment(run_every="10s")` function periodically checks if the current time matches the schedule stored in the database.
* **Frontend**: `streamlit` provides the web interface, including the "Check Price Now" button, the schedule controls, the notification link, and the data table displaying the price history.
