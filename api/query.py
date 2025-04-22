import boto3
import time

athena_client = boto3.client('athena')

billing_period  = '2025-02'
namespace = 'cccd-dev'
database = 'cur_v2_hourly'
output_location = 's3://athena-jn'

#def lambda_handler(event, context):
def get_costs():

  # check that the billing period is valid

  query = f"select product['product_name'], round(sum(line_item_unblended_cost),2) as cost from data where billing_period = '{billing_period}' and resource_tags['user_namespace'] = '{namespace}' group by product['product_name'] order by cost desc limit 10;"

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
          break
      elif state == 'CANCELLED':
          break

  return {
      'statusCode': status_code,
      'body': f"ERROR"
  }

costs = get_costs()
print(costs)