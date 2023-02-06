# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_ecr_assets as ecr_asset
)
import aws_cdk as cdk
from constructs import Construct

from .constants import *


class O3DEClientScalerStack(Stack):
    """
    Create stack for deploying AWS resources required to run the multiplayer clients
    """
    def __init__(self, scope: Construct, id_: str, vpc: ec2.Vpc, security_group: ec2.SecurityGroup,
                 platform: str, project_name: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        self._vpc = vpc
        self._security_group = security_group
        self._platform = platform
        self._project_name = project_name

        # Create the cluster for the Amazon ECS service
        self._cluster = ecs.Cluster(
            self, 'MultiplayerTestScalerEcsCLuster',
            vpc=self._vpc
        )

        client_task_definition = self._create_client_task_definition(f'{RESOURCE_ID_COMMON_PREFIX}ClientTaskDef')
        self._launch_client_tasks(client_task_definition)

    def _create_client_task_definition(self, id_: str) -> ecs.FargateTaskDefinition:
        """
        Create the AWS Fargate task definition for clients
        :param id_: Task definition construct ID
        :return: AWS Fargate Task definition
        """
        operating_system_family = ECS_TASK_OPERATING_SYSTEM_FAMILY_MAP.get(self._platform)
        if not operating_system_family:
            raise RuntimeError(f'Client for the {self._platform} platform is not supported yet')

        client_task_definition = ecs.FargateTaskDefinition(
            self, id_,
            memory_limit_mib=ECS_TASK_MEMORY_LIMIT_MIB,
            cpu=ECS_TASK_CPU_UNITS,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=operating_system_family,
                cpu_architecture=ECS_TASK_CPU_ARCHITECTURE
            )
        )

        # Create the container image and push it to the CDK default Amazon Elastic Container Registry (ECR) repository
        docker_image = ecr_asset.DockerImageAsset(
            self, 'MultiplayerTestScalerDockerImage',
            directory=f'{ASSET_DIR_ROOT}/{self._platform}'
        )

        ecs_launch_cmd = ECS_TASK_COMMAND.replace('{project_name}', self._project_name)
        client_task_definition.add_container(
            f'{RESOURCE_ID_COMMON_PREFIX}ClientContainer',
            image=ecs.ContainerImage.from_docker_image_asset(docker_image),  # image is tagged according to its asset hash by default
            entry_point=['powershell.exe'],
            command=[ecs_launch_cmd],
            logging=ecs.LogDriver.aws_logs(
                stream_prefix=ECS_TASK_LOGGING_STREAM_PREFIX
            )
        )

        return client_task_definition

    def _launch_client_tasks(self, client_task_definition: ecs.FargateTaskDefinition) -> None:
        """
        Launch the Amazon ECS service for running the client tasks
        :param client_task_definition: AWS Fargate task definition
        """
        client_count = self.node.try_get_context('client_count')  # how many copies of the client we want to run
        if not client_count:
            raise RuntimeError('Client count is required for deploying the Multiplayer Test Scaler. '
                            'Pass the client count using \'-c client_count={client_count}\'')

        client_subnet_ids = cdk.Fn.import_value(f'{RESOURCE_ID_COMMON_PREFIX}ClientSubnetIds')
        ecs.FargateService(
            self, f'{RESOURCE_ID_COMMON_PREFIX}ClientService',
            cluster=self._cluster,
            task_definition=client_task_definition,
            desired_count=int(client_count),
            security_groups=[self._security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_id(
                        self,
                        id=f'{RESOURCE_ID_COMMON_PREFIX}ClientSubnet{index}',
                        subnet_id=subnet_id
                    ) for index, subnet_id in enumerate(cdk.Fn.split(',', client_subnet_ids))
                ]
            )
        )
