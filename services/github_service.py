import logging
import json
import re
from calendar import timegm
from time import gmtime, sleep
from typing import Callable, Any
from requests import Session
import github
from github import (Github, RateLimitExceededException)
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportServerError
from retrying import retry


class GithubService:
    def __init__(
        self,
        org_token: str,
        org_name: str = "ministryofjustice",
        enterprise_name: str = "ministry-of-justice-uk"
    ) -> None:
        self.github_client_core_api = Github(org_token)
        self.org_name = org_name
        self.enterprise_name: str = enterprise_name

        self.github_client_gql_api: Client = Client(transport=AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {org_token}"},
        ), execute_timeout=120)
        self.github_client_rest_api = Session()
        self.github_client_rest_api.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {org_token}",
            }
        )

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def get_cloud_platform_environments_content(self, path: str) -> dict:

        logging.info("Retrieving namespaces list from cloud-platform-environments repository")
        response_okay = 200
        url = f"https://api.github.com/repos/ministryofjustice/cloud-platform-environments/contents/{path}"

        response = self.github_client_rest_api.get(url, timeout=10)
        if response.status_code == response_okay:
            logging.info("Namespaces list retrieved successfully from cloud-platform-environments.")
            return json.loads(response.content.decode("utf-8"))
        raise ValueError(
            "Failed to get namespaces list from cloud-platform-environments")