# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import pytest
import copy

import aws_cdk as cdk
import aws_cdk.assertions as assertions

from multiplayer_test_scaler.common_stack import O3DECommonStack
from multiplayer_test_scaler.client_stack import O3DEClientScalerStack
from multiplayer_test_scaler.constants import *

TEST_CONTEXT = {
    'asset_dir': 'assets\\Windows',
    'server_port': 33451,
    'client_count': 1,
    'local_reference_machine_cidr': '0.0.0.1/32',
    'platform': 'Windows',
    'project_name': 'MultiplayerSample',
  }


def test_client_stack_creation_context_variable_specified_client_resources_created():
    """
    Setup: All context variables are specified and common stack is created
    Tests: Create the client stack
    Verification: All required resources are included in the stack with proper dependencies
    """
    app = cdk.App(context=TEST_CONTEXT)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack')

    stack = O3DEClientScalerStack(
        app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ClientStack',
        vpc=common_stack.vpc, security_group=common_stack.security_group,
        platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'])
    template = assertions.Template.from_stack(stack)

    template.resource_count_is('AWS::ECS::Cluster', 1)

    template.resource_count_is('AWS::ECS::TaskDefinition', 1)
    template.has_resource_properties('AWS::ECS::TaskDefinition', {
        'ContainerDefinitions': assertions.Match.array_equals([
            assertions.Match.object_like(
                {
                    'Command': assertions.Match.array_equals([ECS_TASK_COMMAND.replace('{project_name}', TEST_CONTEXT['project_name'])]),
                    'EntryPoint': assertions.Match.array_equals(['powershell.exe']),
                    'LogConfiguration': assertions.Match.object_like({
                        'LogDriver': 'awslogs',
                        'Options': assertions.Match.object_like({
                            'awslogs-stream-prefix': ECS_TASK_LOGGING_STREAM_PREFIX
                        })
                    }),
                }
            )
        ]),
        'Cpu': str(ECS_TASK_CPU_UNITS),
        'Memory': str(ECS_TASK_MEMORY_LIMIT_MIB),
        'RequiresCompatibilities': assertions.Match.array_equals(['FARGATE']),
        'RuntimePlatform': assertions.Match.object_equals({
            'CpuArchitecture': 'X86_64',
            'OperatingSystemFamily': 'WINDOWS_SERVER_2019_CORE'
        })
    })

    template.resource_count_is('AWS::ECS::Service', 1)
    template.has_resource_properties('AWS::ECS::Service', assertions.Match.object_like({
        'Cluster': {
            'Ref': list(template.find_resources('AWS::ECS::Cluster').keys())[0]
        },
        'DesiredCount': TEST_CONTEXT['client_count'],
        'LaunchType': 'FARGATE',
        'TaskDefinition': {
            'Ref': list(template.find_resources('AWS::ECS::TaskDefinition').keys())[0]
        }
    }))


def test_client_stack_creation_client_count_not_specified_raise_runtime_error():
    """
    Setup: Context Variable client_count is not specified and common stack is created
    Tests: Create the client stack
    Verification: Runtime error is raised to ask for the client count
    """
    local_test_context = copy.deepcopy(TEST_CONTEXT)
    local_test_context.pop('client_count')

    app = cdk.App(context=local_test_context)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack')

    with pytest.raises(RuntimeError) as exc_info:
        stack = O3DEClientScalerStack(
            app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ClientStack',
            vpc=common_stack.vpc, security_group=common_stack.security_group,
            platform=TEST_CONTEXT['platform'], project_name=TEST_CONTEXT['project_name'])

    assert str(exc_info.value) == 'Client count is required for deploying the Multiplayer Test Scaler. ' \
                                  'Pass the client count using \'-c client_count={client_count}\''


def test_client_stack_creation_unsupported_platform_specified_raise_runtime_error():
    """
    Setup: Unsupported platform is specified and common stack is created
    Tests: Create the client stack
    Verification: Runtime error is thrown for unsupported platform
    """
    app = cdk.App(context=TEST_CONTEXT)
    common_stack = O3DECommonStack(app, f'{RESOURCE_ID_COMMON_PREFIX}Test-CommonStack')

    with pytest.raises(RuntimeError) as exc_info:
        stack = O3DEClientScalerStack(
            app, f'{RESOURCE_ID_COMMON_PREFIX}Test-ClientStack',
            vpc=common_stack.vpc, security_group=common_stack.security_group,
            platform='Test', project_name=TEST_CONTEXT['project_name'])

    assert str(exc_info.value) == 'Client for the Test platform is not supported yet'
