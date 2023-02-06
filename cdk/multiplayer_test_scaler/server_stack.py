# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2
)
import aws_cdk as cdk
from constructs import Construct

import os

from .constants import *
from .custom_image_builder_construct import CustomImageBuilderConstruct


class O3DEServerStack(Stack):
    """
    Create stack for deploying AWS resources required to run the multiplayer server
    """
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, security_group: ec2.SecurityGroup,
                 platform: str, project_name: str, image_id: str = '', **kwargs) \
            -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._vpc = vpc
        self._security_group = security_group
        self._platform = platform
        self._project_name = project_name

        self._server_port = self.node.try_get_context('server_port')
        if not self._server_port:
            self._server_port = DEFAULT_SERVER_PORT

        local_reference_machine_cidr = self.node.try_get_context('local_reference_machine_cidr')
        if local_reference_machine_cidr:
            ec2.CfnSecurityGroupIngress(
                self, f'{RESOURCE_ID_COMMON_PREFIX}LocalRefrenceMachineConnectionIngress',
                ip_protocol='udp',
                cidr_ip=local_reference_machine_cidr,
                description='Open the server port for local reference machines',
                from_port=int(self._server_port),
                group_id=self._security_group.security_group_id,
                to_port=int(self._server_port)
            )
            self._add_remote_client_ingress(local_reference_machine_cidr)

        # Create an IAM role to be used by the instance for remote connection
        self._instance_role = iam.Role(
            self, f'{RESOURCE_ID_COMMON_PREFIX}InstanceRole',
            description='Role to be used by instance for remote connection',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            path='/executionServiceEC2Role/'
        )

        # Add metrics submission IAM policy, if provided
        metrics_policy_export_name = self.node.try_get_context('metrics_policy_export_name')
        if metrics_policy_export_name:
            self._instance_role.add_managed_policy(
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, 'MetricsUserPolicy', cdk.Fn.import_value(metrics_policy_export_name))
            )

        self._key_pair = self.node.try_get_context('key_pair')
        if not self._key_pair:
            raise RuntimeError('EC2 key pair is required for deploying the Multiplayer Test Scaler. '
                            'Pass the key pair using \'-c key_pair={key_pair_value}\'')

        if not image_id:
            # No existing Amazon Machine Image (AMI) is provided.
            # Create one via EC2 Image Builder (https://aws.amazon.com/image-builder/)
            ami_construct = CustomImageBuilderConstruct(
                self, f'{RESOURCE_ID_COMMON_PREFIX}CustomImageBuilderConstruct',
                self._key_pair, self._instance_role, self._platform)
            image_id = ami_construct.custom_image_id

        self._launch_server_instance(image_id)

    def _add_remote_client_ingress(self, local_cidr: str) -> None:
        """
        Add platform specific remote connection ingress
        """
        if self._platform == PLATFORM_WINDOWS:
            ec2.CfnSecurityGroupIngress(
                self, f'{RESOURCE_ID_COMMON_PREFIX}RdpConnectionIngress',
                ip_protocol='tcp',
                cidr_ip=local_cidr,
                description='Allow RDP connection',
                from_port=RDP_CONNECTION_PORT,
                group_id=self._security_group.security_group_id,
                to_port=RDP_CONNECTION_PORT
            )

    def _launch_server_instance(self, image_id: str) -> None:
        """
        Launch an Amazon EC2 instance using the custom AMI
        :param image_id: ID of the custom AMI
        """
        server_commands_user_data = ec2.UserData.custom(
            SERVER_LAUNCH_SCRIPT.replace('{server_port}', str(self._server_port)).replace('{project_name}', self._project_name))

        server_private_ip = self.node.try_get_context('server_private_ip')
        if not server_private_ip:
            server_private_ip = DEFAULT_SERVER_PRIVATE_IP

        if self._platform == PLATFORM_WINDOWS:
            machine_image = ec2.GenericWindowsImage({self.region: image_id})
        else:
            raise RuntimeError(f'Server for the {self._platform} platform is not supported yet')

        server_instance = ec2.Instance(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ServerInstance',
            vpc=self._vpc,
            machine_image=machine_image,
            user_data=server_commands_user_data,
            key_name=self._key_pair,
            instance_type=ec2.InstanceType.of(SERVER_INSTANCE_CLASS, SERVER_INSTANCE_SIZE),
            security_group=self._security_group,
            block_devices=[
                ec2.BlockDevice(
                    device_name='/dev/sda1',
                    volume=ec2.BlockDeviceVolume.ebs(SERVER_INSTANCE_VOLUME_SIZE)
                )
            ],
            private_ip_address=server_private_ip,
            role=self._instance_role,
            vpc_subnets=ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_attributes(
                        self,
                        id=f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnet',
                        subnet_id=cdk.Fn.import_value(f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetId'),
                        availability_zone=cdk.Fn.import_value(f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetAvailabilityZone'),
                        route_table_id=cdk.Fn.import_value(f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetRouteTableId')
                    )
                ]
            ),
            require_imdsv2=True,
        )

        cdk.CfnOutput(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ServerIp',
            description='Public IP address of the server instance',
            value=server_instance.instance_public_ip)
