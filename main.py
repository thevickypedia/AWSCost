import json
import math
from datetime import datetime, timedelta

import boto3


def cost_explorer() -> None:
    """Uses cost explorer to get monthly cost."""
    # Cost Explorer is a global service
    client = boto3.client("ce", region_name="us-east-1")

    end_date = datetime.now()
    # Get cost data for the past 30 days
    start_date = end_date - timedelta(days=30)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date_str, "End": end_date_str},
        Granularity="MONTHLY",  # choose DAILY or HOURLY
        Metrics=[
            "UnblendedCost"
        ],  # Unblended cost is the cost of AWS resources before any applied discounts
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )
    for result in response["ResultsByTime"]:
        print(f"Time Period: {result['TimePeriod']}")
        for group in result["Groups"]:
            service = group["Keys"][0]
            cost = group["Metrics"]["UnblendedCost"]["Amount"]
            print(f"Service: {service}, Cost: {cost}")


def cost_per_gigabyte(byte_size) -> float:
    """Get cost per GB."""
    if byte_size <= 50_000_000_000_000:
        return 0.023
    if byte_size <= 450_000_000_000_000:
        return 0.022
    if byte_size >= 500_000_000_000_000:
        return 0.021
    raise ValueError("Refer https://aws.amazon.com/s3/pricing/ to add pricing options")


def cost_converter(total_size: int) -> float:
    """Round off cost value for the total size."""
    cost_per_gb = cost_per_gigabyte(total_size)
    cost_per_byte = cost_per_gb / (1024**3)
    total_cost = total_size * cost_per_byte
    return round(total_cost, 6)


def size_converter(byte_size) -> str:
    """Converts byte size into human-readable format."""
    if byte_size <= 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    index = int(math.floor(math.log(byte_size, 1024)))
    return f"{round(byte_size / pow(1024, index), 2)} {size_name[index]}"


class AWSS3Cost:
    """AWS S3 cost calculator.

    >>> AWSS3Cost

    """

    def __init__(self):
        self.s3_client = boto3.client("s3")

    def calculate(self):
        """Gather all the buckets and estimate the cost."""
        total_size = 0
        response = self.s3_client.list_buckets()
        bucket_values = {}
        for bucket in response["Buckets"]:
            bucket_name = bucket["Name"]
            total_bucket_size = 0
            number_of_ojects = 0
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        total_bucket_size += obj["Size"]
                        number_of_ojects += 1
            human_readable_size = size_converter(total_bucket_size)
            total_size += total_bucket_size
            bucket_values[bucket_name] = {
                "objects": number_of_ojects,
                "size": human_readable_size,
            }
        print(json.dumps(bucket_values, indent=2))
        human_readable_total_size = size_converter(total_size)
        print("\n")
        print(f"Total size of all buckets: {human_readable_total_size!r}")
        print(
            f"Approximate monthly cost for {human_readable_total_size!r}: ${cost_converter(total_size)!r}"
        )


if __name__ == "__main__":
    # aws_s3_cost = AWSS3Cost()
    # aws_s3_cost.calculate()
    cost_explorer()
