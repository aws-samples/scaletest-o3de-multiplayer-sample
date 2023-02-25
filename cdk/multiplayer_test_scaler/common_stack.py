# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
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

        # Create bucket where test artifacts should be uploaded
        # to retain this on stack destroy, change properties:
        # removal_policy=RemovalPolicy.RETAIN, auto_delete_objects=False
        self._artifacts_bucket = s3.Bucket(self, 'ArtifactsBucket',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True)
        cdk.CfnOutput(
            self,
            f'{RESOURCE_ID_COMMON_PREFIX}ArtifactBucketName',
            description="Bucket where test artifacts will be uploaded",
            value=self._artifacts_bucket.bucket_name,
            export_name=f'{RESOURCE_ID_COMMON_PREFIX}ArtifactBucketName')
        
        # Create lambda to upload artifacts to external bucket when test ends
        self._create_upload_lambda()
        
    def _create_upload_lambda(self):
        destination_bucket_name = cdk.Fn.import_value(DEFAULT_DESTINATION_BUCKET_EXPORT_NAME)
        destination_pattern = cdk.Fn.sub('arn:${AWS::Partition}:s3:::') + destination_bucket_name + '/*'
        upload_policy = iam.Policy(self, 'UploadLambdaPolicy', 
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['cloudformation:ListExports'],
                        resources=['*'] # ListExports does not support resource or condition keys
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['s3:PutObject'],
                        resources=[destination_pattern],
                    )
                ]
            )
        )

        self._upload_lambda = _lambda.Function(self, f'{RESOURCE_ID_COMMON_PREFIX}ArtifactUploadLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/upload_test_artifacts'),
            handler='upload_test_artifacts.handler',
            timeout=Duration.seconds(240),
            description='Uploads MP Scaler artifacts to external bucket when child stacks are torn down.',
        )
        self._upload_lambda.role.attach_inline_policy(upload_policy)
        self._artifacts_bucket.grant_read(self._upload_lambda.role)

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

    @property
    def artifacts_bucket(self) -> s3.Bucket:
        """
        Get the S3 bucket where test artifacts should be stored
        """
        return self._artifacts_bucket
    
    @property
    def upload_lambda(self) -> _lambda.Function:
        """
        Get the lambda function used to upload test artifacts.
        Intended to be used as a target to trigger on child stack destruction.
        """
        return self._upload_lambda