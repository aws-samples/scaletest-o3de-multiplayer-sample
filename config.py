# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import typing

import boto3
from botocore.config import Config

import json
import pprint
from os.path import exists
from pathlib import Path

from constants import *


class BaseConfig(object):
    """
    Base config file handler
    """
    def __init__(self):
        super().__init__()

        self._filename = ''
        self._config = {}

    def has_config(self, key: str) -> bool:
        """
        Check Whether the specified key exists in the config
        :param key: Config key
        :return: Whether the key exists in the config
        """
        return key in self._config

    def set(self, key: str, value: str) -> None:
        """
        Set the value of the specified config key
        :param key: Config key
        :param value: Value for the config key
        """
        self._config[key] = value

    def get(self, key: str, default: object = None) -> any:
        """
        Get the value of the specified config key
        :param key: Config key
        :param default: Default value to return if the key doesn't exist
        :return: Value for the config key
        """
        return self._config.get(key, default)

    def get_str(self, key: str, default: str = '') -> str:
        """
        Returns the first token of the given key's value as a string. Do not use for config values which may contain spaces.
        :param key: Config key
        :param default: Default value to return if the key doesn't exist
        :return: string from the config key
        """
        return str(self._config.get(key, default)).split(' ', 1)[0]

    def get_path(self, key: str, default: str = '') -> str:
        """
        Returns the value of the specified key as a normalized path
        :param key: Config key
        :param default: Default value to return if the key doesn't exist
        :return: Path value from the config key
        """
        _path = Path(self._config.get(key, default))
        return os.path.normpath(_path)

    def load(self, filename: str, backup: bool) -> None:
        """
        Load a config file by its name. Create a new config object if not exists
        :param filename: Config file name
        :param backup: Whether to back up the config file
        """
        raise Exception("Base config load called, need to use specific load")

    def backup(self, filename: str) -> None:
        """
        Make a backup of the config file
        :param filename: Config file name
        """
        # Make a backup config filename
        p = Path(filename)
        back_filename = "{0}_{2}{1}".format(Path.joinpath(p.parent, p.stem), p.suffix, "_bak")
        self.save(back_filename)

    def save(self, filename: str) -> None:
        """
        Save the content of a config file
        :param filename: Config file name
        """
        raise Exception("Base config save called, need to use specific save")

    def default_config(self) -> dict:
        """
        Default content of the config
        :return: Content of the config in dictionary
        """
        return {}

    def display(self):
        """
        Print out the config content
        """
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self._config)


class CfgConfig(BaseConfig):
    """
    Config file handler for O3DE legacy cfg formatted files
    """

    def __init__(self):
        super().__init__()

    def load(self, filename: str, backup: bool) -> None:
        if exists(filename):
            # Read file
            with open(filename) as config_file:
                self._filename = filename
                lines = [line.rstrip() for line in config_file]
                for line in lines:
                    parts = line.split(" ", 1)
                    key = parts[0].strip()
                    value = parts[1] if len(parts) > 1 else ''
                    self._config[key] = value

            # Make backup
            if backup:
                self.backup(filename)

        else:
            print(f"[Warn] Config file {filename} not found. Generating new file")
            self.default_config()

    def save(self, filename: str) -> None:
        with open(filename, 'w') as config_file:
            for key, value in self._config.items():
                if value:
                    config_file.write("{0} {1}\n".format(key, value))
                else:
                    config_file.write(f"{key}\n")


class JsonConfig(BaseConfig):
    """
    Generic JSON Config Handler
    """

    def __init__(self):
        super().__init__()

    def load(self, filename: str, backup: bool) -> None:
        if exists(filename):
            with open(filename) as config_file:
                self._filename = filename
                self._config = json.load(config_file)
            if backup:
                self.backup(filename)
        else:
            print(f"[Warn] Config file {filename} not found. Generating new file")
            self.default_config()

    def save(self, filename: str) -> None:
        with open(filename, 'w') as config_file:
            json.dump(self._config, config_file, allow_nan=False, indent=1)


class AutoScalerConfig(JsonConfig):
    """
    Generates a multiplayer test scaler config
    """

    def __init__(self):
        super().__init__()

    def default_config(self) -> None:
        self._config = {
            # Build configurations
            # Path to the project installer build, relative to the engine root
            SCALER_CONFIG_BUILD_INSTALLER_PATH_KEY: SCALER_CONFIG_DEFAULT_BUILD_INSTALLER_PATH,
            # Whether to build the monolithic O3DE project
            SCALER_CONFIG_BUILD_MONOLITHIC_KEY: SCALER_CONFIG_DEFAULT_BUILD_MONOLITHIC_CONFIG,
            # Location of binaries built for project
            SCALER_CONFIG_BUILD_PATH_KEY: SCALER_CONFIG_DEFAULT_BUILD_PATH,
            # Type of the O3DE project configuration
            SCALER_CONFIG_BUILD_TYPE_KEY: SCALER_CONFIG_DEFAULT_BUILD_TYPE,
            # Path to the O3DE engine
            SCALER_CONFIG_ENGINE_PATH_KEY: '',
            # Path to the scaler output
            SCALER_CONFIG_OUTPUT_PATH_KEY: SCALER_CONFIG_DEFAULT_OUTPUT_PATH,
            # Path to the project cache, relative to the project root
            SCALER_CONFIG_PROJECT_CACHE_PATH_KEY: SCALER_CONFIG_DEFAULT_PROJECT_CACHE_PATH,
            # Name of the O3DE project
            SCALER_CONFIG_PROJECT_NAME_KEY: SCALER_CONFIG_DEFAULT_PROJECT_NAME,
            # Path to the O3DE project
            SCALER_CONFIG_PROJECT_PATH_KEY: '',
            # Path to the 3rd party libraries
            SCALER_CONFIG_THIRD_PARTY_PATH_KEY: SCALER_CONFIG_DEFAULT_THIRD_PARTY_PATH,

            # Project configurations
            # Number of clients to launch
            SCALER_CONFIG_CLIENT_COUNT_KEY: SCALER_CONFIG_DEFAULT_CLIENT_COUNT,
            # IP address that will be assigned to the server
            SCALER_CONFIG_SERVER_PRIVATE_IP_KEY: SCALER_CONFIG_DEFAULT_SERVER_PRIVATE_IP,
            # Port used by the server
            SCALER_CONFIG_SERVER_PORT_KEY: SCALER_CONFIG_DEFAULT_SERVER_PORT,

            # AWS configurations
            SCALER_CONFIG_AWS_ACCOUNT_ID_KEY: '',
            SCALER_CONFIG_AWS_REGION_KEY: '',
            SCALER_CONFIG_EC2_KEY_PAIR_KEY: '',
            SCALER_CONFIG_LOCAL_REFERENCE_MACHINE_CIDR_KEY: '',
            # Path to the AWSMetrics CDK application which is used to ingest and analyze server metrics
            SCALER_CONFIG_AWS_METRICS_CDK_PATH_KEY: '',
            # The AWS CloudFormation export name of the AWSMetrics CDK application user policy
            SCALER_CONFIG_AWS_METRICS_EXPORT_NAME_KEY: ''
        }


class ResourceMappingsConfig(JsonConfig):
    def __init__(self) -> None:
        super().__init__()

    def default_config(self) -> None:
        self._config = {
            'AWSResourceMappings': dict(),
            'AccountId': '',
            'Region': '',
            'Version': '1.1.0'
        }

    def populate_stack_outputs(
            self, target_name: str, stack_name: str, region: str) -> None:
        """
        Calls describe deployed AWS CloudFormation stacks and persist outputs to a resource mappings file.
        :param target_name: Name of the AWS feature gem target.
        :param stack_name: Name of the AWS CloudFormation stack deployed for the AWS feature gem target.
        :param region: Region of the resources to import.
        """
        cloudformation_client = boto3.client(
            'cloudformation',
            config=Config(region_name=region))

        response = cloudformation_client.describe_stacks(
            StackName=stack_name
        )
        stacks = response.get('Stacks', [])
        if len(stacks) == 0:
            raise RuntimeError(f'{stack_name} is invalid.')

        self._write_resource_mappings(stacks[0].get('Outputs', []), target_name, region)

    def _write_resource_mappings(self, stack_outputs: typing.List, target_name: str, region: str) -> None:
        """
        Write stack outputs to the resource mappings file.
        :param stack_outputs: The outputs of the deployed stack with which to populate the file.
        :param target_name: Name of the AWS feature gem target.
        :param region: AWS Region of the resources to import.
        """
        resource_mappings = self._config.get('AWSResourceMappings', dict())
        for output in stack_outputs:
            resource_key = f'{target_name}.{output.get("OutputKey", "InvalidKey")}'
            resource_mappings[resource_key] = resource_mappings.get(resource_key, dict())
            resource_mappings[resource_key]['Type'] = 'MultiplayerTestScalerType'
            resource_mappings[resource_key]['Name/ID'] = output.get('OutputValue', 'InvalidId')
            resource_mappings[resource_key]['Region'] = region

        self._config['AWSResourceMappings'] = resource_mappings


class ClientConfig(CfgConfig):
    """
    Generates a multiplayer client config
    """

    def __init__(self) -> None:
        super().__init__()

    def default_config(self) -> None:
        self._config = {
            'connect': ''
        }


class ServerConfig(CfgConfig):
    """
    Generates a multiplayer server config
    """

    def __init__(self):
        super().__init__()

    def default_config(self) -> None:
        self._config = {
            'host': '',
            'LoadLevel': DEFAULT_LEVEL
        }
