import json
import math
import os
from datetime import datetime, timedelta

import boto3
import dotenv

from config import EnvConfig, Granularity


def env_config() -> EnvConfig:
    """Function to load all the env vars."""
    env_file = os.getenv("env_file") or os.getenv("ENV_FILE") or ".env"
    dotenv.load_dotenv(dotenv_path=env_file)
    env_vars = {key.upper(): value for key, value in os.environ.items()}
    return EnvConfig(
        region_name=env_vars.get("REGION_NAME"),
        profile_name=env_vars.get("PROFILE_NAME"),
        aws_access_key_id=env_vars.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=env_vars.get("AWS_SECRET_ACCESS_KEY"),
    )


def date(date_cls: datetime) -> str:
    """Converts a datetime object to a string indicating the date part."""
    return date_cls.strftime("%A %b %d, %Y")


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

    def cost_explorer(
        self,
        start_date: str = None,
        end_date: str = None,
        total: bool = False,
        granularity: Granularity = Granularity.MONTHLY,
    ) -> None:
        """Uses cost explorer to get monthly cost."""
        dt_format = "%Y-%m-%d"
        now = datetime.now()

        if start_date:
            start_date = datetime.strptime(start_date, dt_format)
        else:
            start_date = end_date - timedelta(days=30)

        if end_date:
            end_date = datetime.strptime(end_date, dt_format)
        else:
            end_date = now

        assert start_date <= now, "start_date cannot be in the future"
        assert end_date > start_date, "end_date cannot be greater than start date"

        start_date_str = start_date.strftime(dt_format)
        end_date_str = end_date.strftime(dt_format)

        # Unblended cost is the cost of AWS resources before any applied discounts
        if total:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={"Start": start_date_str, "End": end_date_str},
                Granularity=granularity.value,
                Metrics=["UnblendedCost"],
            )
            total_cost = 0
            for result in response["ResultsByTime"]:
                total_cost += float(result["Total"]["UnblendedCost"]["Amount"])
            print(
                f"Total cost from {date(start_date)!r} to {date(end_date)!r}: ${round(total_cost, 2)}"
            )
        else:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={"Start": start_date_str, "End": end_date_str},
                Granularity=granularity.value,
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            cost_breakdown = {}
            for result in response["ResultsByTime"]:
                for group in result["Groups"]:
                    service = group["Keys"][0]
                    cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if not cost:
                        continue
                    if cost_breakdown.get(service):
                        cost_breakdown[service] += cost
                    else:
                        cost_breakdown[service] = cost
            print(f"Cost breakdown from {date(start_date)!r} to {date(end_date)!r}")
            for key, value in cost_breakdown.items():
                rounded = round(value, 4)
                if rounded == 0.0000:
                    cost = f"{rounded:.4f} ({value})"
                elif rounded.is_integer():
                    cost = int(rounded)
                else:
                    cost = f"{rounded:.4f}"
                print(f"Service: {key}\nCost: {cost}\n")

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
    aws_client.cost_explorer(start_date="2025-01-01")
