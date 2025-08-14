import boto3
import logging
import time
import pandas as pd
from typing import Tuple

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
    :return: Dict of total coverage per tag, and a DataFrame with per-account & per-tag coverage.
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

    for tag_key in tag_keys:
        logger.info("Processing tag key: %s", tag_key)

        query_total_coverage = generate_query_total_tagging_coverage_for_tag(
          billing_period, business_unit, tag_key)
        logger.info("Executing query for total tagging coverage for tag %s", tag_key)
        athena_total_coverage_ex_id = athena_execute_query(
          query_total_coverage)
        results_total_coverage = boto3.client("athena").get_query_results(
          QueryExecutionId=athena_total_coverage_ex_id)
        total_tagging_cov_prc = (
          round(float(results_total_coverage["ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"]), 2)
          if "VarCharValue" in results_total_coverage["ResultSet"]["Rows"][1]["Data"][0]
          else 0
        )
        logger.info(
          "Total tagging coverage percentage for %s: %.2f%%",
          tag_key, total_tagging_cov_prc)
        total_tag_coverage[tag_key] = total_tagging_cov_prc

        if total_tagging_cov_prc > 0:
            logger.info("Calculating tagging coverage for each AWS account for %s.", tag_key)
            for index, row in df_tagging_coverage_aws_accounts.iterrows():
                aws_account_name = row["AWS_account_name"]
                logger.info("Processing AWS account %s for tag %s", aws_account_name, tag_key)
                query_aws_account_per_tag = generate_query_tagging_per_aws_account_for_tag(
                  aws_account_name, billing_period, business_unit, tag_key)
                athena_aws_account_per_tag_ex_id = athena_execute_query(
                  query_aws_account_per_tag)
                results_aws_account_per_tag = boto3.client("athena").get_query_results(
                  QueryExecutionId=athena_aws_account_per_tag_ex_id)
                aws_account_cov_prc_per_tag = (
                  round(float(results_aws_account_per_tag["ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"]), 2)
                  if "VarCharValue" in results_aws_account_per_tag["ResultSet"]["Rows"][1]["Data"][0]
                  else 0
                )
                df_tagging_coverage_aws_accounts.at[
                  index, tag_key] = aws_account_cov_prc_per_tag

            logger.info("Tagging coverage for AWS accounts for tag %s completed.", tag_key)

    df_tagging_coverage_aws_accounts = df_tagging_coverage_aws_accounts.sort_values(
      by="AWS_account_name",  
      ascending=False).reset_index(drop=True)
    return total_tag_coverage, df_tagging_coverage_aws_accounts


def generate_excel_report(
    total_tagging_cov_percentage: float,
    df_tagging_coverage_aws_accounts: pd.DataFrame,
    business_unit: str
  ) -> None:
    """
    Generates an Excel report with overall tagging coverage and per-account coverage.
    :param total_tagging_cov_percentage: Overall tagging coverage percentage.
    :param df_tagging_coverage_aws_accounts: DataFrame with per-account coverage.
    :param output_path: Path to save the Excel file.
    """
    output_path = f"tagging_coverage_report_{business_unit}.xlsx"
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        summary_df = pd.DataFrame({
            "Status": ["Tagged", "Untagged"],
            "Coverage (%)": [
                total_tagging_cov_percentage,
                100 - total_tagging_cov_percentage
            ]
        })
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        df_tagging_coverage_aws_accounts.to_excel(
          writer, sheet_name="Account Coverage", index=False
        )
        workbook = writer.book
        summary_ws = writer.sheets["Summary"]
        account_ws = writer.sheets["Account Coverage"]

        doughnut_chart = workbook.add_chart({"type": "doughnut"})
        doughnut_chart.add_series({
            "name": "Total Tagging Coverage [%]",
            "categories": ["Summary", 1, 0, 2, 0],
            "values": ["Summary", 1, 1, 2, 1],
            "points": [
                {"fill": {"color": '#4CAF50'}},
                {"fill": {"color": '#D3D3D3'}},
            ],
            "data_labels": {"value": True, "num_format": '0.00"%"'},
        })
        doughnut_chart.set_legend({"position": "left"})
        summary_ws.insert_chart("E2", doughnut_chart, {"x_scale": 1.5, "y_scale": 1.5})

        df_cols = df_tagging_coverage_aws_accounts.columns.tolist()
        account_col = (
          df_cols.index("AWS_account_name")
          if "AWS_account_name" in df_cols
          else 0
        )
        coverage_col = (
          df_cols.index("account_tagging_coverage_pct")
          if "account_tagging_coverage_pct" in df_cols
          else 1
        )

        n_accounts = len(df_tagging_coverage_aws_accounts)
        bar_chart = workbook.add_chart({"type": "column"})
        bar_chart.add_series({
          "name": "Tagging Coverage by Account [%]",
          "categories": ["Account Coverage", 1, account_col, n_accounts, account_col],
          "values": ["Account Coverage", 1, coverage_col, n_accounts, coverage_col],
          "fill": {"color": "#1f77b4"}
          })

        bar_chart.set_x_axis({"name": "Account"})
        bar_chart.set_y_axis({"name": "Coverage (%)", "num_format": '0"%"', "max": 100})
        bar_chart.set_legend({"position": "none"})
        account_ws.insert_chart("D2", bar_chart, {"x_scale": 7, "y_scale": 3})

    logger.info("Excel report generated at: %s", output_path)
