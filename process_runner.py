# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import platform
import subprocess
import typing
from time import sleep


class ProcessRunner:
    """
    A naive process runner
    """

    def __init__(self, description: str, cmds_list: typing.List = []):
        self._description = description
        self._cmd_list = cmds_list

    @staticmethod
    def _stream(process: subprocess.Popen) -> bool:
        """
        Stream live output from the process
        :param process: Process to monitor
        """
        not_terminated = process.poll() is None
        for line in process.stdout:
            # Get binary strings back so decode to ascii for readability
            print(line.decode('utf-8'))
        return not_terminated

    def run(self, exec_dir: str='', env: dict=None) -> int:
        """
        Run the process
        :param exec_dir: Execution directory
        :param env: environment variables for running the process
        :return: exit code of the process being run
        """
        original_cwd = os.getcwd()
        if exec_dir:
            os.chdir(exec_dir)

        print(f'{self._description}: {str(self._cmd_list)}')

        try:
            cmd_args_to_run = self._get_cmd_args_for_os(self._cmd_list)
            process = subprocess.Popen(cmd_args_to_run,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    env=env)
            while self._stream(process):
                # Check for live output every 0.1s
                sleep(0.1)
        except Exception as e:
            print(f'Exception running command: {str(self._cmd_list)}')
            raise e

        # Something went wrong
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)

        os.chdir(original_cwd)
        return process.returncode

    @staticmethod
    def _get_cmd_args_for_os(cmd_args: typing.List) -> typing.List:
        if platform.system() == 'Windows':
            return ['powershell.exe'] + cmd_args
        else:
            return cmd_args
