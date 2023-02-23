# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import argparse

from config import AutoScalerConfig
from constants import *
from package_builder import PackageBuilder
from cdk_manager import CdkManager


def _create_auto_scaler_config(args):
    config = AutoScalerConfig()
    config.load(filename=args.config_file, backup=True)
    config.display()
    config.save(args.config_file)
    return config


def build(config: AutoScalerConfig, args: argparse.Namespace) -> None:
    """
    Build the multiplayer project package
    :param config: Auto scaler config
    :param args: CLI input arguments
    """
    cdk_manager = CdkManager(config)
    if cdk_manager.has_metrics_project():
        # Deploy the AWSMetrics CDK application and import the resources to
        # the resource mapping file before building the project.
        # See the AWS metrics gem setup at https://www.o3de.org/docs/user-guide/gems/reference/aws/aws-metrics/setup/
        cdk_manager.deploy_aws_resources(METRICS_PIPELINE_TARGET, args.platform)

    PackageBuilder(config, args.platform) \
        .configure_project() \
        .process_assets() \
        .build_project('INSTALL') \
        .process_output()


def deploy(config: AutoScalerConfig, args: argparse.Namespace) -> None:
    """
    Deploy multiplayer test scaler AWS resources
    :param config: Auto scaler config
    :param args: CLI input arguments
    """
    CdkManager(config).deploy_aws_resources(args.target, args.platform)


def clear(config: AutoScalerConfig, args: argparse.Namespace) -> None:
    """
    Clear multiplayer test scaler AWS resources
    :param config: Auto scaler config
    :param args: CLI input arguments
    """
    cdk_manager = CdkManager(config)
    cdk_manager.destroy_aws_resources(args.target, args.platform)

    if args.target == 'all' and cdk_manager.has_metrics_project():
        # Destroy the AWSMetrics CDK application as well for cleaning up all the deployed resources
        cdk_manager.destroy_aws_resources(METRICS_PIPELINE_TARGET, args.platform)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='main.py',
        description=(
            'Runs the setup of an O3DE multiplayer project deployment'
        ),
        add_help=False
    )
    parser.add_argument(
        '-f', '--config-file', action='store', default=SCALER_CONFIG_FILENAME,
        help='Path to the multiplayer project config file. Creates a new config file if none exists'
    )
    # Capitalizing the platform argument to satisfy the sentence case requirements of EC2 Image Builder
    parser.add_argument(
        '-p', '--platform', choices=[PLATFORM_WINDOWS], action='store', default=PLATFORM_WINDOWS, type=str.capitalize,
        help='Platform of the project package'
    )

    subparsers = parser.add_subparsers(metavar='COMMAND')
    parser_build = subparsers.add_parser('build', parents=[parser], help='Build the multiplayer project package')
    parser_build.set_defaults(func=build)

    parser_deploy = subparsers.add_parser('deploy', parents=[parser], help='Deploy multiplayer project AWS resources')
    parser_deploy.set_defaults(func=deploy)
    parser_deploy.add_argument(
        '-t', '--target', choices=[SERVER_TARGET, CLIENT_TARGET, ALL_TARGET, METRICS_PIPELINE_TARGET],
        action='store', default=ALL_TARGET,
        help='Target(s) to deploy. The server and client targets will be deployed if no target is specified. '
             'Note that the AWSMetrics target is required to be deployed before the build'
    )

    parser_clear = subparsers.add_parser('clear', parents=[parser], help='Clear deployed AWS resources')
    parser_clear.set_defaults(func=clear)
    parser_clear.add_argument(
        '-t', '--target', choices=[SERVER_TARGET, CLIENT_TARGET, ALL_TARGET, METRICS_PIPELINE_TARGET],
        action='store', default=ALL_TARGET,
        help='Target(s) to clear. All the AWS resources will be cleared if no target is specified'
    )

    args = parser.parse_args()
    config = _create_auto_scaler_config(args)
    if hasattr(args, 'func'):
        args.func(config, args)
