#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

import aws_cdk as cdk

from multiplayer_test_scaler.multiplayer_test_scaler_construct import MultiplayerTestScalerConstruct

"""Configuration"""
REGION = os.environ.get('O3DE_AWS_DEPLOY_REGION', os.environ['CDK_DEFAULT_REGION'])
ACCOUNT = os.environ.get('O3DE_AWS_DEPLOY_ACCOUNT', os.environ['CDK_DEFAULT_ACCOUNT'])

PROJECT_NAME = os.environ.get('O3DE_AWS_PROJECT_NAME', 'MULTIPLAYER-TEST-SCALER')

# Set-up regions to deploy stack to, or use default if not set
env = cdk.Environment(
    account=ACCOUNT,
    region=REGION)

"""End of Configuration"""

app = cdk.App()
multiplayer_test_scaler_construct = MultiplayerTestScalerConstruct(
    app,
    PROJECT_NAME,
    env=env
)

app.synth()
