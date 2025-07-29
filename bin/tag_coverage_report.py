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


def generate_tagging_coverage_report(
    ou:str,
    billing_period:str,
    default_tags=["business_unit"]
) -> None:

    billing_period='2025-07'
    business_unit='HMPPS'
    query_total_tagging_coverage = f"""
    SELECT 
      100.0 * 
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
            AND resource_tags['user_business_unit'] IS NOT NULL
            AND resource_tags['user_business_unit'] <> ''
        ) 
      / 
        (
          SELECT SUM(line_item_unblended_cost)
          FROM data
          WHERE billing_period = '{billing_period}'
            AND cost_category['business_unit'] = '{business_unit}'
        ) 
      AS tagging_coverage_pct
      """
      
    query_list_of_aws_accounts = f"""
    SELECT DISTINCT line_item_usage_account_id, line_item_usage_account_name
    FROM data
    WHERE billing_period = '{billing_period}'
    AND cost_category['business_unit'] = '{business_unit}'
    """
      

    athena_tagging_cov_execution_id = athena_execute_query(query_total_tagging_coverage)
    results_tagging_coverage = boto3.client('athena').get_query_results(QueryExecutionId=athena_tagging_cov_execution_id)
    total_tagging_cov_percentage = float(results_tagging_coverage['ResultSet']['Rows'][1]['Data'][0]['VarCharValue'])

    athena_business_unit_aws_account_ex_id = athena_execute_query(query_list_of_aws_accounts)
    business_unit_aws_accounts_list = boto3.client('athena').get_query_results(QueryExecutionId=athena_business_unit_aws_account_ex_id)
