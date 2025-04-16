import pytest
import json
from services.github_service import GithubService
from unittest.mock import MagicMock


@pytest.fixture
def mocks_github_service(mocker):
    mock_github = mocker.patch("services.github_service.Github", autospec=True)
    mock_transport = mocker.patch("services.github_service.AIOHTTPTransport")
    mock_client = mocker.patch("services.github_service.Client")
    mock_session = mocker.patch("services.github_service.Session")
    mock_session_instance = mock_session.return_value
    mock_session_instance.headers = {"Authorization": "Bearer test_token", "Accept": "application/vnd.github+json"}
    gh_service = GithubService(org_token="test_token", org_name="test_org")

    return {
        "gh_service": gh_service,
        "github": mock_github,
        "transport": mock_transport,
        "client": mock_client,
        "session": mock_session
        }


class TestGithubService:

    @pytest.fixture(autouse=True)
    def setup(self, mocks_github_service):
        self.gh_service = mocks_github_service["gh_service"]
        self.github = mocks_github_service["github"]
        self.transport = mocks_github_service["transport"]
        self.client = mocks_github_service["client"]
        self.session = mocks_github_service["session"]

    def test_github_service_init(self):

        assert self.gh_service.org_name == "test_org"
        self.github.assert_called_once_with("test_token")
        self.client.assert_called_once()
        self.transport.assert_called_once()
        self.session.assert_called_once()
        assert self.gh_service.github_client_rest_api.headers["Authorization"] == "Bearer test_token"
        assert self.gh_service.github_client_rest_api.headers["Accept"] == "application/vnd.github+json"
        isinstance(self.gh_service.github_client_core_api, MagicMock)

    def test_get_cloud_platform_environments_content(self, mocker):

        mock_response = MagicMock()
        mock_response.status_code = 200
        test_response_data = {"key-test": "value-test"}
        mock_response.content = json.dumps(test_response_data).encode('utf-8')
        mock_get_request = mocker.patch.object(
            self.gh_service.github_client_rest_api, "get", return_value=mock_response)
        results = self.gh_service.get_cloud_platform_environments_content(
            path="test_path")
        assert results == {"key-test": "value-test"}
        mock_get_request.assert_called_with(
            "https://api.github.com/repos/ministryofjustice/cloud-platform-environments/contents/test_path",
            timeout=10)

    def test_get_workflow_run_details_error(self, mocker):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = {"message": "Not Found"}
        mock_get_request = mocker.patch.object(
            self.gh_service.github_client_rest_api, "get", return_value=mock_response)

        with pytest.raises(ValueError) as err:
            self.gh_service.get_cloud_platform_environments_content(
                path="test_path")
        assert str(err.value) == (
            "Failed to get namespaces content from cloud-platform-environments"
        )
        mock_get_request.call_count == 3
        mock_get_request.assert_called_with(
            "https://api.github.com/repos/ministryofjustice/cloud-platform-environments/contents/test_path",
            timeout=10
        )
