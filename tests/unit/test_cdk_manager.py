# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import unittest
from unittest.mock import Mock, patch

from cdk_manager import CdkManager
from config import AutoScalerConfig
from constants import *

TEST_DEFAULT_CONFIG = {
    "output_path": "cdk/assets",
    "project_name": "MultiplayerSample",
    "project_path": "C:/Users/testuser/o3de-multiplayersample",
    "client_count": 5,
    "server_private_ip": "10.0.0.4",
    "server_port": SCALER_CONFIG_DEFAULT_SERVER_PORT,
    "aws_account_id": "123456789012",
    "aws_region": "us-east-1",
    "ec2_key_pair": "myKeyPair",
    "local_reference_machine_cidr": "10.0.0.1/32",
    "aws_metrics_cdk_path": "C:/Users/testuser/o3de-multiplayersample/Gem/AWS/MetricsCDK",
    "aws_metrics_policy_export_name": "MULTIPLAYERSAMPLE-AWSMetrics:UserPolicy"
}

class TestCdkManager(unittest.TestCase):

    def setUp(self):
        self._test_config = self._get_test_config()
        self._test_platform = 'test_platform'

    @patch('cdk_manager.ProcessRunner')
    def test_init(self, mock_runner):
        test_cdk_manager = CdkManager(self._test_config)

        self.assertEqual(test_cdk_manager._project_path, self._test_config.get_path("project_path"))
        self.assertEqual(test_cdk_manager._client_count, str(self._test_config.get("client_count")))
        self.assertEqual(test_cdk_manager._server_private_ip, self._test_config.get("server_private_ip"))
        self.assertEqual(test_cdk_manager._server_port, self._test_config.get("server_port"))
        self.assertEqual(test_cdk_manager._ec2_key_pair, self._test_config.get("ec2_key_pair"))
        self.assertEqual(test_cdk_manager._aws_account, self._test_config.get("aws_account_id"))
        self.assertEqual(test_cdk_manager._aws_region, self._test_config.get("aws_region"))
        self.assertEqual(test_cdk_manager._local_reference_machine_cidr, self._test_config.get("local_reference_machine_cidr"))
        self.assertEqual(test_cdk_manager._project_name, self._test_config.get("project_name"))
        self.assertEqual(test_cdk_manager._metrics_cdk_dir, self._test_config.get_path("aws_metrics_cdk_path"))
        self.assertEqual(test_cdk_manager._metrics_policy_export_name, self._test_config.get("aws_metrics_policy_export_name"))

        mock_runner.assert_called_with('Bootstrap CDK',
                ['cdk', 'bootstrap', f'aws://{self._test_config.get("aws_account_id")}/{self._test_config.get("aws_region")}'])

    @patch('cdk_manager.ProcessRunner')
    def test_init_no_metrics_project(self, mock_runner):
        no_metrics_config = self._test_config
        no_metrics_config.set('aws_metrics_cdk_path', '')
        no_metrics_config.set('aws_metrics_policy_export_name', '')
        test_cdk_manager = CdkManager(no_metrics_config)

        self.assertEqual(test_cdk_manager._project_path, self._test_config.get_path("project_path"))
        self.assertEqual(test_cdk_manager._client_count, str(self._test_config.get("client_count")))
        self.assertEqual(test_cdk_manager._server_private_ip, self._test_config.get("server_private_ip"))
        self.assertEqual(test_cdk_manager._server_port, self._test_config.get("server_port"))
        self.assertEqual(test_cdk_manager._ec2_key_pair, self._test_config.get("ec2_key_pair"))
        self.assertEqual(test_cdk_manager._aws_account, self._test_config.get("aws_account_id"))
        self.assertEqual(test_cdk_manager._aws_region, self._test_config.get("aws_region"))
        self.assertEqual(test_cdk_manager._local_reference_machine_cidr, self._test_config.get("local_reference_machine_cidr"))
        self.assertEqual(test_cdk_manager._project_name, self._test_config.get("project_name"))
        self.assertEqual(test_cdk_manager._metrics_cdk_dir, '')
        self.assertEqual(test_cdk_manager._metrics_policy_export_name, '')

        mock_runner.assert_called_with('Bootstrap CDK',
                ['cdk', 'bootstrap', f'aws://{self._test_config.get("aws_account_id")}/{self._test_config.get("aws_region")}'])

    @patch('cdk_manager.ProcessRunner')
    def test_init_ignore_metrics_policy_if_no_project(self, mock_runner):
        no_metrics_config = self._test_config
        no_metrics_config.set('aws_metrics_cdk_path', '')
        no_metrics_config.set('aws_metrics_policy_export_name', 'MULTIPLAYERSAMPLE-AWSMetrics:UserPolicy')
        test_cdk_manager = CdkManager(no_metrics_config)

        self.assertEqual(test_cdk_manager._metrics_cdk_dir, '')
        self.assertEqual(test_cdk_manager._metrics_policy_export_name, '')

        mock_runner.assert_called_with('Bootstrap CDK',
                ['cdk', 'bootstrap', f'aws://{self._test_config.get("aws_account_id")}/{self._test_config.get("aws_region")}'])


    @patch('cdk_manager.ProcessRunner')
    def test_deploy_metrics_pipeline(self, mock_runner):
        expected_args = ['cdk', 'deploy', '-c', 'batch_processing=true', '--require-approval=never']

        cdk_manager = CdkManager(self._test_config)
        cdk_manager._update_resource_mapping_config = Mock()

        cdk_manager.deploy_aws_resources(METRICS_PIPELINE_TARGET, self._test_platform)

        mock_runner.assert_called_with('Deploy CDK application', expected_args)
        assert cdk_manager._update_resource_mapping_config.called

    @patch('cdk_manager.ProcessRunner')
    def test_deploy_client(self, mock_runner):
        expected_args = ['cdk', 'deploy', '-c', f'client_count={str(self._test_config.get("client_count"))}',
                        '-c', f'target={CLIENT_TARGET}',
                        '-c', f'platform={self._test_platform}', '--all', '--require-approval=never']

        CdkManager(self._test_config).deploy_aws_resources(CLIENT_TARGET, self._test_platform)

        mock_runner.assert_called_with('Deploy CDK application', expected_args)

    @patch('cdk_manager.ProcessRunner')
    def test_deploy_server(self, mock_runner):
        expected_args = ['cdk', 'deploy', '-c', f'key_pair={self._test_config.get("ec2_key_pair")}', 
                '-c', f'server_port={self._test_config.get("server_port")}',
                '-c', f'server_private_ip={self._test_config.get("server_private_ip")}',
                '-c', f'local_reference_machine_cidr={self._test_config.get("local_reference_machine_cidr")}',
                '-c', f'metrics_policy_export_name={self._test_config.get("aws_metrics_policy_export_name")}',
                '-c', f'target={SERVER_TARGET}', '-c', f'platform={self._test_platform}', '--all', '--require-approval=never']

        CdkManager(self._test_config).deploy_aws_resources(SERVER_TARGET, self._test_platform)

        mock_runner.assert_called_with('Deploy CDK application', expected_args)

    @patch('cdk_manager.ProcessRunner')
    def test_deploy_all(self, mock_runner):
        expected_args = ['cdk', 'deploy', '-c', f'key_pair={self._test_config.get("ec2_key_pair")}',
                '-c', f'server_port={self._test_config.get("server_port")}',
                '-c', f'server_private_ip={self._test_config.get("server_private_ip")}',
                '-c', f'client_count={str(self._test_config.get("client_count"))}',
                '-c', f'local_reference_machine_cidr={self._test_config.get("local_reference_machine_cidr")}',
                '-c', f'metrics_policy_export_name={self._test_config.get("aws_metrics_policy_export_name")}',
                '-c', f'platform={self._test_platform}', '--all', '--require-approval=never']

        CdkManager(self._test_config).deploy_aws_resources(None, self._test_platform)

        mock_runner.assert_called_with('Deploy CDK application', expected_args)


    @patch('cdk_manager.ProcessRunner')
    def test_destroy_metrics_pipeline(self, mock_runner):
        expected_args = ['cdk', 'destroy', '-c', 'batch_processing=true', '--require-approval=never', '-f']

        CdkManager(self._test_config).destroy_aws_resources(METRICS_PIPELINE_TARGET, self._test_platform)

        mock_runner.assert_called_with('Destroy CDK application', expected_args)

    @patch('cdk_manager.ProcessRunner')
    def test_destroy_client(self, mock_runner):
        expected_args = ['cdk', 'destroy', '-c', f'client_count={str(self._test_config.get("client_count"))}',
                        '-c', f'target={CLIENT_TARGET}',
                        '-c', f'platform={self._test_platform}', '--all', '-f']

        CdkManager(self._test_config).destroy_aws_resources(CLIENT_TARGET, self._test_platform)

        mock_runner.assert_called_with('Destroy CDK application', expected_args)

    @patch('cdk_manager.ProcessRunner')
    def test_destroy_server(self, mock_runner):
        expected_args = ['cdk', 'destroy', '-c', f'key_pair={self._test_config.get("ec2_key_pair")}', 
                '-c', f'server_port={self._test_config.get("server_port")}',
                '-c', f'server_private_ip={self._test_config.get("server_private_ip")}',
                '-c', f'local_reference_machine_cidr={self._test_config.get("local_reference_machine_cidr")}',
                '-c', f'metrics_policy_export_name={self._test_config.get("aws_metrics_policy_export_name")}',
                '-c', f'target={SERVER_TARGET}', '-c', f'platform={self._test_platform}', '--all', '-f']

        CdkManager(self._test_config).destroy_aws_resources(SERVER_TARGET, self._test_platform)

        mock_runner.assert_called_with ('Destroy CDK application', expected_args)

    @patch('cdk_manager.ProcessRunner')
    def test_destroy_all(self, mock_runner):
        expected_args = ['cdk', 'destroy', '-c', f'key_pair={self._test_config.get("ec2_key_pair")}',
                '-c', f'server_port={self._test_config.get("server_port")}',
                '-c', f'server_private_ip={self._test_config.get("server_private_ip")}',
                '-c', f'client_count={str(self._test_config.get("client_count"))}',
                '-c', f'local_reference_machine_cidr={self._test_config.get("local_reference_machine_cidr")}',
                '-c', f'metrics_policy_export_name={self._test_config.get("aws_metrics_policy_export_name")}',
                '-c', f'platform={self._test_platform}', '--all', '-f']

        CdkManager(self._test_config).destroy_aws_resources(None, self._test_platform)

        mock_runner.assert_called_with('Destroy CDK application', expected_args)

    def _get_test_config(self) -> AutoScalerConfig:
        test_config = AutoScalerConfig()
        for k, v in TEST_DEFAULT_CONFIG.items():
            test_config.set(k, v)
        return test_config