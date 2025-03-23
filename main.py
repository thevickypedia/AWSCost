import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import boto3
import dotenv


@dataclass
class EnvConfig:
    """Dataclass for environment variables.

    >>> EnvConfig

    """

    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str
    profile_name: str


def env_config() -> EnvConfig:
    """Function to load all the env vars."""
    env_file = os.getenv("env_file") or os.getenv("ENV_FILE") or ".env"
    dotenv.load_dotenv(dotenv_path=env_file)
    env_vars = {key.upper(): value for key, value in os.environ.items()}
    return EnvConfig(
        aws_access_key_id=env_vars.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=env_vars.get("AWS_SECRET_ACCESS_KEY"),
        region_name=env_vars.get("REGION_NAME"),
        profile_name=env_vars.get("PROFILE_NAME"),
    )


def size_converter(byte_size) -> str:
    """Converts byte size into human-readable format."""
    if byte_size <= 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    index = int(math.floor(math.log(byte_size, 1024)))
    return f"{round(byte_size / pow(1024, index), 2)} {size_name[index]}"


class AWSClient:
    """AWS client.

    >>> AWSClient

    """

    def __init__(self):
        config: EnvConfig = env_config()
        session = boto3.Session(
            region_name=config.region_name,
            profile_name=config.profile_name,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        self.s3_client = session.client("s3")
        # Cost Explorer is a global service
        self.ce_client = session.client("ce", region_name="us-east-1")

    def cost_explorer(self) -> None:
        """Uses cost explorer to get monthly cost."""
        end_date = datetime.now()
        # Get cost data for the past 30 days
        start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Unblended cost is the cost of AWS resources before any applied discounts
        response = self.ce_client.get_cost_and_usage(
            TimePeriod={"Start": start_date_str, "End": end_date_str},
            Granularity="MONTHLY",  # choose DAILY or HOURLY
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        for result in response["ResultsByTime"]:
            print(f"Time Period: {result['TimePeriod']}")
            for group in result["Groups"]:
                service = group["Keys"][0]
                cost = group["Metrics"]["UnblendedCost"]["Amount"]
                print(f"Service: {service}, Cost: {cost}")

    def s3_usage(self):
        """Gather all the buckets and their usage."""
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


if __name__ == "__main__":
    aws_client = AWSClient()
    aws_client.cost_explorer()
