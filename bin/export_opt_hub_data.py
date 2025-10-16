import boto3
import csv

client = boto3.client('cost-optimization-hub', region_name='us-east-1')

def fetch_recommendations():
    recommendations = []
    paginator = client.get_paginator('list_recommendations')
    
    for page in paginator.paginate():
        for item in page['items']:
            print(item)

            recommendations.append({
                'recommendationId': item['recommendationId'],
                'accountId': item['accountId'],
                'region': item['region'],
                'resourceId': item['resourceId'],
                'currentResourceType': item['currentResourceType'],
                'recommendedResourceType': item['recommendedResourceType'],
                'estimatedMonthlySavings': item['estimatedMonthlySavings'],
                'estimatedSavingsPercentage': item['estimatedSavingsPercentage'],
                'recommendationType': item['recommendationType']
            })
    
    return recommendations

def save_to_csv(data, filename='cost_optimization_recommendations.csv'):
    if not data:
        print("No data to write.")
        return

    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print(f"Data successfully written to {filename}")


if __name__ == "__main__":
    recommendations = fetch_recommendations()
    save_to_csv(recommendations)
