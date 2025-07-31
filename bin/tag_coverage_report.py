import boto3
import logging
import time
import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def athena_execute_query(query:str, database='cur_v2_database', s3_output='s3://coat-production-cur-v2-hourly/athena-results/'):

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

    while True:
        result = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = result['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(2)

    if state != 'SUCCEEDED':
        raise Exception(f"Query failed or was cancelled: {state}")

    return query_execution_id


def generate_query_total_tagging_coverage(billing_period: str, business_unit: str):

    query_total_tagging_coverage = f"""
    SELECT 
      100.0 * 
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
            AND line_item_unblended_cost > 0
            AND resource_tags['user_business_unit'] IS NOT NULL
            AND resource_tags['user_business_unit'] <> ''

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


def generate_query_list_of_aws_accounts(billing_period: str, business_unit: str):

    query_list_of_aws_accounts = f"""
    SELECT DISTINCT line_item_usage_account_id, line_item_usage_account_name
    FROM data
    WHERE billing_period = '{billing_period}'
    AND cost_category['business_unit'] = '{business_unit}'
    """
    return query_list_of_aws_accounts


def generate_query_tagging_per_aws_account(
    aws_account_name: str,
    billing_period: str,
    business_unit: str
  ):

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
            AND resource_tags['user_business_unit'] IS NOT NULL
            AND resource_tags['user_business_unit'] <> ''
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


def generate_tagging_coverage_report(
    ou: str,
    billing_period: str
) -> None:

    billing_period = '2025-07'
    business_unit = 'HMPPS'

    query_total_tagging_coverage = generate_query_total_tagging_coverage(billing_period, business_unit)
    query_list_of_aws_accounts = generate_query_list_of_aws_accounts(billing_period, business_unit)

    athena_tagging_cov_execution_id = athena_execute_query(query_total_tagging_coverage)
    results_tagging_coverage = boto3.client('athena').get_query_results(QueryExecutionId=athena_tagging_cov_execution_id)
    total_tagging_cov_percentage = float(results_tagging_coverage['ResultSet']['Rows'][1]['Data'][0]['VarCharValue'])

    athena_bu_aws_account_ex_id = athena_execute_query(query_list_of_aws_accounts)
    results_bu_aws_accounts = boto3.client('athena').get_query_results(QueryExecutionId=athena_bu_aws_account_ex_id)
    rows = results_bu_aws_accounts['ResultSet']['Rows']
    cleaned_data = [
      [col['VarCharValue'] for col in row['Data']]
      for row in rows
      if len(row['Data']) == 2
      ]

    headers = cleaned_data[0]
    df_aws_accounts = pd.DataFrame(cleaned_data[1:], columns=headers)

    for index, row in df_aws_accounts.iterrows():
        aws_account_name = row['line_item_usage_account_name']
        query_tagging_per_aws_account = generate_query_tagging_per_aws_account(aws_account_name, billing_period, business_unit)
        athena_aws_account_ex_id = athena_execute_query(query_tagging_per_aws_account)
        results_aws_account = boto3.client('athena').get_query_results(QueryExecutionId=athena_aws_account_ex_id)
        account_tagging_cov_percentage = float(results_aws_account['ResultSet']['Rows'][1]['Data'][0]['VarCharValue']) if 'VarCharValue' in results_aws_account['ResultSet']['Rows'][1]['Data'][0] else None
        df_aws_accounts.at[index, 'account_tagging_coverage_pct'] = account_tagging_cov_percentage

    df_aws_accounts = df_aws_accounts.sort_values(by='line_item_usage_account_name').reset_index(drop=True)
