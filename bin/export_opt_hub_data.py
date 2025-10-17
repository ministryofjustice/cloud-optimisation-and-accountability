import csv
import boto3

client = boto3.client('cost-optimization-hub', region_name='us-east-1')


def fetch_recommendations():
    recommendations = []
    paginator = client.get_paginator('list_recommendations')

    for page in paginator.paginate():
        for item in page['items']:
            recommendations.append({
                'recommendationId':
                    item.get('recommendationId', ""),
                'accountId':
                    item.get('accountId', ""),
                'region':
                    item.get('region', ""),
                'resourceId':
                    item.get('resourceId', ""),
                'resourceArn':
                    item.get('resourceArn', ""),
                'currentResourceType':
                    item.get('currentResourceType', ""),
                'recommendedResourceType':
                    item.get('recommendedResourceType', ""),
                'estimatedMonthlySavings':
                    item.get('estimatedMonthlySavings', ""),
                'estimatedSavingsPercentage':
                    item.get('estimatedSavingsPercentage', ""),
                'estimatedMonthlyCost':
                    item.get('estimatedMonthlyCost', ""),
                'currencyCode':
                    item.get('currencyCode', ""),
                'implementationEffort':
                    item.get('implementationEffort', ""),
                'restartNeeded':
                    item.get('restartNeeded', ""),
                'actionType':
                    item.get('actionType', ""),
                'rollbackPossible':
                    item.get('rollbackPossible', ""),
                'currentResourceSummary':
                    item.get('currentResourceSummary', ""),
                'recommendedResourceSummary':
                    item.get('recommendedResourceSummary', ""),
                'lastRefreshTimestamp':
                    item.get('lastRefreshTimestamp', ""),
                'recommendationLookbackPeriodInDays': 
                    item.get('recommendationLookbackPeriodInDays', ""),
                'source':
                    item.get('source', ""),
                'tags':
                    item.get('tags', "")
            })

    return recommendations


def save_to_csv(data, filename='cost_optimization_recommendations.csv'):
    if not data:
        print("No data to write.")
        return

    with open(filename, mode='w', newline='', encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print(f"Data successfully written to {filename}")


if __name__ == "__main__":
    save_to_csv(fetch_recommendations())
