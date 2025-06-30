import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from bin.find_ebs_volume_owners import _extract_tag_value, _get_account_organisational_unit, find_ebs_volumes_owners
from unittest.mock import call

class TestFindEbsVolumeOwners:

    def test_extract_tag_value(self):

        tags = [{"key": "owner", "value": "test_owner"}, {"key": "business-unit", "value": "test_unit"}]
        assert _extract_tag_value(tags, "owner") == "test_owner"
        assert _extract_tag_value(tags, "business-unit") == "test_unit"
        assert _extract_tag_value(tags, "non-existent") is None

    def test_get_account_get_organisational_unit(self, mocker):
        mock_client = mocker.patch("boto3.client")
        mock_orgs = mock_client.return_value
        mock_orgs.list_parents.return_value = {
            'Parents': [{'Id': 'ou-12345678', 'Type': 'ORGANIZATIONAL_UNIT'}]
        }
        mock_orgs.describe_organizational_unit.return_value = {
            'OrganizationalUnit': {'Name': 'TestOU'}
        }
        ou_name = _get_account_organisational_unit("123456789012")
        assert ou_name == "TestOU"

    def test_get_account_get_organisational_unit_root(self, mocker):
        mock_client = mocker.patch("boto3.client")
        mock_orgs = mock_client.return_value
        mock_orgs.list_parents.return_value = {
            'Parents': [{'Id': 'r-12345678', 'Type': 'ROOT'}]
        }
        ou_name = _get_account_organisational_unit("123456789012")
        assert ou_name == "Root"

    def test_find_ebs_volumes_owners_no_recommendations(self, mocker):
        mock_client = mocker.patch("boto3.client")
        mock_cost_opt = mock_client.return_value
        mock_cost_opt.get_paginator.return_value.paginate.return_value = []
        mock_logger = mocker.patch("bin.find_ebs_volume_owners.logger")

        find_ebs_volumes_owners(run_manually=True)

        mock_cost_opt.get_paginator.assert_called_once_with("list_recommendations")
        mock_cost_opt.get_paginator.return_value.paginate.assert_called_once_with(
            filter={"resourceTypes": ["EbsVolume"]},
            includeAllRecommendations=True,
            PaginationConfig={"PageSize": 1000}
        )
        mock_logger.info.assert_any_call("No recommendations found.")
    
    def test_find_ebs_volumes_owners_no_org_accounts(self, mocker):
        mock_boto3_client = mocker.patch("boto3.client")
        mock_cost_opt = mocker.Mock()
        mock_orgs = mocker.Mock()
        mock_boto3_client.side_effect = lambda service_name, region_name=None, **kwargs: (
            mock_cost_opt if service_name == "cost-optimization-hub"
            else mock_orgs if service_name == "organizations"
            else mocker.Mock()
        )
        mock_cost_opt.get_paginator.return_value.paginate.return_value = [{
                "items": [
                    {
                        "recommendationId": "rec-123",
                        "resourceId": "vol-123",
                        "currentResourceType": "EbsVolume",
                        "estimatedMonthlySavings": 15.0,
                        "estimatedSavingsPercentage": 20.0,
                        "estimatedMonthlyCost": 75.0,
                        "currentResourceSummary": {"size": "100GB"},
                        "recommendedResourceSummary": {"size": "50GB"},
                        "recommendationLookbackPeriodInDays": 30,
                        "accountId": "123456789012",
                        "tags": [{"key": "owner", "value": "test_owner"}, {"key": "business-unit", "value": "test_unit"}]
                    }
                ]
            }]
        mock_orgs.get_paginator.return_value.paginate.return_value = []
        mock_logger = mocker.patch("bin.find_ebs_volume_owners.logger")

        find_ebs_volumes_owners()

        mock_cost_opt.get_paginator.assert_called_once_with("list_recommendations")
        mock_cost_opt.get_paginator.return_value.paginate.assert_called_once_with(
            filter={"resourceTypes": ["EbsVolume"]},
            includeAllRecommendations=True,
            PaginationConfig={"PageSize": 1000}
        )
        mock_logger.info.assert_any_call("Recommendations found: %s", 1)
        mock_orgs.get_paginator.assert_called_once_with("list_accounts")
        mock_logger.info.assert_any_call("No accounts found in the organization.")

    def test_find_ebs_volumes_owners_recommendations_manual_run(self, mocker):
        mock_boto3_client = mocker.patch("boto3.client")
        mock_cost_opt = mocker.Mock()
        mock_orgs = mocker.Mock()
        mock_boto3_client.side_effect = lambda service_name, region_name=None, **kwargs: (
            mock_cost_opt if service_name == "cost-optimization-hub"
            else mock_orgs if service_name == "organizations"
            else mocker.Mock()
        )
        mock_cost_opt.get_paginator.return_value.paginate.return_value = [{
                "items": [
                    {
                        "recommendationId": "rec-123",
                        "resourceId": "vol-123",
                        "currentResourceType": "EbsVolume",
                        "estimatedMonthlySavings": 15.0,
                        "estimatedSavingsPercentage": 20.0,
                        "estimatedMonthlyCost": 75.0,
                        "currentResourceSummary": {"size": "100GB"},
                        "recommendedResourceSummary": {"size": "50GB"},
                        "recommendationLookbackPeriodInDays": 30,
                        "accountId": "123456789012",
                        "tags": [{"key": "owner", "value": "test_owner"}, {"key": "business-unit", "value": "test_unit"}]
                    }
                ]
            }]
        mock_orgs.get_paginator.return_value.paginate.return_value = [{
            'Accounts': [{'Id': '123456789101', 'Name': 'test_account'}]
        }]
        mock_get_account_ou = mocker.patch(
            "bin.find_ebs_volume_owners._get_account_organisational_unit")
        mock_get_account_ou.return_value = "TestOU"

        mock_logger = mocker.patch("bin.find_ebs_volume_owners.logger")

        mock_slack_cls = mocker.patch("bin.find_ebs_volume_owners.SlackService")
        mock_slack = mock_slack_cls.return_value
        mock_datetime = mocker.patch("bin.find_ebs_volume_owners.datetime")
        mock_datetime.now.return_value = datetime(2025, 6, 1, tzinfo=timezone.utc)

        find_ebs_volumes_owners(run_manually=True)

        mock_cost_opt.get_paginator.assert_called_once_with("list_recommendations")
        mock_cost_opt.get_paginator.return_value.paginate.assert_called_once_with(
            filter={"resourceTypes": ["EbsVolume"]},
            includeAllRecommendations=True,
            PaginationConfig={"PageSize": 1000}
        )
        mock_logger.info.assert_any_call("Recommendations found: %s", 1)
        mock_orgs.get_paginator.assert_called_once_with("list_accounts")
        mock_logger.info.assert_any_call("Accounts found: %s", 1)
        mock_get_account_ou.assert_called_once_with("123456789101")
        mock_logger.info.assert_any_call("Manual run detected sending Slack alert.")
        mock_slack.send_report_with_message.assert_has_calls([
            call(
                file_path='2025-05-31.csv',
                message="EBS volume recommendations",
                filename='2025-05-31.csv'
            ),
            call(
                file_path='aggregated_2025-05-31.csv',
                message="Aggregated EBS volume recommendations",
                filename='aggregated_2025-05-31.csv'
            )
        ])

    def test_find_ebs_volumes_owners_recommendations_scheduled_run(self, mocker):
        mock_boto3_client = mocker.patch("boto3.client")
        mock_cost_opt = mocker.Mock()
        mock_orgs = mocker.Mock()
        mock_boto3_client.side_effect = lambda service_name, region_name=None, **kwargs: (
            mock_cost_opt if service_name == "cost-optimization-hub"
            else mock_orgs if service_name == "organizations"
            else mocker.Mock()
        )
        mock_cost_opt.get_paginator.return_value.paginate.return_value = [{
                "items": [
                    {
                        "recommendationId": "rec-123",
                        "resourceId": "vol-123",
                        "currentResourceType": "EbsVolume",
                        "estimatedMonthlySavings": 15.0,
                        "estimatedSavingsPercentage": 20.0,
                        "estimatedMonthlyCost": 75.0,
                        "currentResourceSummary": {"size": "100GB"},
                        "recommendedResourceSummary": {"size": "50GB"},
                        "recommendationLookbackPeriodInDays": 30,
                        "accountId": "123456789012",
                        "tags": [{"key": "owner", "value": "test_owner"}, {"key": "business-unit", "value": "test_unit"}]
                    }
                ]
            }]
        mock_orgs.get_paginator.return_value.paginate.return_value = [{
            'Accounts': [{'Id': '123456789101', 'Name': 'test_account'}]
        }]
        mock_get_account_ou = mocker.patch(
            "bin.find_ebs_volume_owners._get_account_organisational_unit")
        mock_get_account_ou.return_value = "TestOU"
        mock_logger = mocker.patch("bin.find_ebs_volume_owners.logger")
        mock_slack_cls = mocker.patch("bin.find_ebs_volume_owners.SlackService")
        mock_slack = mock_slack_cls.return_value
        mock_datetime = mocker.patch("bin.find_ebs_volume_owners.datetime")
        mock_datetime.now.return_value = datetime(2025, 6, 1, tzinfo=timezone.utc)

        find_ebs_volumes_owners(run_manually=False)

        mock_cost_opt.get_paginator.assert_called_once_with("list_recommendations")
        mock_cost_opt.get_paginator.return_value.paginate.assert_called_once_with(
            filter={"resourceTypes": ["EbsVolume"]},
            includeAllRecommendations=True,
            PaginationConfig={"PageSize": 1000}
        )
        mock_logger.info.assert_any_call("Recommendations found: %s", 1)
        mock_orgs.get_paginator.assert_called_once_with("list_accounts")
        mock_logger.info.assert_any_call("Accounts found: %s", 1)
        mock_get_account_ou.assert_called_once_with("123456789101")
        mock_logger.info.assert_any_call("Aggregated DataFrame dumped to %s", "aggregated_2025-05-31.csv")
        mock_logger.info.assert_any_call("DataFrame dumped to %s", "2025-05-31.csv")
        mock_slack.send_report_with_message.assert_not_called()
