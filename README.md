# Mattress Price Tracker 🛏️

This Streamlit application automates the process of checking and tracking the price of a specific mattress from the Dreams.co.uk website. It uses Selenium to navigate the product page, select user-defined options (size, comfort, etc.), and retrieve the accurate price.

The app features both manual and scheduled price checks, logs the price history to a local CSV file, and sends push notifications for scheduled updates.

## Features

* **Automated Browser Interaction**: Uses Selenium to select specific product options (e.g., size, comfort grade) to get the correct price.
* **Manual Price Check**: Instantly check the current price with the click of a button.
* **Scheduled Monitoring**: Automatically checks the price every Wednesday at 9 am.
* **Price History Logging**: Saves every price check with a timestamp to a `price_history.csv` file.
* **Push Notifications**: Sends a notification to your phone or desktop via the free `ntfy.sh` service after each scheduled check.
* **Web Interface**: Built with Streamlit for an easy-to-use interface accessible from your browser.

## How to Use

#### 1. Prerequisites

* Python 3.7+
* Google Chrome browser installed

#### 2. Install Dependencies

Install the required dependencies:

```sh
pip install -r requirements.txt
```

#### 3. Configure the App

Open `app.py` and modify the following variables at the top of the file:

* `PRODUCT_URL`: The URL of the product page you want to track.
* `NTFY_TOPIC`: A unique topic name for your `ntfy.sh` push notifications. Make it something private and memorable.
* `DESIRED_SIZE`, `DESIRED_COMFORT`, `DESIRED_ZIPPED`: The specific product options you want the script to select.

#### 4. Set Up Notifications

1.  Download the **ntfy** app on your phone (iOS or Android) or visit `https://ntfy.sh/` on your desktop.
2.  Subscribe to the same topic name you set for `NTFY_TOPIC` in the `app.py` file.

#### 5. Run the Application

Execute the following command in your terminal:

```sh
streamlit run app.py
```

Your web browser will open a new tab at `http://localhost:8501`, where you can interact with the application.

## How It Works

* **Web Scraping**: Selenium and `webdriver-manager` are used to launch a headless Chrome browser, navigate to the product page, accept cookies, and click the buttons corresponding to the desired mattress options.
* **Scheduling**: The `schedule` library runs a background thread to trigger the price check function at the specified time.
* **Data Persistence**: `pandas` is used to manage the price history, reading from and appending to `price_history.csv`.
* **Frontend**: `streamlit` provides the web interface, including the "Check Price Now" button and the data table displaying the price history.
