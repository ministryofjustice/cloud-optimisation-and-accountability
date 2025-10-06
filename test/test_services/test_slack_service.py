from unittest.mock import MagicMock
import pytest
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient
from services.slack_service import SlackService


class TestSlackService:

    def test_init_slack_service(self):
        service = SlackService("test_slack_token")
        assert isinstance(service.slack_client, WebClient)

    def send_alert_to_operations_engineering_success(self, mocker):

        mock_slack_client = mocker.Mock()
        mock_slack_client.chat_postMessage.return_value = {"ok": True}
        mocker.patch("services.slack_service.WebClient", return_value=mock_slack_client)

        service = SlackService("test-token")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "test message"
                }
            }
        ]
        service._send_alert_to_coat_notifications(blocks)

        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel=SlackService.COAT_NOTIFICATIONS_CHANNEL_ID,
            mrkdown=True,
            blocks=blocks
        )

    def test_send_alert_to_operations_engineering_error(self, mocker):

        mock_response = MagicMock()
        error_dict = {"error": "invalid_auth"}
        mock_response.__getitem__.side_effect = lambda key: error_dict[key]
        slack_error = SlackApiError("Auth error", response=mock_response)
        mock_slack_client = mocker.Mock()
        mock_slack_client.chat_postMessage.side_effect = slack_error
        mocker.patch("services.slack_service.WebClient", return_value=mock_slack_client)

        service = SlackService("fake-token")
        with pytest.raises(SlackApiError) as err:
            service._send_alert_to_coat_notifications([
               {"type": "section",
                "text": {"type": "mrkdwn", "text": "Test message"}}])

        assert "Auth error" in str(err.value)

    def test__create_block_with_message(self):

        service = SlackService("fake-token")
        block = service._create_block_with_message("test_message")

        assert isinstance(block, list)
        assert block[0]["type"] == "section"
        assert block[0]["text"]["text"] == "test_message"

    def test_send_nonprod_resource_wastage_alerts(self, mocker):

        mock_slack_client = mocker.Mock()
        mock_slack_client.chat_postMessage.return_value = {"ok": True}
        mocker.patch("services.slack_service.WebClient", return_value=mock_slack_client)

        service = SlackService("dummy-token")

        db_wastage_ns = ["namespace1, namespace2"]
        pod_wastage_ns = ["namespace3, namespace4"]

        service.send_nonprod_resource_wastage_alerts(db_wastage_ns, pod_wastage_ns)

        expected_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*⚠️ Resource wastage detected in CP nonprod environments*"
                    }
                },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"📌*{len(db_wastage_ns)} RDS instances not configured to shut "
                        "down outside of work hours in the following namespaces:*\n"
                        f"{db_wastage_ns}"
                    )
                    }
                },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"📌*{len(pod_wastage_ns)} POD instances without scheduled "
                        "downtime when the database is turned off at night in "
                        "the following namespaces:*\n"
                        f"{pod_wastage_ns}"
                    )
                    }
                }
            ]
        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel=SlackService.COAT_NOTIFICATIONS_CHANNEL_ID,
            mrkdown=True,
            blocks=expected_blocks
        )
