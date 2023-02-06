# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import aws_cdk as cdk
from constructs import Construct

from .client_stack import O3DEClientScalerStack
from .common_stack import O3DECommonStack
from .constants import PLATFORM_WINDOWS
from .server_stack import O3DEServerStack


class MultiplayerTestScalerConstruct(Construct):
    """
    Orchestrates setting up the Auto Scaler Stacks
    """

    def __init__(
            self,
            scope: Construct,
            id_: str,
            env: cdk.Environment) -> None:
        super().__init__(scope, id_)

        # Create the common stack for deploying shared resources like VPC and security group
        common_stack = O3DECommonStack(
            scope,
            f'{id_}-CommonStack',
            stack_name=f'{id_}-CommonStack',
            env=env
        )

        platform = self.node.try_get_context('platform')
        if not platform:
            platform = PLATFORM_WINDOWS
            print(f'No deployment platform is specified. Use default platform {PLATFORM_WINDOWS}')

        target = self.node.try_get_context('target')
        if not target or target == 'server':
            # No target or the server target is specified. Deploy the server stack
            server_stack = O3DEServerStack(
                scope,
                f'{id_}-ServerStack',
                stack_name=f'{id_}-ServerStack',
                vpc=common_stack.vpc,
                security_group=common_stack.security_group,
                platform=platform,
                project_name=id_,
                env=env
            )

        if not target or target == 'client':
            # No target or the client target is specified. Deploy the client stack
            client_stack = O3DEClientScalerStack(
                scope,
                f'{id_}-ClientStack',
                stack_name=f'{id_}-ClientStack',
                vpc=common_stack.vpc,
                security_group=common_stack.security_group,
                platform=platform,
                project_name=id_,
                env=env
            )

        if not target:
            # No target is specified. Both client and server stacks will be deployed, so
            # ensure that the client stack is deployed after the server stack.
            client_stack.node.add_dependency(server_stack)
