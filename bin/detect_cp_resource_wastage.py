import base64
import re
import os
import boto3
from datetime import datetime, timedelta, timezone
import time
import logging
import csv
from typing import Dict, Optional, List, Union
from services.github_service import GithubService
from services.slack_service import SlackService
from config.constants import ENTERPRISE, MINISTRY_OF_JUSTICE
import concurrent.futures


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _get_environment_variables() -> str:

    github_token = os.getenv("GH_TOKEN")
    if not github_token:
        raise ValueError(
            "The env variable GH_TOKEN is empty or missing")

    return github_token

def _write_csv(file_name: str, headers: list, data: List[Union[list, str, dict]]) -> str:
    
    with open(file_name, mode="w", newline="") as csvfile:
        if all(isinstance(row, dict) for row in data):
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for row in data:
                if isinstance(row, list):
                    writer.writerow(row)
                elif isinstance(row, str):
                    writer.writerow([row])
                else:
                    writer.writerow([str(row)])

    return file_name


def _process_namespace(ns: str, github_service: GithubService) -> Dict[str, Optional[str]]:
    logger.info("Processing ns: %s", ns)

    result = {'db_waste': None, 'pod_waste': None}

    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        resources_repo = github_service.get_cloud_platform_environments_content(
            f"namespaces/live.cloud-platform.service.justice.gov.uk/{ns}/resources"
        )

        if resources_repo is not None:
            break  # success
        else:
            logger.warning("Attempt %d: No resources found for namespace '%s'. Retrying in %d seconds...", 
                           attempt + 1, ns, retry_delay)
            time.sleep(retry_delay)
    else:
        # All attempts failed
        logger.error("Failed to fetch resources for namespace '%s' after %d attempts", ns, max_retries)
        return result

    resources = [
        resource["name"]
        for resource in resources_repo]

    if "rds.tf" in resources:
        rds_file = github_service.get_cloud_platform_environments_content(
            f"namespaces/live.cloud-platform.service.justice.gov.uk/{ns}/resources/rds.tf")
        rds_decod_content = base64.b64decode(rds_file["content"]).decode("utf-8")
        if not re.search(r'enable_rds_auto_start_stop\s*=\s*true', rds_decod_content):
            result['db_waste'] = ns
        if re.search(r'enable_rds_auto_start_stop\s*=\s*true', rds_decod_content) and "scheduled-downtime.tf" not in resources:
            result['pod_waste'] = ns

    return result


def detect_cp_resource_wastage(run_manually: bool = False) -> None:

    github_token = _get_environment_variables()
    github_service = GithubService(github_token, MINISTRY_OF_JUSTICE, ENTERPRISE)

    logger.info("Fetching all namespaces...")
    namespaces = github_service.get_all_namespaces()
    nonprod_namespaces = [ns for ns in namespaces if re.search(r'dev|staging|preprod', ns)]
    resource_wastage = {"db_waste": [],
                        "pod_waste": []}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        logger.info("Processing namespaces in parallel...")
        futures = [executor.submit(_process_namespace, ns, github_service) for ns in nonprod_namespaces]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result['db_waste']:
                resource_wastage['db_waste'].append(result['db_waste'])
                logger.info("Database wastage detected: %s", result['db_waste'])
            if result['pod_waste']:
                resource_wastage['pod_waste'].append(result['pod_waste'])
                logger.info("Pod wastage detected: %s", result['pod_waste'])

    if run_manually:
        logger.info("Manual run detected – sending Slack alert.")
        SlackService(os.getenv("ADMIN_SLACK_TOKEN")).send_nonprod_resource_wastage_alerts(
            db_wastage_ns=resource_wastage['db_waste'],
            pod_wastage_ns=resource_wastage['pod_waste']
        )
    else:
        report_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        report_date_str = report_date.isoformat()

        pod_csv = _write_csv(
            file_name=report_date_str,
            headers=["Namespace"],
            data=resource_wastage['pod_waste']
            )

        db_csv = _write_csv(
            file_name=report_date_str,
            headers=["Namespace"],
            data=resource_wastage['db_waste']
            )
        bucket_name = os.environ['S3_BUCKET_NAME']
        s3 = boto3.resource('s3')
        s3.Bucket(bucket_name).upload_file(db_csv, f'rds_waste_reports/{db_csv}')
        s3.Bucket(bucket_name).upload_file(db_csv, f'pod_waste_reports/{pod_csv}')


if __name__ == "__main__":
    run_manually_flag = os.getenv("RUN_MANUALLY", "false").lower() == "true"
    detect_cp_resource_wastage(run_manually=run_manually_flag)
