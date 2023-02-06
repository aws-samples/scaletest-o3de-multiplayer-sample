# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from typing import List

from config import AutoScalerConfig, ResourceMappingsConfig
from constants import *
from process_runner import ProcessRunner

DEPLOY_CMD = 'deploy'
DESTROY_CMD = 'destroy'

class CdkManager(object):
    """
    Deploy the project package to launch server and clients on AWS
    """

    def __init__(self, config: AutoScalerConfig):
        super().__init__()
        self._config = config

        scaler_root_cwd = os.getcwd()
        self._project_path = self._config.get_path(SCALER_CONFIG_PROJECT_PATH_KEY, scaler_root_cwd)
        self._asset_path = self._config.get_path(SCALER_CONFIG_OUTPUT_PATH_KEY, SCALER_CONFIG_DEFAULT_OUTPUT_PATH)
        self._asset_path = os.path.abspath(self._asset_path)
        if not os.path.exists(self._asset_path):
            assert False, f'Could not find assets in path provided {self._asset_path}. ' \
                          f'Please build and package your O3DE project before deployment'

        self._client_count = self._config.get_str(SCALER_CONFIG_CLIENT_COUNT_KEY, SCALER_CONFIG_DEFAULT_CLIENT_COUNT)
        self._server_private_ip = self._config.get_str(SCALER_CONFIG_SERVER_PRIVATE_IP_KEY,
                                                       SCALER_CONFIG_DEFAULT_SERVER_PRIVATE_IP)
        self._server_port = self._config.get_str(SCALER_CONFIG_SERVER_PORT_KEY, SCALER_CONFIG_DEFAULT_SERVER_PORT)

        self._ec2_key_pair = self._config.get_str(SCALER_CONFIG_EC2_KEY_PAIR_KEY, '')
        self._aws_account = self._config.get_str(SCALER_CONFIG_AWS_ACCOUNT_ID_KEY, os.environ.get('CDK_DEFAULT_ACCOUNT'))
        self._aws_region = self._config.get_str(SCALER_CONFIG_AWS_REGION_KEY, os.environ.get('CDK_DEFAULT_REGION'))
        if not self._aws_account or not self._aws_region:
            assert False, 'No AWS account or region is provided. Update the multiplayer test scaler config file or ' \
                          'Set up the CDK environment variables CDK_DEFAULT_ACCOUNT and CDK_DEFAULT_REGION. ' \
                          'Check https://docs.aws.amazon.com/cdk/v2/guide/environments.html for more details'

        self._local_reference_machine_cidr = self._config.get_str(SCALER_CONFIG_LOCAL_REFERENCE_MACHINE_CIDR_KEY, '')
        if not self._local_reference_machine_cidr:
            print("[Warn] No local machine CIDR group is specified. No server port or RDP ingress rules will be created")
        self._project_name = self._config.get_str(SCALER_CONFIG_PROJECT_NAME_KEY, SCALER_CONFIG_DEFAULT_PROJECT_NAME)
        self._env = dict(os.environ, **{
            'O3DE_AWS_DEPLOY_REGION':  self._aws_region,
            'O3DE_AWS_DEPLOY_ACCOUNT': self._aws_account,
            'O3DE_AWS_PROJECT_NAME': self._project_name
        })
        self._validate_metrics_project_settings(
            self._config.get_str(SCALER_CONFIG_AWS_METRICS_CDK_PATH_KEY),
            self._config.get_str(SCALER_CONFIG_AWS_METRICS_EXPORT_NAME_KEY)
        )
        main_script_dir = os.path.abspath(os.path.dirname(__file__))
        self._scaler_cdk_dir = os.path.join(str(main_script_dir), 'cdk')

        self._bootstrap()

    def _validate_metrics_project_settings(self, metrics_project_dir: str, metrics_policy: str) -> None:
        """
        Validate provided metrics project settings 
        """
        if not metrics_project_dir:
            print("No 'aws_metrics_cdk_path' provided, proceeding without deploying a metrics project." )
            if metrics_policy != "":
                print("[Warn] Ignoring 'aws_metrics_policy_export_name' because no 'aws_metrics_cdk_path' provided.")
            
            self._metrics_cdk_dir = ""
            self._metrics_policy_export_name = ""
            return

        elif metrics_project_dir and not metrics_policy:
            raise RuntimeError('No AWS Metrics user policy is specified. '
                               'Server instance will be unable to submit metrics to the AWS backend')
        
        self._metrics_cdk_dir = os.path.normpath(metrics_project_dir)
        self._metrics_policy_export_name = metrics_policy
        

    def _bootstrap(self) -> None:
        """
        Bootstrap AWS CDK
        """
        cmd_list = ['cdk', 'bootstrap', f'aws://{self._aws_account}/{self._aws_region}']
        process = ProcessRunner('Bootstrap CDK', cmd_list)
        process.run(env=self._env)

    def deploy_aws_resources(self, target: str, platform: str) -> None:
        """
        Deploy the AWS CDK application
        :param target: Target to deploy
        :param platform: Platform of the project package
        """
        cdk_dir = self._metrics_cdk_dir if target == METRICS_PIPELINE_TARGET else self._scaler_cdk_dir
        self._install_dependencies(cdk_dir)

        if target == METRICS_PIPELINE_TARGET:
            cdk_deploy_cmd_args = ['cdk', DEPLOY_CMD, '-c', 'batch_processing=true', '--require-approval=never']
        elif target == CLIENT_TARGET:
            cdk_deploy_cmd_args = self._get_client_cdk_cmd_args(DEPLOY_CMD, target, platform)
        elif target == SERVER_TARGET:
            cdk_deploy_cmd_args = self._get_server_cdk_cmd_args(DEPLOY_CMD, target, platform)
        else:
            cdk_deploy_cmd_args = self._get_all_cdk_command_args(DEPLOY_CMD, platform)

        process = ProcessRunner('Deploy CDK application', cdk_deploy_cmd_args)
        process.run(cdk_dir, env=self._env)

        if target == METRICS_PIPELINE_TARGET:
            # Import the AWSMetrics stack outputs to the resource mappings file.
            # Server metrics will be sent to the AWS backend automatically via the AWSMetrics gem.
            self._update_resource_mapping_config(target)

    def destroy_aws_resources(self, target: str, platform: str) -> None:
        """
        Destroy the AWS CDK application
        :param target: Target to destroy
        :param platform: Platform of the project package
        """
        cdk_dir = self._metrics_cdk_dir if target == METRICS_PIPELINE_TARGET else self._scaler_cdk_dir
        self._install_dependencies(cdk_dir)

        if target == METRICS_PIPELINE_TARGET:
            cdk_destroy_cmd_args = ['cdk', DESTROY_CMD, '-c', 'batch_processing=true', '--require-approval=never', '-f']
        elif target == CLIENT_TARGET:
            cdk_destroy_cmd_args = self._get_client_cdk_cmd_args(DESTROY_CMD, target, platform)
        elif target == SERVER_TARGET:
            cdk_destroy_cmd_args = self._get_server_cdk_cmd_args(DESTROY_CMD, target, platform)
        else:
            cdk_destroy_cmd_args = self._get_all_cdk_command_args(DESTROY_CMD, platform)

        process = ProcessRunner('Destroy CDK application', cdk_destroy_cmd_args)
        process.run(cdk_dir, env=self._env)

    def has_metrics_project(self) -> bool:
        """
        Whether or not an AWS Metrics project is in use
        """
        return self._metrics_cdk_dir != ""

    def _install_dependencies(self, cdk_dir: str) -> None:
        """
        Install dependencies of the AWS CDK application
        :param cdk_dir: The AWS CDK application directory
        """
        install_dependencies_cmd_list = ['pip', 'install', '-r', 'requirements.txt']
        process = ProcessRunner('Install required dependencies', install_dependencies_cmd_list)
        process.run(cdk_dir)

    def _update_resource_mapping_config(self, aws_feature_gem: str = 'AWSMetrics') -> None:
        """
        Update the resource mapping config file and import all the AWS feature stack outputs
        :param aws_feature_gem: Name of the AWS feature gem
        """
        resource_mappings_config_file = os.path.join(self._project_path, 'Config',
                                                     RESOURCE_MAPPINGS_CONFIG_FILENAME)
        resource_mappings_config = ResourceMappingsConfig()
        resource_mappings_config.load(filename=resource_mappings_config_file, backup=True)
        resource_mappings_config.set('AccountId', self._aws_account)
        resource_mappings_config.set('Region', self._aws_region)

        stack_name = f'{self._project_name.upper()}-{aws_feature_gem}-{self._aws_region}'
        resource_mappings_config.populate_stack_outputs(
            aws_feature_gem, stack_name, self._aws_region)

        resource_mappings_config.display()
        resource_mappings_config.save(resource_mappings_config_file)

    def _get_client_cdk_cmd_args(self, cdk_cmd: str, target: str, platform: str) -> List[str]:
        client_cmd_args = ['cdk', cdk_cmd, '-c', f'client_count={self._client_count}', 
                '-c', f'target={target}',
                '-c', f'platform={platform}', '--all']
        final_arg = '--require-approval=never' if (cdk_cmd == DEPLOY_CMD) else '-f'
        client_cmd_args.append(final_arg)
        return client_cmd_args

    def _get_server_cdk_cmd_args(self, cdk_cmd: str, target: str, platform: str) -> List[str]:
        server_cmd_args = ['cdk', cdk_cmd, '-c', f'key_pair={self._ec2_key_pair}', 
                '-c', f'server_port={self._server_port}',
                '-c', f'server_private_ip={self._server_private_ip}',
                '-c', f'local_reference_machine_cidr={self._local_reference_machine_cidr}',
                '-c', f'metrics_policy_export_name={self._metrics_policy_export_name}',
                '-c', f'target={target}', '-c', f'platform={platform}', '--all']

        final_arg = '--require-approval=never' if (cdk_cmd == DEPLOY_CMD) else '-f'
        server_cmd_args.append(final_arg)
        return server_cmd_args

    def _get_all_cdk_command_args(self, cdk_cmd: str, platform: str) -> List[str]:
        cmd_args = ['cdk', cdk_cmd, '-c', f'key_pair={self._ec2_key_pair}',
                '-c', f'server_port={self._server_port}',
                '-c', f'server_private_ip={self._server_private_ip}',
                '-c', f'client_count={self._client_count}',
                '-c', f'local_reference_machine_cidr={self._local_reference_machine_cidr}',
                '-c', f'metrics_policy_export_name={self._metrics_policy_export_name}',
                '-c', f'platform={platform}', '--all']

        final_arg = '--require-approval=never' if (cdk_cmd == DEPLOY_CMD) else '-f'
        cmd_args.append(final_arg)
        return cmd_args