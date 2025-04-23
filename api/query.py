import boto3
import time

athena_client = boto3.client('athena')

database = 'cur_v2_hourly'
output_location = 's3://athena-jn'

def process_query(query):

    query_execution = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': database,
        },
        ResultConfiguration={
            'OutputLocation': output_location,
        }
    )
    execution_id = query_execution['QueryExecutionId']

    costs = {
    }

    status_code = 400
    message = ''

    while True:
        time.sleep(0.1)
        query_details = athena_client.get_query_execution(
            QueryExecutionId=execution_id
        )
        state = query_details['QueryExecution']['Status']['State']

        # The state can have several values, such as QUEUED, RUNNING, SUCCEEDED, FAILED, and CANCELLED.
        if state == 'SUCCEEDED':
            response_query_result = athena_client.get_query_results(
                QueryExecutionId=execution_id
            )
            status_code = 200
            for row in response_query_result['ResultSet']['Rows'][1:]:
                key = row['Data'][0]['VarCharValue']
                value = float(row['Data'][1]['VarCharValue'])
                if value >0:
                    costs[key] = value
            return {
                'statusCode': status_code,
                'body': costs
            }
        elif state == 'FAILED':
            message = query_details['QueryExecution']['Status']['StateChangeReason']
            break
        elif state == 'CANCELLED':
            message = 'Query cancelled'
            break

    return {
        'statusCode': status_code,
        'body': message
    }

def get_costs_period(billing_period, namespace):
  # TODO check that the billing period is valid
  query = f"select product['product_name'], round(sum(line_item_unblended_cost),2) as cost from data where billing_period = '{billing_period}' and resource_tags['user_namespace'] = '{namespace}' group by product['product_name'] order by cost desc limit 20;"
  return process_query(query)

def get_costs_dates(start_date, end_date, namespace):
    # TODO check that the dates are valid
    query = f"select product['product_name'], round(sum(line_item_unblended_cost),2) as cost from data where resource_tags['user_namespace'] = '{namespace}' and line_item_usage_start_date >= DATE '{start_date}' and line_item_usage_start_date <= DATE '{end_date}' group by product['product_name'] order by cost desc limit 20;"
    return process_query(query)

def lambda_handler(event, context):
    # Extract path parameters
    params = event.get('pathParameters', {})
    nm = params.get('namespace')
    bp = params.get('billing_period')

    # Check if start_date and end_date exist
    start_date_str = params.get('start_date')
    end_date_str = params.get('end_date')

    if start_date_str and end_date_str and nm:
        return get_costs_dates(start_date_str, end_date_str, nm)
    elif bp and nm:
        return get_costs_period(bp, nm)
    else:
        return {
            'statusCode': 400,
            'body': 'Invalid parameters: missing namespace and/or billing period'
        }

# simulate the input sent to the lambda
event = {
    "pathParameters": {
        "billing_period": "2025-02",
        "namespace": "hmpps-book-secure-move-api-staging"
    }
}

costs = lambda_handler(event, {})
print(costs)

event = {
    "pathParameters": {
        "start_date": "2025-02-01",
        "end_date": "2025-02-28",
        "namespace": "hmpps-book-secure-move-api-staging"
    }
}
costs = lambda_handler(event, {})
print(costs)
