import pytest
import base64
from bin.detect_cp_resource_wastage import _get_environment_variables,_process_namespace, detect_cp_resource_wastage


def encode_content(content: str) -> str:
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")


class TestDetectResourceWastage:

    def test_get_environment_variables(self, mocker):
        mock_getenv = mocker.patch("os.getenv")
        mock_getenv.return_value = "token_mock"

        result = _get_environment_variables()

        assert result == "token_mock"

    def test_get_environment_variables_missing_token(self, mocker):

        mock_getenv = mocker.patch("os.getenv")
        mock_getenv.return_value = None

        with pytest.raises(ValueError) as err:
            _get_environment_variables()

        assert str(err.value) == (
            "The env variable GH_TOKEN is empty or missing"
        )

    def test_process_namespace_no_rds(self, mocker):
        ns = "test_ns_01"
        mock_github_service = mocker.patch("services.github_service.GithubService")
        mock_github_service.get_cloud_platform_environments_content.return_value = [
            {"name": "test-teraform.tf"},
            {"name": "main.tf"}
            ]
        result = _process_namespace(ns, mock_github_service)
        assert result == {"db_waste": None, "pod_waste": None}

    def test_process_namespace_no_rds_auto_start_stop(self, mocker): 
        ns = "test_ns_02"
        mock_github_service = mocker.patch("services.github_service.GithubService")
        mock_github_service.get_cloud_platform_environments_content.side_effect = [
            [{"name": "rds.tf"}],
            {"content": encode_content("test resource content")}
        ]
        result = _process_namespace(ns, mock_github_service)
        assert result == {"db_waste": ns, "pod_waste": None}

    def test_process_namespace_no_pod_scheduled_downtime(self, mocker):
        ns = "test_ns_03"
        mock_github_service = mocker.patch("services.github_service.GithubService")
        mock_github_service.get_cloud_platform_environments_content.side_effect = [
            [{"name": "rds.tf"}],
            {"content": encode_content("enable_rds_auto_start_stop = true")}
        ]
        result = _process_namespace(ns, mock_github_service)
        assert result == {"db_waste": None, "pod_waste": ns}

    def test_process_namespace_rds_and_pod_downtime_scheduled(self, mocker):
        ns = "test_ns_04"
        mock_github_service = mocker.patch("services.github_service.GithubService")
        mock_github_service.get_cloud_platform_environments_content.side_effect = [
            [{"name": "rds.tf"}, {"name": "scheduled-downtime.tf"}],
            {"content": encode_content("enable_rds_auto_start_stop = true")}
        ]
        result = _process_namespace(ns, mock_github_service)
        assert result == {'db_waste': None, 'pod_waste': None}

    def test_detect_cp_resource_wastage_scheduled(self, mocker):

        mock_get_environment_variables = mocker.patch(
            "bin.detect_cp_resource_wastage._get_environment_variables")
        mock_get_environment_variables.return_value = ("mock_moj_token", "mock_ap_token")
        mock_github_service = mocker.patch("bin.detect_cp_resource_wastage.GithubService")
        mock_github_service_instance = mock_github_service.return_value
        mock_github_service_instance.get_all_namespaces.return_value = [
            "test-ns-04-dev", "test-ns-05-staging",
            "test-ns-06-preprod"]
        mock_process_namespace = mocker.patch("bin.detect_cp_resource_wastage._process_namespace")
        mock_process_namespace.side_effect = [
            {"db_waste": "test_ns_04_dev", "pod_waste": None},
            {"db_waste": None, "pod_waste": "test_pod_05_staging"},
            {"db_waste": None, "pod_waste": None}
        ]
        mock_s3 = mocker.patch("bin.detect_cp_resource_wastage.boto3.resource")
        mock_bucket = mock_s3.return_value.Bucket.return_value
        mock_bucket.upload_file.return_value = None

        detect_cp_resource_wastage(run_manually=False)

        assert mock_get_environment_variables.call_count == 1
        assert mock_github_service_instance.get_all_namespaces.call_count == 1
        assert mock_process_namespace.call_count == 3
        assert mock_s3.call_count == 1
        assert mock_bucket.upload_file.call_count == 2

    def test_detect_cp_resource_wastage_manual(self, mocker):

        mock_get_environment_variables = mocker.patch(
            "bin.detect_cp_resource_wastage._get_environment_variables")
        mock_get_environment_variables.return_value = ("mock_moj_token", "mock_ap_token")
        mock_github_service = mocker.patch("bin.detect_cp_resource_wastage.GithubService")
        mock_github_service_instance = mock_github_service.return_value
        mock_github_service_instance.get_all_namespaces.return_value = [
            "test-ns-04-dev", "test-ns-05-staging",
            "test-ns-06-preprod"]
        mock_process_namespace = mocker.patch("bin.detect_cp_resource_wastage._process_namespace")
        mock_process_namespace.side_effect = [
            {"db_waste": "test_ns_04_dev", "pod_waste": None},
            {"db_waste": None, "pod_waste": "test_pod_05_staging"},
            {"db_waste": None, "pod_waste": None}]

        mock_slack_cls = mocker.patch("bin.detect_cp_resource_wastage.SlackService")
        mock_slack = mock_slack_cls.return_value

        detect_cp_resource_wastage(run_manually=True)

        assert mock_get_environment_variables.call_count == 1
        assert mock_github_service_instance.get_all_namespaces.call_count == 1
        assert mock_process_namespace.call_count == 3
        mock_slack.send_nonprod_resource_wastage_alerts.assert_called_once_with(
            db_wastage_ns=["test_ns_04_dev"], pod_wastage_ns=["test_pod_05_staging"]
        )
