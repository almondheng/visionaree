"""
Video Query Handler

This Lambda function handles queries about video analysis results.
It returns all segment captions for a given job ID.
"""

import json
import boto3
import logging
import os
from typing import Dict, Any, List
from decimal import Decimal
from segment_caption_update import list_job_segment_captions

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Get table names from environment variables
VIDEO_ANALYSIS_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
JOB_STATUS_TABLE_NAME = os.environ.get('JOB_STATUS_TABLE_NAME')

video_analysis_table = dynamodb.Table(VIDEO_ANALYSIS_TABLE_NAME) if VIDEO_ANALYSIS_TABLE_NAME else None
job_status_table = dynamodb.Table(JOB_STATUS_TABLE_NAME) if JOB_STATUS_TABLE_NAME else None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function to handle video segment requests.
    
    This function returns all segment captions for a given job ID.
    
    Args:
        event: API Gateway event containing the job ID
        context: Lambda context object
        
    Returns:
        Dict containing all segments for the job in JSON format
    """
    
    try:
        logger.info(f"Received video query event: {json.dumps(event, indent=2)}")
        
        # Extract job ID from path parameters
        path_parameters = event.get('pathParameters', {})
        job_id = path_parameters.get('jobId') if path_parameters else None
        
        if not job_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Missing jobId in path parameters',
                    'message': 'Job ID is required to get video segments'
                })
            }
        
        logger.info(f"Getting segments for job {job_id}")
        
        # Get all segments for the job
        segments_result = get_job_segments(job_id)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(segments_result, indent=2, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error processing video query: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': 'Failed to get video segments',
                'details': str(e)
            })
        }


def get_job_segments(job_id: str) -> Dict[str, Any]:
    """
    Get all segment captions for a given job ID.
    
    Args:
        job_id: The video job ID to get segments for
        
    Returns:
        Dict containing all segments for the job
    """
    
    try:
        # Get job status information
        job_info = get_job_status(job_id)
        
        if not job_info:
            return {
                'jobId': job_id,
                'status': 'error',
                'message': 'Job not found or analysis not completed',
                'segments': []
            }
        
        # Get all segment captions for this job
        segment_captions = list_job_segment_captions(job_id)
        
        if not segment_captions:
            return {
                'jobId': job_id,
                'status': 'no_data',
                'message': 'No segment captions found for this video',
                'jobInfo': {
                    'videoFileName': job_info.get('videoFileName', ''),
                    'videoDuration': job_info.get('videoDuration', 0),
                    'totalSegments': job_info.get('totalSegments', 0),
                    'processedSegments': job_info.get('processedSegments', 0),
                    'jobStatus': job_info.get('status', 'unknown')
                },
                'segments': []
            }
        
        # Sort segments by start time
        segment_captions.sort(key=lambda x: x.get('segmentStartTime', 0))
        
        # Prepare simplified segment data
        segments = []
        for segment in segment_captions:
            segments.append({
                'segmentStartTime': segment.get('segmentStartTime', 0),
                'caption': segment.get('caption', ''),
                'timestamp': segment.get('timestamp'),
                'metadata': segment.get('inferenceMetadata', {})
            })
        
        # Prepare the response
        response = {
            'jobId': job_id,
            'status': 'success',
            'jobInfo': {
                'videoFileName': job_info.get('videoFileName', ''),
                'videoDuration': job_info.get('videoDuration', 0),
                'totalSegments': job_info.get('totalSegments', 0),
                'processedSegments': job_info.get('processedSegments', 0),
                'jobStatus': job_info.get('status', 'unknown')
            },
            'totalSegments': len(segments),
            'segments': segments
        }
        
        logger.info(f"Retrieved {len(segments)} segments for job {job_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting segments for job {job_id}: {str(e)}")
        return {
            'jobId': job_id,
            'status': 'error',
            'message': f'Failed to get segments: {str(e)}',
            'segments': []
        }


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get job status information from DynamoDB.
    
    Args:
        job_id: The job ID to look up
        
    Returns:
        Job status information or None if not found
    """
    
    if not job_status_table:
        logger.warning("Job status table not configured")
        return None
    
    try:
        # Query the job status table for this job ID
        response = job_status_table.query(
            KeyConditionExpression='jobId = :job_id',
            ExpressionAttributeValues={':job_id': job_id},
            ScanIndexForward=False,  # Get most recent first
            Limit=1
        )
        
        items = response.get('Items', [])
        if items:
            return items[0]
        else:
            logger.warning(f"No job status found for job {job_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {str(e)}")
        return None