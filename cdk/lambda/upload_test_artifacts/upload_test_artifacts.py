# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3

CFN_STACK_TAG_KEY = 'aws:cloudformation:stack-id'
DELETE_STATUS = 'DELETE_IN_PROGRESS'
SOURCE_BUCKET_EXPORT_NAME = 'MultiplayerTestScalerArtifactBucketName'
DEFAULT_DESTINATION_BUCKET_EXPORT_NAME = 'O3deMetricsUploadBucket'

def handler(event, context):
    if 'resources' not in event or type(event['resources']) is not list or len(event['resources']) < 1:
        raise RuntimeError('List of resources not provided! No action will be taken.')
    
    stack_id = event['resources'][0]
    new_stack_status = event['detail']['status-details']['status']
    
    print(f'Status for stack {stack_id} has changed to: {new_stack_status}')
    if new_stack_status != DELETE_STATUS:
        print(f'Status change for stack is not {DELETE_STATUS}, ignoring.')
        return {
            'statusCode': 200,
        }
 
    # get artifact and metrics bucket names
    cfn = boto3.client('cloudformation')
    export_dict = find_exported_buckets(cfn)
    source_bucket = export_dict['source']
    destination_bucket = export_dict['destination']
    
    if "".__eq__(destination_bucket):
        raise RuntimeError('Upload destination bucket missing! No action will be taken.')
    
    if "".__eq__(source_bucket):
        raise RuntimeError('Artifact source bucket missing! No action will be taken.')
 
    # upload bucket content with unique key
    s3_client = boto3.client('s3')

    # see: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/paginator/ListObjectsV2.html
    list_objects_paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = list_objects_paginator.paginate(Bucket=source_bucket)
    for page in page_iterator:
        print(f'list of source bucket contents contains {len(page["Contents"])} objects')
        for obj in page['Contents']:
            key_name = obj['Key']
            copy_source = {'Bucket': source_bucket, 'Key': key_name }
            s3_client.copy(copy_source, destination_bucket, f'MpScalerArtifacts/{key_name}')
    
    return {
        'statusCode': 200,
    }
    
def find_exported_buckets(cfn_client: any) -> dict:
    found_buckets = {
        'source': '',
        'destination': ''
    }

    # see: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation/paginator/ListExports.html
    exports_paginator = cfn_client.get_paginator('list_exports')
    page_iterator = exports_paginator.paginate()
    for page in page_iterator:
        if found_buckets['source'] != "" and found_buckets['destination'] != "":
            break  # if we already found both buckets, stop searching
        for export in page['Exports']:
            if export['Name'] == SOURCE_BUCKET_EXPORT_NAME:
                value = export['Value']
                found_buckets['source'] = value
                print(f'source bucket is: {value}')
            if export['Name'] == DEFAULT_DESTINATION_BUCKET_EXPORT_NAME:
                value = export['Value']
                found_buckets['destination'] = value
                print(f'destination bucket is: {value}')

    return found_buckets