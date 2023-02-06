# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import typing

from aws_cdk import (
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_iam as iam,
    aws_imagebuilder as image_builder,
)
import aws_cdk as cdk
from constructs import Construct

from .constants import *
from .image_components_builder import ImageComponentsBuilder

class CustomImageBuilderConstruct(Construct):
    """
    Custom Image builder construct for building the server Amazon Machine Image (AMI)
    """

    def __init__(self, scope: Construct, construct_id: str, key_pair: str,
                 instance_role: iam.Role, platform: str) -> None:
        super().__init__(scope, construct_id)
        self._instance_role = instance_role
        self._key_pair = key_pair
        self._platform = platform

        self._add_image_builder_permissions()
        self._enable_image_builder_logging()
        self._create_custom_ami()

    def _add_image_builder_permissions(self) -> None:
        """
        Create the instance profile for EC2 Image Builder and add required permissions
        For more details, see https://docs.aws.amazon.com/imagebuilder/latest/userguide/security_iam_service-with-iam.html#security_iam_id-based-policy-examples
        """
        self._instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('EC2InstanceProfileForImageBuilder'))
        self._instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        self._image_builder_instance_profile = iam.CfnInstanceProfile(
            self, 'InstanceProfile',
            path='/executionServiceEC2Role/',
            roles=[self._instance_role.role_name]
        )

    def _enable_image_builder_logging(self) -> None:
        """
        Create an Amazon S3 bucket for storing EC2 Image Builder logs
        """
        self._log_bucket = s3.Bucket(
            self, 'LogBucket',
            lifecycle_rules=[s3.LifecycleRule(expiration=cdk.Duration.days(30))],
            removal_policy=cdk.RemovalPolicy.RETAIN
        )

        # Set image builder logging permission
        iam.Policy(
            self, 'LogBucketPolicy',
            policy_name=f'{RESOURCE_ID_COMMON_PREFIX}LogBucketPolicy',
            roles=[self._instance_role],
            document=iam.PolicyDocument(
                statements=[iam.PolicyStatement(
                    actions=['s3:PutObject'],
                    effect=iam.Effect.ALLOW,
                    resources=[cdk.Fn.sub(
                        'arn:${AWS::Partition}:s3:::${BUCKET}/*',
                        {'BUCKET': self._log_bucket.bucket_name}
                    )]
                )]
            ),
        )

    def _create_image_builder_infra_config(
            self, instance_profile_name: str) -> image_builder.CfnInfrastructureConfiguration:
        """
        Create the infrastructure configurations that EC2 Image Builder uses to build and test the built image.
        Check https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-infra-config.html for more details
        :param instance_profile_name: Instance profile named used by Image Builder
        :return: Infrastructure configuration for Image Builder
        """
        return image_builder.CfnInfrastructureConfiguration(
            self, 'InfrastructureConfiguration',
            name=f'{RESOURCE_ID_COMMON_PREFIX}InfrastructureConfiguration',
            instance_profile_name=instance_profile_name,
            logging=image_builder.CfnInfrastructureConfiguration.LoggingProperty(
                s3_logs=image_builder.CfnInfrastructureConfiguration.S3LogsProperty(
                    s3_bucket_name=self._log_bucket.bucket_name
                )
            ),
            terminate_instance_on_failure=True,
            instance_types=['c5.large'],
            key_pair=self._key_pair
        )

    def _create_image_builder_recipe(self) -> image_builder.CfnImageRecipe:
        """
        Create the EC2 Image Builder recipe that defines the base image to use as the starting point to create a new image,
        along with the set of components to customize the image and verify that everything is working as expected.
        Check https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-recipes.html for more details
        :return: Recipe for Image Builder
        """
        if self._platform == PLATFORM_WINDOWS:
            parent_image = cdk.Fn.sub(
                'arn:${AWS::Partition}:imagebuilder:${AWS::Region}:aws:image/windows-server-2019-english-full-base-x86/x.x.x')
        else:
            raise RuntimeError(f'Server for the {self._platform} platform is not supported yet')

        return image_builder.CfnImageRecipe(
            self, 'Recipe',
            name=f'{RESOURCE_ID_COMMON_PREFIX}Recipe',
            version='1.0.0', # in-place server stack updates must increment this
            parent_image=parent_image,
            components=[
                image_builder.CfnImageRecipe.ComponentConfigurationProperty(
                    component_arn=component_arn) for component_arn in self._create_image_builder_components()
            ]
        )

    def _create_image_builder_components(self) -> typing.List[str]:
        """
        Create the YAML documents based EC2 Image Builder components that define the scripts to customize or test the image.
        Check https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-components.html for more details
        :return: List of components for building image
        """
        project_package_asset = self._upload_project_package()
        project_package_asset.grant_read(self._instance_role)

        return ImageComponentsBuilder(self, self._platform) \
            .add_vc_redistributable_component() \
            .add_launcher_download_component(project_package_asset.s3_object_url) \
            .add_component_by_arn(cdk.Fn.sub(
            'arn:${AWS::Partition}:imagebuilder:${AWS::Region}:aws:component/powershell-windows/x.x.x')) \
            .build()

    def _upload_project_package(self) -> s3_assets.Asset:
        """
        Upload the project package to Amazon S3 for creating the AMI
        :return: Uploaded S3 asset
        """
        return s3_assets.Asset(
            self, 'ProjectPackage',
            path=f'{ASSET_DIR_ROOT}/{self._platform}/{ZIPPED_PACKAGE_NAME}'
        )

    def _create_image_builder_distribution(self) -> image_builder.CfnDistributionConfiguration:
        """
        Create the EC2 Image Builder distribution used to distribute the AMI.
        Check https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-distribution-settings.html for more details
        :return: The EC2 Image Builder distribution config
        """
        return image_builder.CfnDistributionConfiguration(
            self, f'Distribution',
            name=f'{RESOURCE_ID_COMMON_PREFIX}Distribution',
            distributions=[
                image_builder.CfnDistributionConfiguration.DistributionProperty(
                    region=cdk.Fn.ref('AWS::Region'),
                    ami_distribution_configuration={
                        'Name': 'o3de-multiplayer-test-scaler-ami-{{ imagebuilder:buildDate }}',
                        'Description': 'O3DE Multiplayer Test Scaler AMI',
                        'AmiTags': {
                            'AmiTagKey': 'o3de-multiplayer-test-scaler-ami',
                            'Name': 'o3de-multiplayer-test-scaler-ami-{{ imagebuilder:buildDate }}'
                        }
                    }
                )
            ]
        )

    def _create_custom_ami(self) -> None:
        """
        Build a custom Amazon Machine Image (AMI) which includes the multiplayer server
        """
        self._o3de_launcher_image = image_builder.CfnImage(
            self, 'Image',
            image_recipe_arn=self._create_image_builder_recipe().ref,
            infrastructure_configuration_arn=self._create_image_builder_infra_config(
                self._image_builder_instance_profile.ref).attr_arn,
            distribution_configuration_arn=self._create_image_builder_distribution().ref,
            enhanced_image_metadata_enabled=False
        )

    @property
    def custom_image_id(self) -> str:
        """
        Retrieve the custom image ID
        :return: Image ID
        """
        return self._o3de_launcher_image.attr_image_id