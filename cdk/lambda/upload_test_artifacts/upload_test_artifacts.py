# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3

CFN_STACK_TAG_KEY = 'aws:cloudformation:stack-id'
DELETE_STATUS = 'DELETE_IN_PROGRESS'
SOURCE_BUCKET_EXPORT_NAME = 'MultiplayerTestScalerArtifactBucketName'
DEFAULT_DESTINATION_BUCKET_EXPORT_NAME = 'O3deMetricsUploadBucket'

def handler(event, context):
    stack_id = event['resources'][0]
    new_stack_status = event['detail']['status-details']['status']
    
    print(f'Status for stack {stack_id} has changed to: {new_stack_status}')
    if new_stack_status != DELETE_STATUS:
        print(f'Status change for stack is not {DELETE_STATUS}, NoOp.')
        return {
            'statusCode': 200,
        }
 
    # get artifact and metrics bucket names
    cfn = boto3.client('cloudformation')
    response = cfn.list_exports()
 
    source_bucket = ''
    destination_bucket = ''
    for export in response['Exports']:
        if export['Name'] == SOURCE_BUCKET_EXPORT_NAME:
            source_bucket = export['Value']
            print(f'source_bucket is: {source_bucket}')
        if export['Name'] == DEFAULT_DESTINATION_BUCKET_EXPORT_NAME:
            destination_bucket = export['Value']
            print(f'destination_bucket is: {destination_bucket}')
 
    if destination_bucket == '' or source_bucket == '':
        raise RuntimeError('Required bucket missing! No action will be taken.')
 
    # upload bucket content with unique key
    s3_client = boto3.client('s3')
    list_response = s3_client.list_objects(Bucket=source_bucket)
    print(f'source bucket contains {len(list_response["Contents"])} objects')
    for obj in list_response['Contents']:
        key_name = obj['Key']
        copy_source = {'Bucket': source_bucket, 'Key': key_name }
        s3_client.copy(copy_source, destination_bucket, f'MpScalerArtifacts/{key_name}')
    
    return {
        'statusCode': 200,
    }