
# Multiplayer Test Scaler AWS CDK application

This is the AWS Cloud Development Kit (CDK) application O3DE Multiplayer Test Scaler uses to deploy an O3DE multiplayer project into AWS.

When fully deployed, the following AWS Cloudformation stacks will be created in your AWS account:
- Common stack: Includes resources (VPC, security group, etc.) that will be shared by the other two stacks.
- Server stack: Includes EC2 image builder resources to create the server Amazon Machine Image (AMI) and the Amazon EC2 instance running the server AMI.
- Client stack: Includes Amazon Elastic Container Service (ECS) resources for running the clients.

## Prerequisites

This CDK project expects the following artifacts to be available in the `assets/{Platform}` directory:
1. A folder called "project" which contains release binaries and assets of an O3DE multiplayer project. See the [O3DE documentation](https://www.o3de.org/docs/user-guide/packaging/windows-release-builds/) for more details on packaging your project.
1. A compressed version of the same project within a compressed file called `project.zip`.

If using the O3DE Multiplayer Test Scaler CLI (in the directory above this one), the `build` step will generate these for you. See the [top level README](../README.md) for details.


## Standalone deployment

To synthesize the AWS CloudFormation template for this project, run:

```
$ cdk synth -c key_pair={ec2_key_pair} -c server_port={server_port} -c server_private_ip={static_server_private_ip} -c local_reference_machine_cidr={local_reference_machine_cidr} -c client_count={num_of_clients_to_launch} -c platform=Windows  --all
```

To deploy the AWS CDK application, run:
```
$ cdk deploy -c key_pair={ec2_key_pair} -c server_port={server_port} -c server_private_ip={static_server_private_ip} -c local_reference_machine_cidr={local_reference_machine_cidr} -c client_count={num_of_clients_to_launch} -c platform=Windows  --all
```

### Arguments
- _client_count_: Number of clients to launch.
- _key_pair_: Amazon EC2 key pair to use.
- _local_reference_machine_cidr_: External IPv4 CIDR for local reference machines that need to connect to the remote server for verification.
- _platform_: Platform for deploying the project package. This will default to Windows if not specified.
- _server_port_: Server port to use. This will default to 33450 if not specified.
- _server_private_ip_: Static IP address to assign to the server. In this CDK application, the public subnet used to deploy the server instance has a IPv4 CIDR of 10.0.0.0/24. The server private IP address should fall within the subnet CIDR, and also be included in the project's `launch_client.cfg` file.
- _target_: The target to deploy, server or client. Both stacks will be deployed if no target is specified.

## Environment Variables
- O3DE_AWS_DEPLOY_REGION: AWS region to deploy resources
- O3DE_AWS_DEPLOY_ACCOUNT: AWS account to deploy resources
- O3DE_AWS_PROJECT_NAME: Name of the project to deploy. Defaults to MULTIPLAYER-TEST-SCALER

## Deployment Configurations
Modify the `constants.py` values to change your project and hardware configurations

## Useful Commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
