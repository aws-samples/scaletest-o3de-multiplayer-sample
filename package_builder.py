# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from __future__ import annotations
import os
import shutil
from typing import List

from constants import *
from config import AutoScalerConfig, ClientConfig, ServerConfig
from process_runner import ProcessRunner


class PackageBuilder(object):
    """
    Build and package the multiplayer project
    """
    def __init__(self, config: AutoScalerConfig, platform: str) -> None:
        super().__init__()
        self._config = config
        self._platform = platform

        # this tool root
        scaler_root_cwd = os.getcwd()
        # what's in "project_path"
        self._project_path = str(self._config.get(SCALER_CONFIG_PROJECT_PATH_KEY, scaler_root_cwd))
        self._engine_path = str(self._config.get(SCALER_CONFIG_ENGINE_PATH_KEY, scaler_root_cwd))
        self._third_party_path = str(self._config.get(SCALER_CONFIG_THIRD_PARTY_PATH_KEY,
                                                      SCALER_CONFIG_DEFAULT_THIRD_PARTY_PATH))
        self._project_cache_path = self._get_project_cache_path()
        self._project_name = str(self._config.get(SCALER_CONFIG_PROJECT_NAME_KEY, SCALER_CONFIG_DEFAULT_PROJECT_NAME))
        self._build_type = str(self._config.get(SCALER_CONFIG_BUILD_TYPE_KEY, SCALER_CONFIG_DEFAULT_BUILD_TYPE))
        self._monolithic = bool(self._config.get(SCALER_CONFIG_BUILD_MONOLITHIC_KEY, False))
        self._build_path = os.path.join(
            str(self._config.get(SCALER_CONFIG_BUILD_PATH_KEY, SCALER_CONFIG_DEFAULT_BUILD_PATH)), self._platform)
        self._output_path = os.path.join(
            str(self._config.get(SCALER_CONFIG_OUTPUT_PATH_KEY, SCALER_CONFIG_DEFAULT_OUTPUT_PATH)), self._platform)
        self._server_private_ip = str(self._config.get(SCALER_CONFIG_SERVER_PRIVATE_IP_KEY,
                                                       SCALER_CONFIG_DEFAULT_SERVER_PRIVATE_IP))
        installer_path = str(self._config.get(SCALER_CONFIG_DEFAULT_BUILD_INSTALLER_PATH,
                                              SCALER_CONFIG_DEFAULT_BUILD_INSTALLER_PATH))
        self._installer_build_path = os.path.join(self._project_path, installer_path, self._platform, self._build_type)
        if self._monolithic:
            self._installer_build_path = os.path.join(self._installer_build_path, 'Monolithic')
        else:
            self._installer_build_path = os.path.join(self._installer_build_path, 'Default')

    def configure_project(self, custom_cmake_args: List[str] = []) -> PackageBuilder:
        """
        Configure the multiplayer project for build
        :param custom_cmake_args: Custom cmake arguments for configuring the project
        :return: The builder itself
        """
        self._create_project_config_files()

        project_config_cmd_args = ['cmake', '-S', '.', '-B', self._build_path, '-G', f'"{self._get_generator()}"',
                                f'-DLY_3RDPARTY_PATH={self._third_party_path}', f'-DLY_MONOLITHIC_GAME={self._monolithic}']
        project_config_cmd_args.extend(custom_cmake_args)
        process = ProcessRunner('Configure project', project_config_cmd_args)
        process.run(self._project_path)

        return self

    def _create_project_config_files(self) -> None:
        """
        Create launch_server.cfg and launch_client.cfg files
        """
        print('Creating launch_server.cfg and launch_client.cfg...')
        server_file = os.path.join(self._project_path, SERVER_CONFIG_FILENAME)
        server_config = ServerConfig()
        server_config.load(filename=server_file, backup=True)
        server_config.display()
        server_config.save(server_file)

        client_file = os.path.join(self._project_path, CLIENT_CONFIG_FILENAME)
        client_config = ClientConfig()
        client_config.load(filename=client_file, backup=True)
        client_config.set('connect', self._server_private_ip)
        client_config.display()
        client_config.save(client_file)
        print('...Done')

    def process_assets(self) -> PackageBuilder:
        """
        Process the project assets
        :return: The builder itself
        """
        # Build asset target and process assets
        asset_cmd_args = ['cmake', '--build', self._build_path, '--target', f'{self._project_name}.Assets', '--config',  self._build_type]
        process = ProcessRunner('Converting assets', asset_cmd_args)
        process.run(self._project_path)

        return self

    def build_project(self, target: str, custom_cmake_args: List[str] = []) -> PackageBuilder:
        """
        Build the multiplayer project
        :param target: Build target
        :param custom_cmake_args: Custom cmake arguments for building the project
        :return: The builder itself
        """
        build_path = os.path.join(self._project_path, self._build_path)
        project_build_cmd_args = ['cmake', '--build', build_path, '--target', target, '--config', self._build_type]
        project_build_cmd_args.extend(custom_cmake_args)
        process = ProcessRunner('Build project', project_build_cmd_args)
        process.run(self._project_path)

        return self

    def process_output(self) -> None:
        """
        Package the multiplayer project for deployment
        """
        if self._build_type != 'release':
            # This extra step is only required for non-release build since
            # assets will be copied to the installer directory automatically for release build.
            print('Copying assets to the installer directory...')
            source_cache_path = os.path.join(self._project_path, self._project_cache_path)
            target_cache_path = os.path.join(self._installer_build_path, self._project_cache_path)
            if os.path.exists(target_cache_path):
                shutil.rmtree(target_cache_path)
            shutil.copytree(source_cache_path, target_cache_path)
            print('...Done')

        # Copy the project package and config files to the output directory
        print(f'Copying the project package to the output directory {self._output_path} ...')
        project_package_path = os.path.join(self._output_path, OUTPUT_PACKAGE_FOLDER_NAME)
        if os.path.exists(project_package_path):
            shutil.rmtree(project_package_path)

        shutil.copytree(self._installer_build_path, project_package_path, ignore=shutil.ignore_patterns(
            '*.Tests.*', '*.Editor.*', '*.Builders.*', '*.exe'))
        shutil.copy2(os.path.join(self._installer_build_path,
                                  f'{self._project_name}.GameLauncher.exe'), project_package_path)
        shutil.copy2(os.path.join(self._installer_build_path,
                                  f'{self._project_name}.ServerLauncher.exe'), project_package_path)
        # Copy over engine.json to the package root
        shutil.copy2(os.path.join(self._engine_path, 'engine.json'), project_package_path)
        # Copy over the Config folder to the package root
        # This is the workaround for a known issue where the AWSCore gem only reads resource mapping files
        # from the project source folder instead of cache
        shutil.copytree(os.path.join(self._project_path, 'Config'), os.path.join(project_package_path, 'Config'))
        print('...Done')

        # Compress the package for creating a custom Amazon Machine Image (AMI)
        zipped_package_path = f'{project_package_path}.zip'
        print(f'Archiving the project package to {zipped_package_path} ...')
        if os.path.exists(zipped_package_path):
            os.remove(zipped_package_path)
        shutil.make_archive(project_package_path, 'zip', project_package_path)
        print('...Done')

    def _get_generator(self):
        """
        Get the platform specific generator
        :return: Generator for the current platform
        """
        if self._platform == PLATFORM_WINDOWS:
            return WINDOWS_GENERATOR
        else:
            raise RuntimeError(f'Build for the {self._platform} platform is not supported yet')

    def _get_project_cache_path(self):
        """
        Get the platform specific cache path
        :return: Path to the cache folder for the current platform
        """
        project_cache_path = str(self._config.get(SCALER_CONFIG_PROJECT_CACHE_PATH_KEY,
                                                        SCALER_CONFIG_DEFAULT_PROJECT_CACHE_PATH))
        if self._platform == PLATFORM_WINDOWS:
            return os.path.join(project_cache_path, WINDOWS_CACHE_SUBFOLDER_NAME)
        else:
            raise RuntimeError(f'Build for the {self._platform} platform is not supported yet')
