import boto3
import logging
import os
import time
import pandas as pd
from typing import Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.slack_service import SlackService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def athena_execute_query(
    query: str,
    database: str = "cur_v2_database",
    s3_output: str = "s3://coat-production-cur-v2-hourly/athena-results/",
) -> str:

    """
    Executes an Athena query and returns the results.
    :param query: The SQL query to execute.
    :param database: The Athena database to use.
    :param s3_output: The S3 bucket where query results will be stored.
    :return: Query execution ID.
    """
    athena_client = boto3.client("athena", region_name="eu-west-2")

    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": s3_output},
        WorkGroup="coat_cur_report"
    )
    query_execution_id = response["QueryExecutionId"]
    logger.info("Started Athena query with execution ID: %s", query_execution_id)
    while True:
        result = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = result["QueryExecution"]["Status"]["State"]
        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        time.sleep(2)

    if state != "SUCCEEDED":
        raise RuntimeError(f"Query failed or was cancelled: {state}")

    return query_execution_id


def generate_query_total_tagging_coverage_for_tag(
  billing_period: str,
  business_unit: str,
  tag_key: str
  ) -> str:
    """    Generates a SQL query to calculate the total tagging coverage percentage.
    :param billing_period: The billing period for which to calculate coverage.
    :param business_unit: The business unit for which to calculate coverage.
    :return: SQL query string."""

    query_total_tagging_coverage = f"""
    SELECT
      100.0 *
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
            AND line_item_unblended_cost > 0
            AND resource_tags['{tag_key}'] IS NOT NULL
            AND resource_tags['{tag_key}'] <> ''

        )
      /
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
            AND line_item_unblended_cost > 0
        )
      AS tagging_coverage_pct
      """
    return query_total_tagging_coverage


def generate_query_list_of_aws_accounts(billing_period: str,
                                        business_unit: str) -> str:
    """Generates a SQL query to list all AWS accounts for a given billing
    period and business unit.
    :param billing_period: The billing period for which to list accounts.
    :param business_unit: The business unit for which to list accounts.
    :return: SQL query string."""

    query_list_of_aws_accounts = f"""
    SELECT DISTINCT line_item_usage_account_id, line_item_usage_account_name
    FROM data
    WHERE billing_period = '{billing_period}'
    AND cost_category['business_unit'] = '{business_unit}'
    """
    return query_list_of_aws_accounts


def generate_query_tagging_per_aws_account_for_tag(
    aws_account_name: str,
    billing_period: str,
    business_unit: str,
    tag_key: str
  ) -> str:
    """Generates a SQL query to calculate tagging coverage for a specific AWS account.
    :param aws_account_name: The name of the AWS account.
    :param billing_period: The billing period for which to calculate coverage.
    :param business_unit: The business unit for which to calculate coverage.
    :return: SQL query string."""

    query_tagging_per_aws_account = f"""
    SELECT
      100.0 *
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
            AND line_item_usage_account_name = '{aws_account_name}'
            AND line_item_unblended_cost > 0
            AND resource_tags['{tag_key}'] IS NOT NULL
            AND resource_tags['{tag_key}'] <> ''
        )
      /
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
            AND line_item_usage_account_name = '{aws_account_name}'
            AND line_item_unblended_cost > 0
        )
      AS account_tagging_coverage_pct
      """

    return query_tagging_per_aws_account


def fetch_account_coverage(index, aws_account_name,
                           tag_key, billing_period,
                           business_unit):
    logger.info("Processing AWS account coverage %s for tag %s",
                aws_account_name, tag_key)
    query_aws_account_per_tag = generate_query_tagging_per_aws_account_for_tag(
        aws_account_name, billing_period, business_unit, tag_key
    )
    athena_aws_account_per_tag_ex_id = athena_execute_query(query_aws_account_per_tag)
    results_aws_account_per_tag = boto3.client("athena").get_query_results(
        QueryExecutionId=athena_aws_account_per_tag_ex_id
    )
    aws_account_cov_prc_per_tag = (
        round(float(results_aws_account_per_tag[
          "ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"]), 2)
        if "VarCharValue" in results_aws_account_per_tag[
          "ResultSet"]["Rows"][1]["Data"][0]
        else 0
    )
    return index, tag_key, aws_account_cov_prc_per_tag


def fetch_total_tag_coverage(tag_key, billing_period, business_unit):
    logger.info("Processing total coverage for tag key: %s", tag_key)
    query_total_coverage = generate_query_total_tagging_coverage_for_tag(
        billing_period, business_unit, tag_key
    )
    athena_total_coverage_ex_id = athena_execute_query(query_total_coverage)
    results_total_coverage = boto3.client("athena").get_query_results(
        QueryExecutionId=athena_total_coverage_ex_id
    )
    total_tagging_cov_prc = (
        round(float(results_total_coverage[
          "ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"]), 2)
        if "VarCharValue" in results_total_coverage[
          "ResultSet"]["Rows"][1]["Data"][0]
        else 0
    )
    logger.info("Total tagging coverage for %s: %.2f%%", tag_key, total_tagging_cov_prc)
    return tag_key, total_tagging_cov_prc


# pylint: disable=W0102,R0914
def generate_tagging_coverage_metrics(
    business_unit: str,
    billing_period: str,
    tag_keys: list[str] = ["user_business_unit", "user_application",
                           "user_service_area", "user_owner", "user_is_production"]
) -> Tuple[int, pd.DataFrame]:
    """
    Generates tagging coverage metrics for a specific business unit and billing period.
    :param business_unit: The business unit for which to generate metrics.
    :param billing_period: The billing period for which to generate metrics.
    :param tag_keys: List of tag keys to consider for coverage.
    :return: df of total coverage per tag,
    and a df with coverage per-account & per-tag.
    """

    logger.info("Fetching AWS accounts for business unit %s", business_unit)
    query_list_of_aws_accounts = generate_query_list_of_aws_accounts(
      billing_period, business_unit)
    athena_bu_aws_account_ex_id = athena_execute_query(query_list_of_aws_accounts)
    results_bu_aws_accounts = boto3.client("athena").get_query_results(
      QueryExecutionId=athena_bu_aws_account_ex_id)
    rows = results_bu_aws_accounts["ResultSet"]["Rows"]
    cleaned_data = [
      [col["VarCharValue"] for col in row["Data"]]
      for row in rows
      if len(row["Data"]) == 2
      ]
    headers = cleaned_data[0]
    df_aws_accounts = pd.DataFrame(cleaned_data[1:], columns=headers)

    total_tag_coverage = {}
    df_tagging_coverage_aws_accounts = df_aws_accounts.rename(columns={
        "line_item_usage_account_id": "AWS_account_id",
        "line_item_usage_account_name": "AWS_account_name"
    })

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_total_tag_coverage, tag_key,
                            billing_period, business_unit)
            for tag_key in tag_keys
        ]
        for future in as_completed(futures):
            tag_key, coverage = future.result()
            total_tag_coverage[tag_key] = coverage

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for tag_key, coverage in total_tag_coverage.items():
            if coverage > 0:
                for index, row in df_tagging_coverage_aws_accounts.iterrows():
                    futures.append(
                        executor.submit(
                            fetch_account_coverage,
                            index,
                            row["AWS_account_name"],
                            tag_key,
                            billing_period,
                            business_unit
                        )
                    )
                logger.info(
                  "Completed per-account tagging coverage for tag %s", tag_key)

        for future in as_completed(futures):
            index, tag_key, account_cov = future.result()
            df_tagging_coverage_aws_accounts.at[index, tag_key] = account_cov

    df_total_tagging_coverage = pd.DataFrame(
      total_tag_coverage.items(), columns=["Tag", "Coverage (%)"])
    df_tagging_coverage_aws_accounts = df_tagging_coverage_aws_accounts.sort_values(
      by="AWS_account_name").reset_index(drop=True)

    return df_total_tagging_coverage, df_tagging_coverage_aws_accounts


def generate_excel_report(
    df_total_tagging_coverage: pd.DataFrame,
    df_tagging_coverage_aws_accounts: pd.DataFrame,
    business_unit: str
  ) -> None:
    """
    Generates an Excel report with overall tagging coverage and per-account coverage.
    :param total_tagging_cov_percentage: Overall tagging coverage percentage.
    :param df_tagging_coverage_aws_accounts: DataFrame with per-account coverage.
    :param output_path: Path to save the Excel file.
    """
    df_total_tagging_coverage['Tag'] = df_total_tagging_coverage['Tag'].str.replace(
      r'^user_', '', regex=True)
    df_tagging_coverage_aws_accounts = df_tagging_coverage_aws_accounts.rename(
      columns=lambda x: x[len("user_"):] if x.startswith("user_") else x)

    output_path = f"tagging_coverage_report_{business_unit}.xlsx"
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_total_tagging_coverage.to_excel(
          writer, sheet_name="Total Coverage per Tag", index=False)

        df_tagging_coverage_aws_accounts.to_excel(
          writer, sheet_name="Account Coverage per Tag", index=False
        )
        workbook = writer.book
        summary_ws = writer.sheets["Total Coverage per Tag"]

        colors = ['#5DADE2', '#58D68D', '#EB984E', '#878f99', '#AF7AC5']

        chart = workbook.add_chart({'type': 'column'})
        chart.set_title({'name': 'Total Tagging Coverage'})
        chart.set_y_axis({'name': 'Coverage (%)'})
        chart.set_x_axis({'name': 'Tag'})
        chart.set_legend({'position': 'none'})

        chart.add_series({
            'name': 'Coverage (%)',
            'categories': ['Total Coverage per Tag', 1, 0,
                           len(df_total_tagging_coverage), 0],
            'values': ['Total Coverage per Tag', 1, 1,
                       len(df_total_tagging_coverage), 1],
            'data_labels': {'value': True},
            'points': [{'fill': {'color': colors[i % len(colors)]}}
                       for i in range(len(df_total_tagging_coverage))]
        })

        summary_ws.insert_chart('D2', chart, {'x_scale': 1.5, 'y_scale': 1.5})

    logger.info("Excel report generated at: %s", output_path)

    return output_path


def generate_tagging_coverage_report(business_unit: str,
                                     billing_period: str,
                                     tag_keys: list[str] = [
                                       "user_business_unit", "user_application",
                                       "user_service_area", "user_owner",
                                       "user_is_production"]) -> None:

    df_total_tagging_coverage, df_tagging_coverage_aws_accounts = (
      generate_tagging_coverage_metrics(
        business_unit, billing_period, tag_keys)
    )
    output_report_path = generate_excel_report(
      df_total_tagging_coverage,
      df_tagging_coverage_aws_accounts,
      business_unit)
    logger.info(
      "Tagging coverage report generated for business unit: %s", business_unit)

    SlackService(os.getenv("ADMIN_SLACK_TOKEN")).send_report_with_message(
      file_path=output_report_path,
      message=f"Tagging coverage report for {business_unit}\n"
      f"for billing period {billing_period} has been generated.\n",
      filename=f"tagging_coverage_report_{business_unit}.xlsx"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate tagging coverage report.")
    parser.add_argument(
        "--business_unit", required=True, help="Business unit for the report."
    )
    parser.add_argument(
        "--billing_period", required=True, help="Billing period for the report."
    )
    args = parser.parse_args()
    generate_tagging_coverage_report(args.business_unit, args.billing_period)
