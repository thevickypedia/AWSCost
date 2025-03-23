from enum import Enum
from dataclasses import dataclass

@dataclass
class EnvConfig:
    """Dataclass for environment variables.

    >>> EnvConfig

    """

    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str
    profile_name: str


class Granularity(Enum):
    HOURLY: str = "HOURLY"
    DAILY: str = "DAILY"
    MONTHLY: str = "MONTHLY"
