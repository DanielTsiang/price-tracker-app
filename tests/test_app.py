from datetime import datetime, time
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest
import requests
from sqlalchemy.exc import SQLAlchemyError

from app import (
    NTFY_TOPIC,
    PRODUCT_URL,
    get_latest_price,
    get_mattress_price,
    init_database,
    load_schedule,
    london_tz,
    main,
    run_price_check_job,
    save_schedule,
    send_nfty_notification,
    update_price_history,
)

@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine for testing."""
    engine = Mock()
    connection = Mock()
    context_manager = Mock()
    context_manager.__enter__ = Mock(return_value=connection)
    context_manager.__exit__ = Mock(return_value=None)
    engine.connect.return_value = context_manager
    return engine, connection


class TestDatabaseOperations:
    """Tests for database-related functions."""

    def test_init_database_success(self, mock_engine):
        """Test successful database initialization."""
        engine, connection = mock_engine

        init_database(engine)

        # Verify all expected SQL statements were executed
        assert connection.execute.call_count == 3
        connection.commit.assert_called_once()

    def test_init_database_failure(self, mock_engine):
        """Test database initialization failure."""
        engine, connection = mock_engine
        connection.execute.side_effect = SQLAlchemyError("Database error")

        with patch("streamlit.error") as mock_error, patch(
            "streamlit.stop"
        ) as mock_stop:
            init_database(engine)
            mock_error.assert_called_once()
            mock_stop.assert_called_once()

    def test_save_schedule_success(self, mock_engine):
        """Test successful schedule saving."""
        engine, connection = mock_engine
        test_time = time(14, 30)

        save_schedule(engine, test_time, True)

        connection.execute.assert_called_once()
        connection.commit.assert_called_once()

    def test_save_schedule_failure(self, mock_engine):
        """Test schedule saving failure."""
        engine, connection = mock_engine
        connection.execute.side_effect = Exception("Save failed")
        test_time = time(14, 30)

        with patch("streamlit.error") as mock_error:
            save_schedule(engine, test_time, True)
            mock_error.assert_called_once()

    def test_load_schedule_success(self, mock_engine):
        """Test successful schedule loading."""
        engine, connection = mock_engine
        mock_result = Mock()
        mock_result.check_time = time(9, 0)
        mock_result.is_enabled = True
        connection.execute.return_value.first.return_value = mock_result

        loaded_time, loaded_enabled = load_schedule(engine)

        assert loaded_time == time(9, 0)
        assert loaded_enabled is True

    def test_load_schedule_no_data(self, mock_engine):
        """Test schedule loading when no data exists."""
        engine, connection = mock_engine
        connection.execute.return_value.first.return_value = None

        loaded_time, loaded_enabled = load_schedule(engine)

        assert loaded_time == time(9, 0)
        assert loaded_enabled is True

    def test_load_schedule_failure(self, mock_engine):
        """Test schedule loading failure."""
        engine, connection = mock_engine
        connection.execute.side_effect = Exception("Load failed")

        with patch("streamlit.error") as mock_error:
            loaded_time, loaded_enabled = load_schedule(engine)
            mock_error.assert_called_once()
            assert loaded_time == time(9, 0)
            assert loaded_enabled is True


class TestPriceFetching:
    """Tests for price fetching functionality."""

    @patch("requests.get")
    def test_get_mattress_price_success(self, mock_get):
        """Test successful price fetching."""
        mock_response = Mock()
        mock_response.json.return_value = {"productData": {"price": {"value": "1399"}}}
        mock_get.return_value = mock_response

        price = get_mattress_price()

        assert price == 1399
        mock_get.assert_called_once_with(PRODUCT_URL, timeout=15)
        mock_response.raise_for_status.assert_called_once()

    @patch("requests.get")
    def test_get_mattress_price_request_failure(self, mock_get):
        """Test price fetching with request failure."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with patch("streamlit.error") as mock_error:
            price = get_mattress_price()

            assert price is None
            mock_error.assert_called_once()

    @patch("requests.get")
    def test_get_mattress_price_parse_failure(self, mock_get):
        """Test price fetching with JSON parsing failure."""
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_get.return_value = mock_response

        with patch("streamlit.error") as mock_error:
            price = get_mattress_price()

            assert price is None
            mock_error.assert_called_once()

    @patch("requests.get")
    def test_get_mattress_price_invalid_value(self, mock_get):
        """Test price fetching with invalid price value."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "productData": {"price": {"value": "invalid"}}
        }
        mock_get.return_value = mock_response

        with patch("streamlit.error") as mock_error:
            price = get_mattress_price()

            assert price is None
            mock_error.assert_called_once()


class TestGetLatestPrice:
    """Tests for get_latest_price functionality."""

    def test_get_latest_price_success(self, mock_engine):
        """Test successful latest price retrieval."""
        engine, connection = mock_engine

        # Mock database result
        mock_result = Mock()
        mock_result.Price = 1399.99
        mock_result.created_at = datetime(
            2025, 6, 15, 14, 30, 45, tzinfo=ZoneInfo("Europe/London")
        )
        connection.execute.return_value.first.return_value = (
            mock_result.Price,
            mock_result.created_at,
        )

        result = get_latest_price(engine)

        assert "latestPrice" in result
        assert result["latestPrice"] == 1399.99
        assert "timestamp" in result
        assert result["timestamp"] == "Sunday 15 June 2025 at 02:30 PM BST"

    def test_get_latest_price_no_data(self, mock_engine):
        """Test latest price retrieval when no data exists."""
        engine, connection = mock_engine
        connection.execute.return_value.first.return_value = None

        result = get_latest_price(engine)

        assert result == {"error": "No price history found"}

    def test_get_latest_price_database_error(self, mock_engine):
        """Test latest price retrieval with database error."""
        engine, connection = mock_engine
        connection.execute.side_effect = Exception("Database error")

        result = get_latest_price(engine)

        assert "error" in result
        assert result["error"] == "Failed to retrieve latest price from the database."


class TestPriceHistoryUpdate:
    """Tests for price history update functionality."""

    @patch("pandas.DataFrame.to_sql")
    @patch("app.datetime")
    def test_update_price_history_success(
        self, mock_datetime, mock_to_sql, mock_engine
    ):
        """Test successful price history update."""
        mock_now = datetime(2024, 7, 21, 22, 30, 45, tzinfo=london_tz)
        mock_datetime.now.return_value = mock_now
        engine, connection = mock_engine

        result = update_price_history(1399, engine)

        assert result is True
        mock_datetime.now.assert_called_once_with(tz=london_tz)
        mock_to_sql.assert_called_once_with(
            "price_history", con=engine, if_exists="append", index=False
        )

    @patch("pandas.DataFrame.to_sql")
    def test_update_price_history_failure(self, mock_to_sql, mock_engine):
        """Test price history update failure."""
        mock_to_sql.side_effect = Exception("Database error")
        engine, connection = mock_engine

        with patch("streamlit.error") as mock_error:
            result = update_price_history(1399, engine)

            assert result is False
            mock_error.assert_called_once()


class TestNotifications:
    """Tests for notification functionality."""

    @patch("requests.post")
    def test_send_ntfy_notification_success(self, mock_post):
        """Test successful notification sending."""
        send_nfty_notification(1399)

        mock_post.assert_called_once_with(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data="The mattress price is now £1399.00".encode(encoding="utf-8"),
            headers={
                "Title": "Mattress Price Alert",
                "Priority": "high",
                "Tags": "bed,money",
            },
        )

    @patch("requests.post")
    def test_send_ntfy_notification_failure(self, mock_post):
        """Test notification sending failure."""
        mock_post.side_effect = Exception("Network error")

        with patch("streamlit.error") as mock_error:
            send_nfty_notification(1399)
            mock_error.assert_called_once()


class TestPriceCheckJob:
    """Tests for the main price check job."""

    @patch("app.send_nfty_notification")
    @patch("app.update_price_history")
    @patch("app.get_mattress_price")
    def test_run_price_check_job_success(
        self, mock_get_price, mock_update_history, mock_send_notification, mock_engine
    ):
        """Test successful price check job execution."""
        mock_get_price.return_value = 1399
        mock_update_history.return_value = True
        engine, connection = mock_engine

        with patch("streamlit.toast") as mock_toast:
            run_price_check_job(engine)

            mock_get_price.assert_called_once()
            mock_update_history.assert_called_once_with(1399, engine)
            mock_send_notification.assert_called_once_with(1399)
            mock_toast.assert_called_once_with(
                "✅ Price updated: £1399.00. Notification sent!"
            )

    @patch("app.get_mattress_price")
    def test_run_price_check_job_price_fetch_failure(self, mock_get_price, mock_engine):
        """Test price check job when price fetching fails."""
        mock_get_price.return_value = None
        engine, connection = mock_engine

        with patch("streamlit.toast") as mock_toast:
            run_price_check_job(engine)

            mock_toast.assert_called_once_with("🚨 Failed to retrieve price.")

    @patch("app.update_price_history")
    @patch("app.get_mattress_price")
    def test_run_price_check_job_database_update_failure(
        self, mock_get_price, mock_update_history, mock_engine
    ):
        """Test price check job when database update fails."""
        mock_get_price.return_value = 1399
        mock_update_history.return_value = False
        engine, connection = mock_engine

        with patch("streamlit.toast") as mock_toast:
            run_price_check_job(engine)

            mock_toast.assert_called_once_with("🚨 Failed to update database.")


class TestDataFrameOperations:
    """Tests for DataFrame operations in price history updates."""

    @patch("pandas.DataFrame")
    @patch("app.datetime")
    def test_price_history_dataframe_structure(
        self, mock_datetime, mock_dataframe, mock_engine
    ):
        """Test that the DataFrame is structured correctly for price history."""
        mock_now = datetime(2024, 1, 15, 14, 30, 45, tzinfo=london_tz)
        mock_datetime.now.return_value = mock_now
        engine, connection = mock_engine

        # Mock DataFrame instance
        mock_df_instance = Mock()
        mock_dataframe.return_value = mock_df_instance

        update_price_history(1399.00, engine)

        # Verify DataFrame was created with correct data structure
        expected_data = {
            "Date": ["2024-01-15"],
            "Time": ["14:30:45"],
            "Price": [1399.00],
        }
        mock_dataframe.assert_called_once_with(expected_data)

        # Verify to_sql was called with correct parameters
        mock_df_instance.to_sql.assert_called_once_with(
            "price_history", con=engine, if_exists="append", index=False
        )


class TestAPIEndpoints:
    """Tests for API endpoints functionality."""

    @patch("streamlit.query_params")
    @patch("streamlit.json")
    def test_health_endpoint(self, mock_json, mock_query_params):
        """Test health endpoint returns correct response."""
        mock_query_params.get.return_value = "health"

        main()

        mock_json.assert_called_once_with({"health": "green"})

    @patch("streamlit.query_params")
    @patch("streamlit.json")
    @patch("app.get_latest_price")
    def test_latest_price_endpoint_success(
        self, mock_get_latest_price, mock_json, mock_query_params
    ):
        """Test latestPrice endpoint returns price data."""
        mock_query_params.get.return_value = "latestPrice"
        mock_get_latest_price.return_value = {
            "latestPrice": 1399.99,
            "timestamp": "Monday 15 January 2024 at 02:30 PM GMT",
        }

        main()

        mock_json.assert_called_once_with(
            {
                "latestPrice": 1399.99,
                "timestamp": "Monday 15 January 2024 at 02:30 PM GMT",
            }
        )

    @pytest.mark.parametrize("endpoint_param", ["unknown_endpoint", None])
    @patch("streamlit.query_params")
    @patch("streamlit.set_page_config")
    def test_unknown_or_no_endpoint_continues_to_main_app(
            self, mock_set_page_config, mock_query_params, endpoint_param
    ):
        """Test that when an unknown endpoint or no endpoint is specified, the main app UI loads."""
        mock_query_params.get.return_value = endpoint_param

        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.schedule_time = time(9, 0)
        mock_session_state.schedule_enabled = True
        mock_session_state.last_run_key = None

        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)

        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)

        # Mock other dependencies to prevent full app execution
        with patch("app.get_database_engine") as mock_get_engine, \
                patch("streamlit.columns") as mock_columns, \
                patch("app.load_schedule") as mock_load_schedule, \
                patch("streamlit.session_state", mock_session_state):
            mock_engine = Mock()
            mock_get_engine.return_value = mock_engine
            mock_load_schedule.return_value = (time(9, 0), True)

            mock_columns.return_value = [mock_col1, mock_col2]

            main()

            # Verify the main app setup was called
            mock_set_page_config.assert_called_once_with(
                page_title="Mattress Price Tracker", page_icon="🛏️", layout="wide"
            )
