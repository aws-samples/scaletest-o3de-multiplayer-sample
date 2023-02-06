# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

# Config file names
SCALER_CONFIG_FILENAME = 'multiplayer_test_scaler_config.json'
CLIENT_CONFIG_FILENAME = 'launch_client.cfg'
SERVER_CONFIG_FILENAME = 'launch_server.cfg'
RESOURCE_MAPPINGS_CONFIG_FILENAME = 'default_aws_resource_mappings.json'

# Scaler config file keys
SCALER_CONFIG_BUILD_INSTALLER_PATH_KEY = 'build_installer_path'
SCALER_CONFIG_BUILD_MONOLITHIC_KEY = 'build_monolithic'
SCALER_CONFIG_BUILD_PATH_KEY = 'build_path'
SCALER_CONFIG_BUILD_TYPE_KEY = 'build_type'

SCALER_CONFIG_ENGINE_PATH_KEY = 'engine_path'
SCALER_CONFIG_OUTPUT_PATH_KEY = 'output_path'
SCALER_CONFIG_PROJECT_CACHE_PATH_KEY = 'project_cache_path'
SCALER_CONFIG_PROJECT_NAME_KEY = 'project_name'
SCALER_CONFIG_PROJECT_PATH_KEY = 'project_path'
SCALER_CONFIG_THIRD_PARTY_PATH_KEY = 'third_party_path'

SCALER_CONFIG_CLIENT_COUNT_KEY = 'client_count'
SCALER_CONFIG_SERVER_PORT_KEY = 'server_port'
SCALER_CONFIG_SERVER_PRIVATE_IP_KEY = 'server_private_ip'

SCALER_CONFIG_AWS_ACCOUNT_ID_KEY = 'aws_account_id'
SCALER_CONFIG_AWS_REGION_KEY = 'aws_region'
SCALER_CONFIG_EC2_KEY_PAIR_KEY = 'ec2_key_pair'
SCALER_CONFIG_LOCAL_REFERENCE_MACHINE_CIDR_KEY = 'local_reference_machine_cidr'
SCALER_CONFIG_AWS_METRICS_CDK_PATH_KEY = 'aws_metrics_cdk_path'
SCALER_CONFIG_AWS_METRICS_EXPORT_NAME_KEY = 'aws_metrics_policy_export_name'

# Scaler config default values
SCALER_CONFIG_DEFAULT_BUILD_INSTALLER_PATH = os.path.join('install', 'bin')
SCALER_CONFIG_DEFAULT_BUILD_MONOLITHIC_CONFIG = False
SCALER_CONFIG_DEFAULT_BUILD_PATH = 'build'
SCALER_CONFIG_DEFAULT_BUILD_TYPE = 'release'

SCALER_CONFIG_DEFAULT_OUTPUT_PATH = os.path.join('cdk', 'assets')

SCALER_CONFIG_DEFAULT_PROJECT_CACHE_PATH = 'Cache'
SCALER_CONFIG_DEFAULT_PROJECT_NAME = 'MultiplayerSample'
SCALER_CONFIG_DEFAULT_THIRD_PARTY_PATH = '%LY_3RDPARTY_PATH%'

SCALER_CONFIG_DEFAULT_CLIENT_COUNT = 1
SCALER_CONFIG_DEFAULT_SERVER_PRIVATE_IP = '10.0.0.4'
SCALER_CONFIG_DEFAULT_SERVER_PORT = '33450'

# Platform specific constants
PLATFORM_WINDOWS = 'Windows'
WINDOWS_GENERATOR = 'Visual Studio 16'
WINDOWS_CACHE_SUBFOLDER_NAME = 'pc'

# Level to spawn when loading
DEFAULT_LEVEL = 'Levels/SampleBase/SampleBase.spawnable'

# Scaler output configurations
OUTPUT_PACKAGE_FOLDER_NAME = 'project'

# Deployment targets
METRICS_PIPELINE_TARGET = 'AWSMetrics'
CLIENT_TARGET = 'client'
SERVER_TARGET = 'server'
ALL_TARGET = 'all'

