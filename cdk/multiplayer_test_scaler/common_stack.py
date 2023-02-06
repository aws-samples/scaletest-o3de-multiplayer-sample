# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
import aws_cdk as cdk
from constructs import Construct

from .constants import *


class O3DECommonStack(Stack):
    """
    Create stack for deploying the shared resources among stacks
    """
    def __init__(self, scope: Construct, construct_id: str, ** kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a shared VPC with 1 public subnet group and 1 private subnet group.
        # see https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/Vpc.html 
        self._vpc = ec2.Vpc(
            self, f'{RESOURCE_ID_COMMON_PREFIX}Vpc',
            cidr='10.0.0.0/16',
            subnet_configuration=[
                {
                    'cidrMask': 24,
                    'name': 'public',
                    'subnetType': ec2.SubnetType.PUBLIC
                },
                {
                    'cidrMask': 24,
                    'name': 'private_with_nat',
                    'subnetType': ec2.SubnetType.PRIVATE_WITH_NAT
                }
            ]
        )

        # Export the subnet that will be used to launch the server Amazon EC2 instance explicitly.
        # Avoid the automatic output from the CDK to make sure that the common stack outputs won't change
        # when users choose to deploy either the server or clients separately via the target context variable
        server_subnet_selections = self._vpc.select_subnets(
            subnet_type=ec2.SubnetType.PUBLIC
        )
        if len(server_subnet_selections.subnets) == 0:
            raise RuntimeError('No public subnet is available. Please check the vpc subnet configuration')
        cdk.CfnOutput(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetId',
            description='ID of the public subnet for deploying the server instance',
            value=server_subnet_selections.subnets[0].subnet_id,
            export_name=f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetId'
        )
        cdk.CfnOutput(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetAvailabilityZone',
            description='Availability zone of the public subnet for deploying the server instance',
            value=server_subnet_selections.subnets[0].availability_zone,
            export_name=f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetAvailabilityZone'
        )
        cdk.CfnOutput(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetRouteTableId',
            description='Route table ID of the public subnet for deploying the server instance',
            value=server_subnet_selections.subnets[0].route_table.route_table_id,
            export_name=f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetRouteTableId'
        )

        # Export the subnets that will be used to launch the client Amazon ECS tasks explicitly.
        # Avoid the automatic outputs from the CDK to make sure that the common stack outputs won't change
        # when users choose to only deploy the server or clients separately via the target context variable
        client_subnets_selection = self._vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT)
        cdk.CfnOutput(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ClientSubnetIds',
            description='Private subnets for running client ECS tasks',
            value=cdk.Fn.join(
                ',', [subnet.subnet_id for subnet in client_subnets_selection.subnets]),
            export_name=f'{RESOURCE_ID_COMMON_PREFIX}ClientSubnetIds'
        )

        # Create a security group shared by the server and clients
        self._security_group = ec2.SecurityGroup(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}SecurityGroup',
            vpc=self._vpc
        )
        self._security_group.add_ingress_rule(
            self._security_group,
            ec2.Port.all_udp(),
            'Allow cross instance communication on UDP',
        )

    @property
    def vpc(self) -> ec2.Vpc:
        """
        Get the VPC shared by the server and clients
        :return: Shared VPC
        """
        return self._vpc

    @property
    def security_group(self) -> ec2.SecurityGroup:
        """
        Get the security group shared by the server and clients
        :return: Shared security group
        """
        return self._security_group
