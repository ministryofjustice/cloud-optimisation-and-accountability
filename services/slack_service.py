import logging
from textwrap import dedent
from urllib.parse import quote
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError



class SlackService:
    COAT_NOTIFICATIONS_CHANNEL_ID = "C09DXU35H9P"  # coat-notifications
    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    # Added to stop TypeError on instantiation. See https://github.com/python/cpython/blob/d2340ef25721b6a72d45d4508c672c4be38c67d3/Objects/typeobject.c#L4444
    def __new__(cls, *args, **kwargs):
        return super(SlackService, cls).__new__(cls)

    def __init__(self, slack_token: str) -> None:
        self.slack_client = WebClient(slack_token)

    def _send_alert_to_coat_notifications(self, blocks: list[dict]):
        try:
            self.slack_client.chat_postMessage(
                channel=self.COAT_NOTIFICATIONS_CHANNEL_ID,
                mrkdown=True,
                blocks=blocks
            )
        except SlackApiError as e:
            logging.error("Slack API error: {%s}", e.response['error'])
            raise

    def _create_block_with_message(self, message, block_type="section"):
        return [
            {
                "type": block_type,
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]

    def send_nonprod_resource_wastage_alerts(self, db_wastage_ns, pod_wastage_ns):

        message_header = "*⚠️ Resource wastage detected in CP nonprod environments*"
        db_section = f"📌*{len(db_wastage_ns)} RDS instances not configured to shut down outside of work hours in the following namespaces:*\n{db_wastage_ns}"
        pod_section = f"📌*{len(pod_wastage_ns)} POD instances without scheduled downtime when the database is turned off at night in the following namespaces:*\n{pod_wastage_ns}"

        blocks = []
        blocks += self._create_block_with_message(message=message_header)
        blocks.append({"type": "divider"})
        blocks += self._create_block_with_message(message=db_section)
        blocks += self._create_block_with_message(message=pod_section)

        self._send_alert_to_coat_notifications(blocks)
    
    def send_report_with_message(self, file_path: str, message: str, filename: str | None = None):
        try:
            with open(file_path, "rb") as file_content:
                self.slack_client.files_upload(
                    channels=self.COAT_NOTIFICATIONS_CHANNEL_ID,
                    initial_comment=message,
                    file=file_content,
                    filename=filename or file_path
                )
        except SlackApiError as e:
            logging.error("Slack API error: {%s}", e.response['error'])
            raise
