import re
from typing import Iterable, Union

import boto3


class ComputeEnvironmentMismatchError(Exception):
    pass


class JobQueueMismatchError(Exception):
    pass


class JobBlueprintMismatchError(Exception):
    pass


class JobBlueprintCreationError(Exception):
    pass


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

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.describe_compute_environments

        nextToken = None
        first = True
        while first or nextToken:
            kwargs = {}
            # handle a non-first page
            if nextToken:
                kwargs["nextToken"] = nextToken

            response = batch_client.describe_compute_environments(
                **kwargs,
            )
            for compute_environment in response["computeEnvironments"]:
                if compute_environment["computeEnvironmentName"] == name:
                    # found a name match
                    env_type = compute_environment["type"]
                    env_state = compute_environment["state"]
                    env_status = compute_environment["status"]
                    env_status_reason = compute_environment["statusReason"]
                    env_service_role = compute_environment["serviceRole"]
                    env_compute_type = compute_environment["computeResources"]["type"]
                    env_compute_maxvcpus = compute_environment["computeResources"][
                        "maxvCpus"
                    ]
                    env_compute_securitygroupids = compute_environment[
                        "computeResources"
                    ]["securityGroupIds"]
                    env_compute_subnets = compute_environment["computeResources"][
                        "subnets"
                    ]

                    if env_type != "MANAGED":
                        raise ComputeEnvironmentMismatchError(f"type is {env_type}")
                    if env_state != "DISABLED":
                        raise ComputeEnvironmentMismatchError(f"state is {env_state}")
                    if env_status not in ("DELETING", "DELETED", "INVALID"):
                        raise ComputeEnvironmentMismatchError(
                            f"status is {env_status} because {env_status_reason}"
                        )
                    if env_service_role != service_role_arn:
                        raise ComputeEnvironmentMismatchError(
                            f"service role is {env_service_role}"
                        )
                    if env_compute_type != "FARGATE":
                        raise ComputeEnvironmentMismatchError(
                            f"type is {env_compute_type}"
                        )
                    if env_compute_maxvcpus != 100:
                        raise ComputeEnvironmentMismatchError(
                            f"maxvCpus is {env_compute_type}"
                        )
                    if frozenset(env_compute_securitygroupids) != frozenset(
                        [security_group_id]
                    ):
                        raise ComputeEnvironmentMismatchError(
                            f"security group ids are {env_compute_type}"
                        )
                    if frozenset(env_compute_subnets) != frozenset(subnet_ids):
                        raise ComputeEnvironmentMismatchError(
                            f"subnets are {env_compute_type}"
                        )

                    # got to here without problem so we can use it
                    return compute_environment["computeEnvironmentArn"]

            # mark that we've finished the first page
            first = False
            # move to the next page, if applicable
            if "nextToken" in response and response["nextToken"]:
                nextToken = response["nextToken"]
            else:
                # no next page
                nextToken = None

        # no match found
        return None

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

    def _get_queue(
        self, batch_client, name: str, compute_environment_arn: str
    ) -> Union[None, str]:

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.describe_job_queues

        nextToken = None
        first = True
        while first or nextToken:
            kwargs = {}
            # handle a non-first page
            if nextToken:
                kwargs["nextToken"] = nextToken

            response = batch_client.describe_job_queues(
                **kwargs,
            )
            for job_queue in response["jobQueues"]:
                if job_queue["jobQueueName"] == name:
                    # found a name match

                    queue_state = job_queue["state"]
                    queue_status = job_queue["status"]
                    queue_status_reason = job_queue["statusReason"]
                    queue_compute_envs = job_queue["computeEnvironmentOrder"]

                    if queue_state != "DISABLED":
                        raise JobQueueMismatchError(f"state is {queue_state}")
                    if queue_status not in ("DELETING", "DELETED", "INVALID"):
                        raise JobQueueMismatchError(
                            f"status is {queue_status} because {queue_status_reason}"
                        )
                    if len(queue_compute_envs) != 1:
                        raise JobQueueMismatchError(
                            f"status is {queue_status} because {queue_status_reason}"
                        )

                    # got to here without problem so we can use it
                    return job_queue["jobQueueArn"]

            # mark that we've finished the first page
            first = False
            # move to the next page, if applicable
            if "nextToken" in response and response["nextToken"]:
                nextToken = response["nextToken"]
            else:
                # no next page
                nextToken = None

        # no match found
        return None

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

    def _get_blueprint(
        self,
        batch_client,
        name: str,
        image: str,
        vcpu: Union[float, int],
        memory: int,
        command: Iterable[str],
    ) -> str:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.describe_job_definitions

        nextToken = None
        first = True
        while first or nextToken:
            kwargs = {}
            # handle a non-first page
            if nextToken:
                kwargs["nextToken"] = nextToken

            response = batch_client.describe_job_definitions(
                **kwargs,
            )
            for blueprint in response["jobDefinitions"]:
                if blueprint["jobDefinitionName"] == name:
                    # found a name match

                    if blueprint["type"] != "container":
                        raise JobBlueprintMismatchError(f"type is {blueprint['type']}")
                    if blueprint["containerProperties"]["image"] != image:
                        raise JobBlueprintMismatchError(
                            f"image is {blueprint['containerProperties']['image']} not {image}"
                        )
                    if float(blueprint["containerProperties"]["vcpus"]) != vcpu:
                        raise JobBlueprintMismatchError(
                            f"vcpu is {blueprint['containerProperties']['vcpus']} not {vcpu}"
                        )
                    if int(blueprint["containerProperties"]["memory"]) != memory:
                        raise JobBlueprintMismatchError(
                            f"memory is {blueprint['containerProperties']['memory']} not {memory}"
                        )
                    if tuple(blueprint["containerProperties"]["command"]) != tuple(
                        command
                    ):
                        raise JobBlueprintMismatchError(
                            f"command is {blueprint['containerProperties']['command']} not {command}"
                        )

                    # TODO more validation

                    # got to here without problem so we can use it
                    return blueprint["jobDefinitionArn"]

            # mark that we've finished the first page
            first = False
            # move to the next page, if applicable
            if "nextToken" in response and response["nextToken"]:
                nextToken = response["nextToken"]
            else:
                # no next page
                nextToken = None

        # no match found
        return None

    def _create_blueprint(
        self,
        batch_client,
        name: str,
        image: str,
        vcpu: Union[float, int],
        memory: int,
        command: Iterable[str],
    ) -> str:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.register_job_definition

        # only certain vcpu & memory combinations allowed on Fargate
        permitted_memory_vcpu = {
            512: (0.25,),
            1024: (0.25, 0.5),
            2048: (0.25, 0.5, 1),
            3072: (0.5, 1),
            4096: (0.5, 1, 2),
            5120: (1, 2),
            6144: (1, 2),
            7168: (1, 2),
            8192: (1, 2, 4),
            9216: (2, 4),
            10240: (2, 4),
            11264: (2, 4),
            12288: (2, 4),
            13312: (2, 4),
            14336: (2, 4),
            15360: (2, 4),
            16384: (2, 4),
            17408: (4,),
            18432: (4,),
            19456: (4,),
            20480: (4,),
            21504: (4,),
            22528: (4,),
            23552: (4,),
            24576: (4,),
            25600: (4,),
            26624: (4,),
            27648: (4,),
            28672: (4,),
            29696: (4,),
            30720: (4,),
        }
        if memory not in permitted_memory_vcpu:
            raise JobBlueprintCreationError(f"memory {memory} not acceptable")
        if vcpu not in permitted_memory_vcpu[memory]:
            raise JobBlueprintCreationError(f"vcpu {vcpu} not acceptable")

        containerProperties = {
            "image": image,
            # When this parameter is true, the container is given read-only access to its
            # root file system. This parameter maps to ReadonlyRootfs in the Create a
            # container section of the Docker Remote API and the --read-only option to
            # docker run .
            "readonlyRootFilesystem": True,
            "resourceRequirements": [
                {"type": "VCPU", "value": str(vcpu)},
                {"type": "MEMORY", "value": str(memory)},
            ],
        }
        # optionally add a command if specified
        if command:
            containerProperties["command"] = command

        # send the actual client request
        response = batch_client.register_job_definition(
            jobDefinitionName=name,
            type="container",
            containerProperties=containerProperties,
            platformCapabilities=["FARGATE"],
        )

        return str(response["jobDefinitionArn"])  # , int(response["revision"])

    def _get_or_create_blueprint(
        self,
        batch_client,
        name: str,
        image: str,
        vcpu: Union[float, int],
        memory: int,
        command: Iterable[str],
    ) -> str:

        # Note: this is vulnerable to race conditions if another process creates between
        # the get and the create.
        existing = self._get_blueprint(batch_client, name, image, vcpu, memory, command)
        if existing:
            return existing
        else:
            return self._create_blueprint(
                batch_client, name, image, vcpu, memory, command
            )

    def build(
        self,
        service_role_arn: str,
        security_group_id: str,
        subnet_ids: Iterable[str],
        image_name: str,
        image_tag: str,
        image_repo: Union[str, None],
        vcpu: Union[float, int] = 0.25,
        memory: int = 512,
        command: Iterable[str] = [],
        name_prefix: str = "chorecoral",
    ):

        # TODO when a default service role is created its called AWSServiceRoleForBatch
        # see https://docs.aws.amazon.com/batch/latest/userguide/service_IAM_role.html
        # We should detect and use this role if no service role is given.

        # TODO when a defauult execution rols is created its called ecsTaskExecutionRole
        # see https://docs.aws.amazon.com/batch/latest/userguide/execution-IAM-role.html
        # We should detect and use this role if no execution role is given

        # build a single string for the image to be used
        image_full = image_name
        if image_tag:
            image_full = image_full + ":" + image_tag
        if image_repo:
            image_full = image_repo + "/" + image_full

        # create a name for this in general
        # name must only be alphanumeric, with _- in middle
        name = re.sub("[^A-Za-z0-9_-]", "_", name_prefix + "_" + image_full)
        if not re.match("^[A-Za-z0-9][A-Za-z0-9_-]{1,126}[A-Za-z0-9]$", name):
            raise ValueError(f"name invalid '{name}'")

        # start up a client
        batch_client = boto3.client("batch")

        # ensure compute environment exists
        compute_arn = self._get_or_create_compute_environment(
            batch_client, name, service_role_arn, security_group_id, subnet_ids
        )

        # ensure queue exists
        self._get_or_create_queue(batch_client, name, compute_arn)

        # ensure blueprint exists
        self._get_or_create_blueprint(
            batch_client, name, image_full, vcpu, memory, command
        )

        # TODO create job
