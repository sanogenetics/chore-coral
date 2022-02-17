from typing import Iterable, Union

import boto3


class Builder:
    def __init__(self):
        pass

    def _get_compute_environment(
        self,
        batch_client,
        name: str,
        service_role_arn: str,
        security_group_id: str,
        subnet_ids: Iterable[str],
    ) -> Union[str, None]:
        raise NotImplementedError()

    def _create_compute_environment(
        self,
        batch_client,
        name: str,
        service_role_arn: str,
        security_group_id: str,
        subnet_ids: Iterable[str],
    ) -> str:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.create_compute_environment
        response = batch_client.create_compute_environment(
            computeEnvironmentName=name,
            type="MANAGED",
            state="ENABLED",
            computeResources={
                # https://aws.amazon.com/fargate/ - Serverless compute for containers
                "type": "FARGATE",
                # The maximum number of Amazon EC2 vCPUs that a compute environment can reach.
                "maxvCpus": 100,
                # The VPC subnets where the compute resources are launched. These subnets
                # must be within the same VPC. Fargate compute resources can contain up to 16
                # subnets. For more information, see VPCs and Subnets in the Amazon VPC User
                # Guide https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html.
                "subnets": list(subnet_ids),
                # The Amazon EC2 security groups associated with instances launched in the
                # compute environment. One or more security groups must be specified, either
                # in securityGroupIds or using a launch template referenced in launchTemplate.
                # This parameter is required for jobs that are running on Fargate resources
                # and must contain at least one security group. Fargate doesn't support
                # launch templates. If security groups are specified using both
                # securityGroupIds and launchTemplate , the values in securityGroupIds are
                # used.
                "securityGroupIds": [security_group_id],
            },
            serviceRole=service_role_arn,
        )
        return response["computeEnvironmentArn"]

    def _get_or_create_compute_environment(
        self,
        batch_client,
        name: str,
        service_role_arn: str,
        security_group_id: str,
        subnet_ids: Iterable[str],
    ) -> str:
        # Note: this is vulnerable to race conditions if another process creates between
        # the get and the create.
        existing = self._get_compute_environment(
            batch_client, name, service_role_arn, security_group_id, subnet_ids
        )
        if existing:
            return existing
        else:
            return self._create_compute_environment(
                batch_client, name, service_role_arn, security_group_id, subnet_ids
            )

    def _get_queue(self, batch_client, name: str, compute_environment_arn: str) -> str:
        raise NotImplementedError()

    def _create_queue(
        self, batch_client, name: str, compute_environment_arn: str
    ) -> str:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.create_job_queue
        response = batch_client.create_job_queue(
            jobQueueName=name,
            state="ENABLED",
            priority=10,
            computeEnvironmentOrder=[
                {"order": 10, "computeEnvironment": compute_environment_arn}
            ],
        )
        return response["jobQueueArn"]

    def _get_or_create_queue(
        self, batch_client, name: str, compute_environment_arn: str
    ) -> str:
        # Note: this is vulnerable to race conditions if another process creates between
        # the get and the create.
        existing = self._get_queue(batch_client, name, compute_environment_arn)
        if existing:
            return existing
        else:
            return self._create_queue(batch_client, name, compute_environment_arn)

    def build(
        self,
        service_role_arn: str,
        security_group_id: str,
        subnet_ids: Iterable[str],
        image_name: str,
        image_tag: str,
        name_prefix: str = "chorecoral",
    ):
        # create a name for this in general
        name = f"{name_prefix}:{image_name}:{image_tag}"

        # start up a client
        batch_client = boto3.client("batch")

        # ensure compute environment exists
        compute_arn = self._get_or_create_compute_environment(
            batch_client, name, service_role_arn, security_group_id, subnet_ids
        )

        # ensure queue exists
        self._get_or_create_queue(batch_client, name, compute_arn)

        # TODO ensure blueprint exists

        # TODO create job