# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import aws_cdk as cdk
import aws_cdk.assertions as assertions

from multiplayer_test_scaler.common_stack import O3DECommonStack
from multiplayer_test_scaler.server_stack import O3DEServerStack
from multiplayer_test_scaler.constants import *

TEST_CONTEXT = {
    'asset_dir': 'assets\\Windows',
    'key_pair': 'autoscaler',
    'server_port': 33451,
    'server_private_ip': '10.0.0.5',
    'local_reference_machine_cidr': '0.0.0.1/32',
    'platform': 'Windows'
  }
CDK_ENV = cdk.Environment(region='us-east-1')


def test_common_stack_creation_context_variable_specified_common_resources_created():
    """
    Setup: All context variables are specified
    Tests: Create the common stack
    Verification: All required resources are included in the stack with proper dependencies
    """
    app = cdk.App(context=TEST_CONTEXT)
    stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack')
    template = assertions.Template.from_stack(stack)

    template.resource_count_is('AWS::EC2::VPC', 1)
    template.has_resource_properties('AWS::EC2::VPC', {
        'CidrBlock': '10.0.0.0/16'
    })

    template.resource_count_is('AWS::EC2::SecurityGroup', 1)
    template.has_resource_properties('AWS::EC2::SecurityGroup', {
        'VpcId': {
            'Ref': list(template.find_resources('AWS::EC2::VPC').keys())[0]
        }
    })

    template.resource_count_is('AWS::EC2::SecurityGroupIngress', 1)
    template.has_resource_properties('AWS::EC2::SecurityGroupIngress', {
        'IpProtocol': 'udp',
        'Description': 'Allow cross instance communication on UDP',
        'FromPort': 0,
        'ToPort': 65535,
        'GroupId': {
            'Fn::GetAtt': [list(template.find_resources('AWS::EC2::SecurityGroup').keys())[0], 'GroupId']
        },
        'SourceSecurityGroupId': {
            'Fn::GetAtt': [list(template.find_resources('AWS::EC2::SecurityGroup').keys())[0], 'GroupId']
        },
    })

    template.has_output(f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetId', {
        'Export': {
            "Name": f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetId'
           }
    })
    template.has_output(f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetAvailabilityZone', {
        'Export': {
            "Name": f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetAvailabilityZone'
           }
    })
    template.has_output(f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetRouteTableId', {
        'Export': {
            "Name": f'{RESOURCE_ID_COMMON_PREFIX}ServerSubnetRouteTableId'
           }
    })
    template.has_output(f'{RESOURCE_ID_COMMON_PREFIX}ClientSubnetIds', {
        'Export': {
            "Name": f'{RESOURCE_ID_COMMON_PREFIX}ClientSubnetIds'
           }
    })
