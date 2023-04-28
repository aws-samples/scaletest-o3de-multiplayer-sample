# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import copy
import pytest

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
    'platform': 'Windows',
    'metrics_policy_export_name': 'mps-metrics-policy',
    'project_name': 'MultiplayerSample',
  }
CDK_ENV = cdk.Environment(region='us-east-1')


def test_server_stack_creation_context_variable_specified_server_resources_created():
    """
    Setup: All context variables are specified and common stack is created
    Tests: Create the server stack
    Verification: All required resources are included in the stack with proper dependencies
    """
    app = cdk.App(context=TEST_CONTEXT)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack', env=CDK_ENV)
    server_stack = O3DEServerStack(
        app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ServerStack',
        vpc=common_stack.vpc, security_group=common_stack.security_group,
        platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'],
        artifacts_bucket=common_stack.artifacts_bucket,
        env=CDK_ENV)
    template = assertions.Template.from_stack(server_stack)

    template.resource_count_is('AWS::EC2::SecurityGroupIngress', 2)
    template.has_resource_properties('AWS::EC2::SecurityGroupIngress', {
        'IpProtocol': 'tcp',
        'FromPort': RDP_CONNECTION_PORT,
        'ToPort': RDP_CONNECTION_PORT
    })

    template.has_resource_properties('AWS::EC2::SecurityGroupIngress', {
        'IpProtocol': 'udp',
        'FromPort': TEST_CONTEXT['server_port'],
        'ToPort': TEST_CONTEXT['server_port']
    })

    template.has_resource_properties('AWS::IAM::Role', {
        'AssumeRolePolicyDocument': {
            'Statement': [{
                'Action': 'sts:AssumeRole',
                'Effect': 'Allow',
                'Principal': {
                    'Service': 'ec2.amazonaws.com'
                }
            }],
        },
        'ManagedPolicyArns': [
            {
                'Fn::ImportValue': 'mps-metrics-policy'
            },
            {
                'Fn::Join': ['', ['arn:', {'Ref': 'AWS::Partition'}, ':iam::aws:policy/EC2InstanceProfileForImageBuilder']]
            },
            {
                'Fn::Join': ['', ['arn:', {'Ref': 'AWS::Partition'}, ':iam::aws:policy/AmazonSSMManagedInstanceCore']]
            }
        ],
        'Path': '/executionServiceEC2Role/'
    })

    template.has_resource_properties('AWS::IAM::InstanceProfile', {
        'Roles': [
            {
                'Ref': list(template.find_resources('AWS::IAM::Role').keys())[0]
            }
        ],
        'Path': '/executionServiceEC2Role/'
    })

    template.resource_count_is('AWS::S3::Bucket', 1)

    """
    Included policies should be:
    1. image builder log bucket policy (see below `.has_resource_properties()` check)
    2. instance role default policy, defined by CDK `grant_read()` methods
    """
    template.resource_count_is('AWS::IAM::Policy', 2)

    template.has_resource_properties('AWS::IAM::Policy', {
        'PolicyDocument': {
            'Statement': [{
                'Action': 's3:PutObject',
                'Effect': 'Allow',
                'Resource': {
                    'Fn::Sub': [
                        'arn:${AWS::Partition}:s3:::${BUCKET}/*',
                        {
                            'BUCKET': {
                                'Ref': list(template.find_resources('AWS::S3::Bucket').keys())[0]
                            }
                    }]
                }
            }]
        },
        'Roles': [{
            'Ref': list(template.find_resources('AWS::IAM::Role').keys())[0]
        }]
     })
    
    template.resource_count_is('AWS::ImageBuilder::Component', 2)
    template.has_resource_properties('AWS::ImageBuilder::Component', {
        'Name': f'{RESOURCE_ID_COMMON_PREFIX}VCRedistributableComponent',
        'Platform': 'Windows'
    })
    template.has_resource_properties('AWS::ImageBuilder::Component', {
        'Name': f'{RESOURCE_ID_COMMON_PREFIX}DownloadComponent',
        'Platform': 'Windows'
    })

    template.resource_count_is('AWS::ImageBuilder::ImageRecipe', 1)
    template.has_resource_properties('AWS::ImageBuilder::ImageRecipe', {
        'Components': [
            {
                'ComponentArn': {
                    'Ref': list(template.find_resources('AWS::ImageBuilder::Component').keys())[0],
                }
            },
            {
                'ComponentArn': {
                    'Ref': list(template.find_resources('AWS::ImageBuilder::Component').keys())[1],
                }
            },
            {
                'ComponentArn': {
                    'Fn::Sub': 'arn:${AWS::Partition}:imagebuilder:${AWS::Region}:aws:component/powershell-windows/x.x.x',
                }
            }
        ]
    })

    template.resource_count_is('AWS::ImageBuilder::InfrastructureConfiguration', 1)
    template.has_resource_properties('AWS::ImageBuilder::InfrastructureConfiguration', {
        'InstanceProfileName': {
            'Ref': list(template.find_resources('AWS::IAM::InstanceProfile').keys())[0]
        },
        'KeyPair': TEST_CONTEXT['key_pair'],
        'Logging': {
            'S3Logs': {
               'S3BucketName': {
                   'Ref': list(template.find_resources('AWS::S3::Bucket').keys())[0]
               }
            }
        },
        'TerminateInstanceOnFailure': True
    })

    template.resource_count_is('AWS::ImageBuilder::DistributionConfiguration', 1)

    template.resource_count_is('AWS::ImageBuilder::Image', 1)
    template.has_resource_properties('AWS::ImageBuilder::Image', {
        'InfrastructureConfigurationArn': {
            'Fn::GetAtt': [list(template.find_resources('AWS::ImageBuilder::InfrastructureConfiguration').keys())[0], 'Arn']
        },
        'DistributionConfigurationArn': {
            'Ref': list(template.find_resources('AWS::ImageBuilder::DistributionConfiguration').keys())[0]
        },
        'ImageRecipeArn': {
            'Ref': list(template.find_resources('AWS::ImageBuilder::ImageRecipe').keys())[0]
        }
    })

    template.resource_count_is('AWS::EC2::Instance', 1)
    user_data_capture = assertions.Capture()
    template.has_resource_properties('AWS::EC2::Instance', {
        'ImageId': {
            'Fn::GetAtt': [list(template.find_resources('AWS::ImageBuilder::Image').keys())[0], 'ImageId']
        },
        'KeyName': TEST_CONTEXT['key_pair'],
        'PrivateIpAddress': TEST_CONTEXT['server_private_ip'],
        'UserData': user_data_capture
    })
    assert len(user_data_capture.as_object().get('Fn::Base64')) > 0, 'Instance user data does not exist'

    template.has_output(f'{RESOURCE_ID_COMMON_PREFIX}ServerIp', {
        'Value': {
            'Fn::GetAtt': [list(template.find_resources('AWS::EC2::Instance').keys())[0], 'PublicIp']
        }
    })

    template.has_resource('AWS::EC2::LaunchTemplate', 1)
    template.has_resource_properties('AWS::EC2::LaunchTemplate', {
        'LaunchTemplateData': {
            'MetadataOptions': {
                'HttpTokens': 'required'
            }
        }
    })

    template.resource_count_is('AWS::SSM::Document', 1)
    template.resource_count_is('AWS::Events::Rule', 1)

def test_server_stack_creation_no_key_pair_specified_raise_runtime_error():
    """
    Setup: Context variable key_pair is not specified and common stack is created
    Tests: Create the server stack
    Verification: Runtime error is raised to ask for the EC2 key pair
    """
    local_test_context = copy.deepcopy(TEST_CONTEXT)
    local_test_context.pop('key_pair')

    app = cdk.App(context=local_test_context)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack', env=CDK_ENV)
    with pytest.raises(RuntimeError) as exc_info:
        server_stack = O3DEServerStack(
            app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ServerStack',
            vpc=common_stack.vpc, security_group=common_stack.security_group,
            platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'],
            artifacts_bucket=common_stack.artifacts_bucket,
            env=CDK_ENV)

    assert str(exc_info.value) == 'EC2 key pair is required for deploying the Multiplayer Test Scaler. ' \
                                  'Pass the key pair using \'-c key_pair={key_pair_value}\''


def test_server_stack_creation_no_server_private_ip_specified_use_default_server_private_ip():
    """
    Setup: Context server_private_ip is not specified and common stack is created
    Tests: Create the server stack
    Verification: Use the default server_private_ip value for the server instance private IP
    """
    local_test_context = copy.deepcopy(TEST_CONTEXT)
    local_test_context.pop('server_private_ip')

    app = cdk.App(context=local_test_context)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack', env=CDK_ENV)
    server_stack = O3DEServerStack(
        app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ServerStack',
        vpc=common_stack.vpc, security_group=common_stack.security_group,
        platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'],
        artifacts_bucket=common_stack.artifacts_bucket,
        env=CDK_ENV)
    template = assertions.Template.from_stack(server_stack)
    user_data_capture = assertions.Capture()
    template.has_resource_properties('AWS::EC2::Instance', {
        'ImageId': {
            'Fn::GetAtt': [list(template.find_resources('AWS::ImageBuilder::Image').keys())[0], 'ImageId']
        },
        'KeyName': TEST_CONTEXT['key_pair'],
        'PrivateIpAddress': DEFAULT_SERVER_PRIVATE_IP,
        'UserData': user_data_capture
    })


def test_server_stack_creation_no_local_reference_machine_cidr_specified_no_security_group_ingress_for_local_reference_machine_connection():
    """
    Setup: Context variable local_reference_machine_cidr is not specified and common stack is created
    Tests: Create the server stack
    Verification: No security group ingress resource is created to open the server port for the local reference machine,
        or to RDP port from local reference machine
    """
    local_test_context = copy.deepcopy(TEST_CONTEXT)
    local_test_context.pop('local_reference_machine_cidr')

    app = cdk.App(context=local_test_context)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-O3DECommonStack', env=CDK_ENV)
    server_stack = O3DEServerStack(
        app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ServerStack',
        vpc=common_stack.vpc, security_group=common_stack.security_group,
        platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'],
        artifacts_bucket=common_stack.artifacts_bucket,
        env=CDK_ENV)
    template = assertions.Template.from_stack(server_stack)

    template.resource_count_is('AWS::EC2::SecurityGroupIngress', 0)


def test_server_stack_creation_no_server_port_specified_use_default_server_port():
    """
    Setup: Context variable server_port is not specified and common stack is created
    Tests: Create the server stack
    Verification: Security group ingress resource for the local reference machine connection uses the default server port
    """
    local_test_context = copy.deepcopy(TEST_CONTEXT)
    local_test_context.pop('server_port')

    app = cdk.App(context=local_test_context)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-O3DECommonStack', env=CDK_ENV)
    server_stack = O3DEServerStack(
        app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ServerStack',
        vpc=common_stack.vpc, security_group=common_stack.security_group,
        platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'],
        artifacts_bucket=common_stack.artifacts_bucket,
        env=CDK_ENV)
    template = assertions.Template.from_stack(server_stack)

    template.has_resource_properties('AWS::EC2::SecurityGroupIngress', {
        'IpProtocol': 'udp',
        'FromPort': DEFAULT_SERVER_PORT,
        'ToPort': DEFAULT_SERVER_PORT
    })


def test_server_stack_creation_unsupported_platform_specified_raise_runtime_error():
    """
    Setup: Unsupported platform is specified and common stack is created
    Tests: Create the server stack
    Verification: Runtime error is thrown for unsupported platform
    """
    app = cdk.App(context=TEST_CONTEXT)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack', env=CDK_ENV)

    with pytest.raises(RuntimeError) as exc_info:
        server_stack = O3DEServerStack(
            app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ServerStack',
            vpc=common_stack.vpc, security_group=common_stack.security_group,
            platform='Test', project_name=TEST_CONTEXT['project_name'],
            artifacts_bucket=common_stack.artifacts_bucket,
            env=CDK_ENV)

    assert str(exc_info.value) == 'Server for the Test platform is not supported yet'
