import boto3
import logging
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from services.slack_service import SlackService


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _extract_tag_value(tags_list, key):
    for tag in tags_list:
        if tag.get("key") == key:
            return tag.get("value")
    return None


def _get_account_ou(account_id):
    client_orgs = boto3.client("organizations", region_name="eu-west-2")
    response = client_orgs.list_parents(
            ChildId=account_id)
    parent_id = response['Parents'][0]['Id']
    parent_type = response['Parents'][0]['Type']

    if parent_type == 'ORGANIZATIONAL_UNIT':
        ou_info = client_orgs.describe_organizational_unit(
            OrganizationalUnitId=parent_id
            )
        return ou_info['OrganizationalUnit']['Name']
    else:
        return "Root"


def find_ebs_volumes_owners(run_manually: bool = False, monthly_savings_threshold: float=10.0):
    client_cost_opt = boto3.client("cost-optimization-hub", region_name="us-east-1")
    paginator = client_cost_opt.get_paginator("list_recommendations")

    page_iterator = paginator.paginate(
    filter={"resourceTypes": [
        "EbsVolume",
        ]},
    includeAllRecommendations=True,
    PaginationConfig={
        "PageSize": 1000
        }
    )
    all_recommendations = []
    for page in page_iterator:
        items = page.get("items", [])
        all_recommendations.extend(items)


    ebs_recommendation_df = pd.DataFrame(all_recommendations)

    if ebs_recommendation_df.empty:
        logger.info("No recommendations found.")
    else:
        logger.info("Recommendations found: %s", len(ebs_recommendation_df))
        ebs_recommendation_df["owner"] = ebs_recommendation_df["tags"].apply(lambda tags: _extract_tag_value(tags, "owner"))
        ebs_recommendation_df["business_unit"] = ebs_recommendation_df["tags"].apply(lambda tags: _extract_tag_value(tags, "business-unit"))
        ebs_recommendation_df = ebs_recommendation_df[["recommendationId", "resourceId", "currentResourceType",
                                                       "estimatedMonthlySavings", "estimatedSavingsPercentage",
                                                       "estimatedMonthlyCost", "currentResourceSummary",
                                                       "recommendedResourceSummary", "recommendationLookbackPeriodInDays",
                                                       "accountId", "owner", "business_unit"]]
    client_orgs = boto3.client("organizations", region_name="eu-west-2")

    paginator = client_orgs.get_paginator("list_accounts")
    page_iterator = paginator.paginate()

    all_moj_accounts = []
    for page in page_iterator:
        items = page.get("Accounts")
        all_moj_accounts.extend(items)

    moj_accounts_df = pd.DataFrame(all_moj_accounts)
    if moj_accounts_df.empty:
        logger.info("No accounts found.")
    else:
        logger.info("Accounts found: %s", len(moj_accounts_df))
        moj_accounts_df = moj_accounts_df[["Id", "Name"]]
        account_ids = moj_accounts_df["Id"].tolist()

        ous = []
        for account_id in account_ids:
            ou_name = _get_account_ou(account_id)
            logger.info("Parrent aws account found for: %s", account_id)
            ous.append(ou_name)

        moj_accounts_df["aws_OU"] = ous
        moj_accounts_df = moj_accounts_df.rename(columns={"Id": "accountId", "Name": "accountName"})

    ebs_recommendation_df = ebs_recommendation_df.merge(moj_accounts_df[["accountId","accountName", "aws_OU"]], on="accountId", how="left")
    ebs_recommendation_df = ebs_recommendation_df.rename(columns={"accountName": "aws_accountName", "accountId": "aws_accountId" })
    ebs_recommendation_df = ebs_recommendation_df.loc[ebs_recommendation_df["estimatedMonthlySavings"] >= monthly_savings_threshold]
    ebs_recommendation_df = ebs_recommendation_df.sort_values(by="estimatedMonthlySavings", ascending=False).reset_index(drop=True)
    report_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    filename = f"{report_date}.csv"
    ebs_recommendation_df.to_csv(filename, index=False)
    logger.info("DataFrame dumped to %s", filename)

    if run_manually:
        logger.info("Manual run detected sending Slack alert.")
        SlackService(os.getenv("ADMIN_SLACK_TOKEN")).send_report_with_message(
            file_path=filename,
            message="EBS volume recommendations",
            filename=filename
        )


if __name__ == "__main__":
    run_manually_flag = os.getenv("RUN_MANUALLY", "false").lower() == "true"
    find_ebs_volumes_owners(run_manually=run_manually_flag)
