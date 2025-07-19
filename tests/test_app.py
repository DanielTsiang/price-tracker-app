from datetime import datetime, time
from unittest.mock import Mock, patch

import pytest
import requests
from sqlalchemy.exc import SQLAlchemyError

from app import (
    NTFY_TOPIC,
    PRODUCT_URL,
    get_mattress_price,
    init_database,
    load_schedule,
    run_price_check_job,
    save_schedule,
    send_nfty_notification,
    update_price_history,
)


class TestDatabaseOperations:
    """Tests for database-related functions."""

    @pytest.fixture
    def mock_engine(self):
        """Mock SQLAlchemy engine for testing."""
        engine = Mock()
        connection = Mock()
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=connection)
        context_manager.__exit__ = Mock(return_value=None)
        engine.connect.return_value = context_manager
        return engine, connection

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


class TestPriceHistoryUpdate:
    """Tests for price history update functionality."""

    @patch("pandas.DataFrame.to_sql")
    @patch("app.datetime")
    def test_update_price_history_success(self, mock_datetime, mock_to_sql):
        """Test successful price history update."""
        mock_now = datetime(2024, 1, 15, 14, 30, 45)
        mock_datetime.now.return_value = mock_now

        engine = Mock()

        result = update_price_history(1399, engine)

        assert result is True
        mock_to_sql.assert_called_once_with(
            "price_history", con=engine, if_exists="append", index=False
        )

    @patch("pandas.DataFrame.to_sql")
    def test_update_price_history_failure(self, mock_to_sql):
        """Test price history update failure."""
        mock_to_sql.side_effect = Exception("Database error")
        engine = Mock()

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
        self, mock_get_price, mock_update_history, mock_send_notification
    ):
        """Test successful price check job execution."""
        mock_get_price.return_value = 1399
        mock_update_history.return_value = True
        engine = Mock()

        with patch("streamlit.toast") as mock_toast:
            run_price_check_job(engine)

            mock_get_price.assert_called_once()
            mock_update_history.assert_called_once_with(1399, engine)
            mock_send_notification.assert_called_once_with(1399)
            mock_toast.assert_called_once_with(
                "✅ Price updated: £1399.00. Notification sent!"
            )

    @patch("app.get_mattress_price")
    def test_run_price_check_job_price_fetch_failure(self, mock_get_price):
        """Test price check job when price fetching fails."""
        mock_get_price.return_value = None
        engine = Mock()

        with patch("streamlit.toast") as mock_toast:
            run_price_check_job(engine)

            mock_toast.assert_called_once_with("🚨 Failed to retrieve price.")

    @patch("app.update_price_history")
    @patch("app.get_mattress_price")
    def test_run_price_check_job_database_update_failure(
        self, mock_get_price, mock_update_history
    ):
        """Test price check job when database update fails."""
        mock_get_price.return_value = 1399
        mock_update_history.return_value = False
        engine = Mock()

        with patch("streamlit.toast") as mock_toast:
            run_price_check_job(engine)

            mock_toast.assert_called_once_with("🚨 Failed to update database.")


class TestDataFrameOperations:
    """Tests for DataFrame operations in price history updates."""

    @patch("app.datetime")
    def test_price_history_dataframe_structure(self, mock_datetime):
        """Test that the DataFrame is structured correctly for price history."""
        mock_now = datetime(2024, 1, 15, 14, 30, 45)
        mock_datetime.now.return_value = mock_now

        with patch("pandas.DataFrame.to_sql") as mock_to_sql:
            engine = Mock()
            update_price_history(1399, engine)

            # Verify DataFrame was created with correct structure
            call_args = mock_to_sql.call_args
            assert call_args[1]["con"] == engine
            assert call_args[1]["if_exists"] == "append"
            assert call_args[1]["index"] is False
