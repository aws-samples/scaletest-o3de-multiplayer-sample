# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from __future__ import annotations
import typing

from aws_cdk import (
    aws_imagebuilder as image_builder,
)
from constructs import Construct

from .constants import *


class ImageComponentsBuilder:
    """
    Build the EC2 Image Builder component list
    """
    def __init__(self, scope: Construct, platform: str):
        self._components = []
        self._scope = scope
        self._platform = platform

    def add_vc_redistributable_component(self) -> ImageComponentsBuilder:
        """
        Add component to install VisualStudio Compiler (VC) Redistributable
        :return: The builder itself
        """
        if self._platform == PLATFORM_WINDOWS:
            platform = self._platform
        else:
            raise RuntimeError(f'VC redistributable component is only required for Windows')

        self._add_component(
            id_='VCRedistributableComponent',
            name=f'{RESOURCE_ID_COMMON_PREFIX}VCRedistributableComponent',
            description='Install VC Redistributable',
            platform=platform,
            data='name: InstallVCRedistributable\n'
                 'description: Install VC Redistributable\n'
                 'schemaVersion: 1.0\n'
                 'phases:\n'
                 '  - name: build\n'
                 '    steps:\n'
                 '      - name: InstallVCRedistributableStep\n'
                 '        action: ExecutePowerShell\n'
                 '        inputs:\n'
                 '          commands:\n'
                 '            - $Path = $env:TEMP; $Installer = "vc_redist.x86.exe"; Invoke-WebRequest "https://aka.ms/vs/17/release/vc_redist.x86.exe" -OutFile $Path\$Installer; Start-Process -FilePath $Path\$Installer -Args "/install /quiet /norestart" -Verb RunAs -Wait; Remove-Item $Path\$Installer\n'
                 '  - name: validate\n'
                 '    steps:\n'
                 '      - name: CheckInstall\n'
                 '        action: ExecutePowerShell\n'
                 '        inputs:\n'
                 '          commands:\n'
                 '            - |\n'
                 '              $count = Get-WmiObject -Class Win32_Product -Filter "Name LIKE \'%Visual C++ 2022%\'"\n'
                 '              if ($count.count -eq 0) {\n'
                 '                  echo "Visual Studio ReDistributables not installed"\n'
                 '                  exit 1\n'
                 '              }'
        )

        return self

    def add_launcher_download_component(self, source: str) -> ImageComponentsBuilder:
        """
        Add component to download the server package
        :return: The builder itself
        """
        if self._platform == PLATFORM_WINDOWS:
            platform = self._platform
        else:
            raise RuntimeError(f'Launcher download component for {self._platform} is not supported yet')

        self._add_component(
            id_='DownloadComponent',
            name=f'{RESOURCE_ID_COMMON_PREFIX}DownloadComponent',
            description='Download O3DE Launcher Components for Install',
            platform=platform,
            # Component data contains inline YAML document content for the component. Check
            # https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html
            data=f'name: O3DELauncherDownload\n'
                 f'description: Grab the build from S3\n'
                 f'schemaVersion: 1.0\n'
                 f'phases:\n'
                 f'  - name: build\n'
                 f'    steps:\n'
                 f'      - name: CreateTempDirectory\n'
                 f'        action: ExecutePowerShell\n'
                 f'        inputs:\n'
                 f'          commands:\n'
                 f'            - mkdir C:\\temp\n'
                 f'      - name: DownloadO3DELauncher\n'
                 f'        action: S3Download\n'
                 f'        onFailure: Abort\n'
                 f'        maxAttempts: 1\n'
                 f'        inputs:\n'
                 f'          - source: \'{source}\'\n'
                 f'            destination: C:\\temp\\Default.zip\n'
                 f'            overwrite: true\n'
                 f'      - name: UnzipO3DELauncher\n'
                 f'        action: ExecutePowerShell\n'
                 f'        inputs:\n'
                 f'          commands:\n'
                 f'            - Expand-Archive C:\\temp\\Default.zip -DestinationPath c:\\o3de\n'
        )

        return self

    def add_component_by_arn(self, arn: str) -> ImageComponentsBuilder:
        """
        Add an existing component by its Amazon resource name (ARN)
        :param arn: ARN of the existing component
        :return: The builder itself
        """
        self._components.append(arn)
        return self

    def _add_component(self, id_: str, name: str, description: str, platform: str, data: str) -> None:
        """
        Add a new component to the EC2 Image Builder component list
        """
        component = image_builder.CfnComponent(
            self._scope, id_,
            name=name,
            description=description,
            version='1.0.3', # in-place server stack updates must increment this
            change_description='First version',
            platform=platform,
            # Component data contains inline YAML document content for the component. Check
            # https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html
            data=data
        )
        self._components.append(component.ref)

    def build(self) -> typing.List:
        """
        Retrieve the EC2 Image Builder component list
        :return: Image Builder component list
        """
        return self._components
