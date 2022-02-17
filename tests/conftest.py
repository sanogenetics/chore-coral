import os
from typing import List

import boto3
import moto
import pytest


@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="session")
def aws_s3(aws_credentials):
    with moto.mock_s3():
        yield boto3.client("s3")


@pytest.fixture(scope="session")
def aws_batch(aws_credentials):
    with moto.mock_batch():
        yield boto3.client("batch")


@pytest.fixture(scope="session")
def aws_iam(aws_credentials):
    with moto.mock_iam():
        yield boto3.client("iam")


@pytest.fixture(scope="session")
def aws_ec2(aws_credentials):
    with moto.mock_ec2():
        yield boto3.client("ec2")


@pytest.fixture(scope="session")
def service_role(aws_iam) -> str:
    role = aws_iam.create_role(
        RoleName="test service role",
        AssumeRolePolicyDocument="{}",
    )
    role_arn = role.get("Role").get("Arn")
    return role_arn


@pytest.fixture(scope="session")
def security_group(aws_ec2) -> str:
    response = aws_ec2.create_security_group(
        GroupName="test security group", Description="test security group"
    )
    return response["GroupId"]


@pytest.fixture(scope="session")
def virtual_private_cloud(aws_ec2) -> str:
    # get a default vpc if it exists
    response = aws_ec2.describe_vpcs()
    for vpc in response["Vpcs"]:
        if vpc["IsDefault"] is True:
            return vpc["VpcId"]

    # TODO create a new default vpc
    raise NotImplementedError()


@pytest.fixture(scope="session")
def subnets(aws_ec2, virtual_private_cloud: str) -> List[str]:
    response = aws_ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [virtual_private_cloud]}]
    )
    subnet_ids = [subnet["SubnetId"] for subnet in response["Subnets"]]
    return subnet_ids
