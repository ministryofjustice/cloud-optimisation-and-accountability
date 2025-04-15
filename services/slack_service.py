import logging
from textwrap import dedent
from urllib.parse import quote
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError



class SlackService:
    OPERATIONS_ENGINEERING_ALERTS_CHANNEL_ID = "C033QBE511V"
    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    # Added to stop TypeError on instantiation. See https://github.com/python/cpython/blob/d2340ef25721b6a72d45d4508c672c4be38c67d3/Objects/typeobject.c#L4444
    def __new__(cls, *args, **kwargs):
        return super(SlackService, cls).__new__(cls)

    def __init__(self, slack_token: str) -> None:
        self.slack_client = WebClient(slack_token)

    def _send_alert_to_operations_engineering(self, blocks: list[dict]):
        try:
            self.slack_client.chat_postMessage(
                channel=self.OPERATIONS_ENGINEERING_ALERTS_CHANNEL_ID,
                mrkdown=True,
                blocks=blocks
            )
        except SlackApiError as e:
            logging.error("Slack API error: {%s}", e.response['error'])

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
        
        formatted_pod_wastage_ns = "\n".join(f"- `{ns}`" for ns in pod_wastage_ns)
        formatted_db_wastage_ns = "\n".join(f"- `{ns}`" for ns in db_wastage_ns)
        message = (
            f"*Resource wastage detected in CP nonprod environments*\n\n"
            f"📌 DB wastage detected in following namespaces.\n\n"
            f"{formatted_db_wastage_ns}" 
            f"📌 POD wastage detected in following namespaces.\n\n"  
            f"{formatted_pod_wastage_ns}"
        )
        blocks = self._create_block_with_message(message)
        self._send_alert_to_operations_engineering(blocks)