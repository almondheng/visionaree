"""
Job Status Update Module

This module handles all DynamoDB operations for tracking video processing job status.
It provides functions to create and update job status records in the DynamoDB table.
"""

import os
import boto3
import logging
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logger = logging.getLogger()
if not logger.handlers:
    logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Get table name from environment variable
JOB_STATUS_TABLE_NAME = os.environ.get('JOB_STATUS_TABLE_NAME')
job_status_table = dynamodb.Table(JOB_STATUS_TABLE_NAME) if JOB_STATUS_TABLE_NAME else None


def create_job_status_record(job_id: str, upload_timestamp: str, video_metadata: Dict[str, Any]) -> bool:
    """
    Create an initial job status record in DynamoDB.
    
    Args:
        job_id: Analysis job ID
        upload_timestamp: ISO timestamp when the video was uploaded
        video_metadata: Video file metadata
        
    Returns:
        Boolean indicating success
    """
    if not job_status_table:
        logger.warning("Job status table not configured, skipping status record creation")
        return False
    
    try:
        item = {
            'jobId': job_id,
            'uploadTimestamp': upload_timestamp,
            'status': 'pending',
            'videoFileName': video_metadata.get('filename', ''),
            'videoS3Uri': video_metadata.get('s3_uri', ''),
            'videoDuration': video_metadata.get('duration', 0),
            'videoSize': video_metadata.get('size', 0),
            'totalSegments': 0,
            'processedSegments': 0,
            'startTime': upload_timestamp,
            'endTime': None,
            'errorMessage': None,
            'metadata': {
                'resolution': video_metadata.get('resolution', 'unknown'),
                'codec': video_metadata.get('video_codec', 'unknown'),
                'contentType': video_metadata.get('content_type', 'unknown')
            }
        }
        
        job_status_table.put_item(Item=item)
        logger.info(f"✓ Created job status record for job {job_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create job status record for job {job_id}: {str(e)}")
        return False


def update_job_status_record(job_id: str, upload_timestamp: str, status: str, 
                           update_data: Dict[str, Any] = None) -> bool:
    """
    Update an existing job status record in DynamoDB.
    
    Args:
        job_id: Analysis job ID
        upload_timestamp: ISO timestamp when the video was uploaded
        status: New status ('pending', 'done', 'failed')
        update_data: Additional data to update
        
    Returns:
        Boolean indicating success
    """
    if not job_status_table:
        logger.warning("Job status table not configured, skipping status record update")
        return False
    
    try:
        # Prepare update expression and attribute values
        update_expression = "SET #status = :status, endTime = :end_time"
        expression_attribute_names = {'#status': 'status'}
        expression_attribute_values = {
            ':status': status,
            ':end_time': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add optional update data
        if update_data:
            for key, value in update_data.items():
                safe_key = key.replace('.', '_').replace(' ', '_')
                update_expression += f", {safe_key} = :{safe_key}"
                expression_attribute_values[f":{safe_key}"] = value
        
        job_status_table.update_item(
            Key={
                'jobId': job_id,
                'uploadTimestamp': upload_timestamp
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"✓ Updated job status record for job {job_id} to '{status}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update job status record for job {job_id}: {str(e)}")
        return False


def get_job_status_record(job_id: str, upload_timestamp: str) -> Dict[str, Any]:
    """
    Retrieve a job status record from DynamoDB.
    
    Args:
        job_id: Analysis job ID
        upload_timestamp: ISO timestamp when the video was uploaded
        
    Returns:
        Dictionary containing the job status record, or empty dict if not found
    """
    if not job_status_table:
        logger.warning("Job status table not configured, cannot retrieve status record")
        return {}
    
    try:
        response = job_status_table.get_item(
            Key={
                'jobId': job_id,
                'uploadTimestamp': upload_timestamp
            }
        )
        
        item = response.get('Item', {})
        if item:
            logger.info(f"✓ Retrieved job status record for job {job_id}")
        else:
            logger.warning(f"Job status record not found for job {job_id}")
            
        return item
        
    except Exception as e:
        logger.error(f"Failed to retrieve job status record for job {job_id}: {str(e)}")
        return {}


def list_job_status_records(limit: int = 50) -> List[Dict[str, Any]]:
    """
    List recent job status records from DynamoDB.
    
    Args:
        limit: Maximum number of records to return (default: 50)
        
    Returns:
        List of job status records
    """
    if not job_status_table:
        logger.warning("Job status table not configured, cannot list status records")
        return []
    
    try:
        response = job_status_table.scan(
            Limit=limit,
            ProjectionExpression='jobId, uploadTimestamp, #status, videoFileName, videoDuration, startTime, endTime',
            ExpressionAttributeNames={'#status': 'status'}
        )
        
        items = response.get('Items', [])
        logger.info(f"✓ Retrieved {len(items)} job status records")
        return items
        
    except Exception as e:
        logger.error(f"Failed to list job status records: {str(e)}")
        return []