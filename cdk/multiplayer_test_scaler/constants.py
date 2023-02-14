# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2
)

PLATFORM_WINDOWS = 'Windows'
ASSET_DIR_ROOT = 'assets'
ZIPPED_PACKAGE_NAME = 'project.zip'

RESOURCE_ID_COMMON_PREFIX = 'MultiplayerTestScaler'

DEFAULT_SERVER_PORT = 33450
RDP_CONNECTION_PORT = 3389
# In this AWS CDK application, the public subnet used to deploy the server instance has IPv4 CIDR 10.0.0.0/24.
# Make sure the server private IP address falls within the subnet CIDR.
# The same IP address should also be configured in the project launch_client.cfg file.
DEFAULT_SERVER_PRIVATE_IP = '10.0.0.4'
SERVER_LAUNCH_SCRIPT = '<script>\n' \
                       '@echo off\n' \
                       'netsh advfirewall firewall add rule name="O3DE_server" dir=in protocol=UDP localport={server_port} action=allow program="C:\o3de\{project_name}.ServerLauncher.exe" enable=yes\n' \
                       'cd C:/o3de\n' \
                       '{project_name}.ServerLauncher --engine-path=C:\o3de --project-path=C:\o3de --project-cache-path=C:\o3de\Cache ' \
                       '--regset="/Amazon/AWSCore/AllowAWSMetadataCredentials=true" ' \
                       '--console-command-file=C:/o3de/Cache/pc/launch_server.cfg --rhi=null -NullRenderer -bg_ConnectToAssetProcessor=0 \n' \
                       '</script>'
SERVER_INSTANCE_CLASS = ec2.InstanceClass.COMPUTE5
SERVER_INSTANCE_SIZE = ec2.InstanceSize.XLARGE2
SERVER_INSTANCE_VOLUME_SIZE = 50

# Defines the command to run on start up of the client Amazon ECS task:
# 1. Launch the client
# 2. Wait for it to be ready
# 3. Log the generated client log output
ECS_TASK_COMMAND = 'cd \'c:\\project\'; ' \
                   'pwd; ' \
                   './{project_name}.GameLauncher.exe --console-command-file=launch_client.cfg -bg_ConnectToAssetProcessor=0; ' \
                   'start-sleep -seconds 15; ' \
                   'get-content -path user/log/Game.log -Wait'
ECS_TASK_CPU_ARCHITECTURE = ecs.CpuArchitecture.X86_64
ECS_TASK_CPU_UNITS = 1024
ECS_TASK_LOGGING_STREAM_PREFIX = 'auto-scaler-client'
ECS_TASK_MEMORY_LIMIT_MIB = 8192
ECS_TASK_OPERATING_SYSTEM_FAMILY_MAP = {
    PLATFORM_WINDOWS: ecs.OperatingSystemFamily.WINDOWS_SERVER_2019_CORE
}