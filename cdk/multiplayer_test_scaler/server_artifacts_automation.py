# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_ssm as ssm,
)
import aws_cdk as cdk
from constructs import Construct

from .constants import *

class ServerAutomationConstruct(Construct):
    """
    Builds automation resources for pulling logs and metrics files off the server
    """

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        
    def create_file_sync_rule(self, artifact_bucket_name: str) -> events.CfnRule:
        self._create_command_document(artifact_bucket_name)

        doc_arn = Stack.of(self).format_arn(
            service="ssm",
            resource="document",
            resource_name=self._file_sync_document.name
        )

        doc_run_role = iam.Role(
            self, f'{RESOURCE_ID_COMMON_PREFIX}InvokeUploadRuleRole',
            description='Role to be used by Event Bridge to run file sync rule',
            assumed_by=iam.ServicePrincipal('events.amazonaws.com'),
            inline_policies={'InvokeFileSyncRulePolicy': iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['ssm:SendCommand'],
                        resources=[
                            doc_arn,
                            cdk.Fn.sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:instance/*'),
                        ]
                    )
                ])
            }
        )

        # can't use L2 events.Rule b/c it doesn't yet support
        # SSM RunCommand targets. See: https://github.com/aws/aws-cdk/issues/7710
        self._file_sync_rule = events.CfnRule(self, 'IntermitentUploadRule',
            name=f'{RESOURCE_ID_COMMON_PREFIX}SyncArtifactsRule',
            schedule_expression='rate(2 minutes)',
            targets=[events.CfnRule.TargetProperty(
                arn=doc_arn,
                id='MpScalerFileSyncRule',
                run_command_parameters=events.CfnRule.RunCommandParametersProperty(
                    run_command_targets=[events.CfnRule.RunCommandTargetProperty(
                        key="tag:aws:cloudformation:stack-id",
                        values=[Stack.of(self).stack_id] # will run on EC2 instances deployed by this stack
                    )]
                ),
                role_arn=doc_run_role.role_arn
            )]
        )

    def create_upload_trigger(self, upload_lambda: _lambda.Function):
        """
        On server stack deletion, triggers upload of server artifacts 
        to external bucket
        """
        self._final_upload_trigger = events.Rule(self, 'FinalUploadTrigger', 
            event_pattern=events.EventPattern(
                source=["aws.cloudformation"],
                detail_type=["CloudFormation Stack Status Change"],
                resources=[Stack.of(self).stack_id]
            )
        )
        self._final_upload_trigger.add_target(
            events_targets.LambdaFunction(upload_lambda, retry_attempts=2))

    def _create_command_document(self, artifact_bucket_name: str):
        doc_content = {
            "schemaVersion": "2.2",
            "description": "Syncs game server files to artifact bucket",
            "parameters": {
                "bucket": {
                    "type": "String",
                    "description": "The bucket where files will be synced",
                    "default": artifact_bucket_name
                },
                "MPSFolder": {
                    "type": "String",
                    "description": "The folder where files are copied prior to sync to S3",
                    "default": "C:/o3de/user/mpscaler"
                }
            },
            "mainSteps": [
                {
                    "action": "aws:runPowerShellScript",
                    "name": "CreateMpsDir",
                    "inputs": {
                        "runCommand": [
                            "if (!(test-path -path 'C:/o3de/user/{{MPSFolder}}')) { mkdir {{MPSFolder}} }"
                        ]
                    }
                },
                {
                    "action": "aws:runPowerShellScript",
                    "name": "CopyFolders", # need to copy files first b/c originals will be locked by game process
                    "inputs": {
                        "runCommand": [
                            "copy-item -path 'C:/o3de/user/log' -destination {{MPSFolder}} -recurse -force",
                            "copy-item -path 'C:/o3de/user/Metrics' -destination {{MPSFolder}} -recurse -force"
                        ]
                    }
                },
                {
                    "action": "aws:runPowerShellScript",
                    "name": "UploadToS3",
                    "inputs": {
                        "runCommand": [
                            # retreive token and instance ID from EC2 Instance Metadata Service v2
                            # see: https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/configuring-instance-metadata-service.html#instance-metadata-v2-how-it-works
                            '[string]$token = Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token-ttl-seconds" = "30"} -Method PUT -Uri http://169.254.169.254/latest/api/token',
                            '$id = (Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token" = $token} -Method GET -Uri http://169.254.169.254/latest/meta-data/instance-id)',
                            "$date = get-date -format 'ddMMyyyy'",
                            "write-s3object -bucketname {{bucket}} -folder {{MPSFolder}} -keyprefix $date\\server\\$id -recurse"
                        ]
                    }
                }
            ]
        }

        # since Cfn resource type 'AWS::SSM::Document' does not contain an 'Arn' attribute to query, 
        # we need to set a static 'name' in order to be able to recreate the document ARN in create_file_sync_rule()
        self._file_sync_document = ssm.CfnDocument(self, "ServerAutomationDoc",
            content=doc_content,
            document_type="Command",
            name=f'{RESOURCE_ID_COMMON_PREFIX}-server-upload-command'                            
        )
