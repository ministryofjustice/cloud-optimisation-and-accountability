import base64
import re
import os
import logging
from typing import Dict, Optional
from services.github_service import GithubService
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


def _process_namespace(ns: str, github_service: GithubService) -> Dict[str, Optional[str]] :

    result = {'db_waste': None, 'pod_waste': None}

    resources = [
        resource["name"]
        for resource in github_service.get_cloud_platform_environments_content(
            f"namespaces/live.cloud-platform.service.justice.gov.uk/{ns}/resources"
            )]
    if "rds.tf" in resources:
        rds_file = github_service.get_cloud_platform_environments_content(
            f"namespaces/live.cloud-platform.service.justice.gov.uk/{ns}/resources/rds.tf")
        rds_decod_content = base64.b64decode(rds_file["content"]).decode("utf-8")
        if not re.search(r'enable_rds_auto_start_stop\s*=\s*true', rds_decod_content):
            print("db_wastage")
            result['db_waste'] = ns
        if re.search(r'enable_rds_auto_start_stop\s*=\s*true', rds_decod_content) and "scheduled-downtime.tf" not in resources:
            print("pod wastage")
            result['pod_waste'] = ns

    return result


def detect_cp_resource_wastage():

    github_token = _get_environment_variables()
    github_service = GithubService(github_token, MINISTRY_OF_JUSTICE, ENTERPRISE)

    logger.info("Fetching all namespaces...")
    namespaces = [item["name"] for item in github_service.get_cloud_platform_environments_content("namespaces/live.cloud-platform.service.justice.gov.uk")]
    nonprod_namespaces = [ns for ns in namespaces if re.search(r'dev|staging|preprod', ns)]
    resource_wastage = {"db_waste": [],
                        "pod_waste": []}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(_process_namespace, ns, github_service) for ns in nonprod_namespaces]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result['db_waste']:
                resource_wastage['db_waste'].append(result['db_waste'])
                logger.info("Database wastage detected: %s", result['db_waste'])
            if result['pod_waste']:
                resource_wastage['pod_waste'].append(result['pod_waste'])
                logger.info("Pod wastage detected: %s", result['pod_waste'])

    #Code to sent results to Slack channel"

    if __name__ == "__main__":
        detect_cp_resource_wastage()

