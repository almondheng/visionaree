"""
Segment Caption Update Module

This module handles writing video segment inference results to the VideoAnalysisTable in DynamoDB.
It provides functions to store caption data from Bedrock inference results.
"""

import os
import boto3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import time

# Configure logging
logger = logging.getLogger()
if not logger.handlers:
    logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Get table name from environment variable
VIDEO_ANALYSIS_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
video_analysis_table = dynamodb.Table(VIDEO_ANALYSIS_TABLE_NAME) if VIDEO_ANALYSIS_TABLE_NAME else None


def save_segment_caption(job_id: str, segment_start_time: int, 
                        caption: str, inference_metadata: Dict[str, Any] = None) -> bool:
    """
    Save a video segment caption to the VideoAnalysisTable.
    
    Args:
        job_id: Analysis job ID
        segment_start_time: Start time of the segment in seconds
        caption: The inference result caption from Bedrock
        inference_metadata: Additional metadata about the inference
        
    Returns:
        Boolean indicating success
    """
    if not video_analysis_table:
        logger.warning("Video analysis table not configured, skipping caption save")
        return False
    
    try:
        # Prepare the item to store
        item = {
            'jobIdPartitionId': job_id,  # Use job_id directly as partition key
            'segmentStartTime': segment_start_time,
            'caption': caption,
            'jobId': job_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'createdAt': int(time.time() * 1000)  # Unix timestamp in milliseconds
        }
        
        # Add inference metadata if provided
        if inference_metadata:
            item['inferenceMetadata'] = inference_metadata
        
        # Save to DynamoDB
        video_analysis_table.put_item(Item=item)
        logger.info(f"✓ Saved caption for segment {segment_start_time}s (job: {job_id})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save caption for segment {segment_start_time}s: {str(e)}")
        return False


def save_batch_segment_captions(inference_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Save multiple segment captions in batch to DynamoDB.
    
    Args:
        inference_results: List of inference results from Bedrock processing
        
    Returns:
        Dict containing batch save results
    """
    if not video_analysis_table:
        logger.warning("Video analysis table not configured, skipping batch caption save")
        return {'success': False, 'saved_count': 0, 'failed_count': 0}
    
    saved_count = 0
    failed_count = 0
    errors = []
    
    try:
        logger.info(f"Starting batch save of {len(inference_results)} segment captions")
        
        for result in inference_results:
            if result.get('status') == 'success' and result.get('caption'):
                job_id = result.get('job_id')
                start_time = result.get('start_time')
                caption = result.get('caption')
                
                # Prepare inference metadata
                inference_metadata = {
                    'status': result.get('status'),
                    'model_id': 'us.amazon.nova-pro-v1:0',  # From the summarize.py module
                    'inference_timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                
                # Add error information if available
                if result.get('error'):
                    inference_metadata['error'] = result.get('error')
                
                success = save_segment_caption(
                    job_id=job_id,
                    segment_start_time=start_time,
                    caption=caption,
                    inference_metadata=inference_metadata
                )
                
                if success:
                    saved_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Failed to save segment {start_time}s")
            else:
                # Skip failed inference results
                failed_count += 1
                start_time = result.get('start_time', 'unknown')
                error_msg = result.get('error', 'No caption available')
                errors.append(f"Skipped segment {start_time}s: {error_msg}")
                logger.warning(f"Skipping failed inference result for segment {start_time}s: {error_msg}")
        
        logger.info(f"Batch save completed: {saved_count} saved, {failed_count} failed")
        
        return {
            'success': saved_count > 0,
            'saved_count': saved_count,
            'failed_count': failed_count,
            'total_processed': len(inference_results),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Error in batch caption save: {str(e)}")
        return {
            'success': False,
            'saved_count': saved_count,
            'failed_count': failed_count + (len(inference_results) - saved_count),
            'total_processed': len(inference_results),
            'errors': errors + [f"Batch operation error: {str(e)}"]
        }


def get_segment_caption(job_id: str, segment_start_time: float) -> Optional[Dict[str, Any]]:
    """
    Get a specific segment caption from DynamoDB.
    
    Args:
        job_id: The job ID
        segment_start_time: The segment start time in seconds
        
    Returns:
        Dict containing the segment caption data, or None if not found
    """
    if not video_analysis_table:
        logger.warning("Video analysis table not configured")
        return None
    
    try:
        response = video_analysis_table.get_item(
            Key={
                'jobId': job_id,
                'segmentStartTime': Decimal(str(segment_start_time))
            }
        )
        
        if 'Item' in response:
            logger.info(f"Retrieved segment caption for job {job_id} at {segment_start_time}s")
            return response['Item']
        else:
            logger.info(f"No segment caption found for job {job_id} at {segment_start_time}s")
            return None
            
    except Exception as e:
        logger.error(f"Error getting segment caption for job {job_id} at {segment_start_time}s: {str(e)}")
        return None


def list_job_segment_captions(job_id: str) -> List[Dict[str, Any]]:
    """
    List all segment captions for a job from DynamoDB.
    
    Args:
        job_id: The job ID
        
    Returns:
        List of segment caption records for the job
    """
    if not video_analysis_table:
        logger.warning("Video analysis table not configured")
        return []
    
    try:
        logger.info(f"Querying segments for job {job_id}")
        
        # Query all segments for this job
        response = video_analysis_table.query(
            KeyConditionExpression='jobId = :job_id',
            ExpressionAttributeValues={
                ':job_id': job_id
            }
        )
        
        segments = response.get('Items', [])
        logger.info(f"Found {len(segments)} segments for job {job_id}")
        
        return segments
        
    except Exception as e:
        logger.error(f"Error listing segments for job {job_id}: {str(e)}")
        return []