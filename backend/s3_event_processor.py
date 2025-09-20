import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, List
import logging
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function to process S3 upload events.
    
    This function is triggered when files are uploaded to the S3 bucket
    and performs processing on the uploaded video files.
    
    Args:
        event: S3 event notification containing bucket and object information
        context: Lambda context object
        
    Returns:
        Dict containing processing status and results
    """
    
    try:
        logger.info(f"Received S3 event: {json.dumps(event, indent=2)}")
        
        # Process each record in the S3 event
        processed_files = []
        
        for record in event.get('Records', []):
            # Extract S3 bucket and object information
            s3_info = record.get('s3', {})
            bucket_name = s3_info.get('bucket', {}).get('name')
            object_key = unquote_plus(s3_info.get('object', {}).get('key', ''))
            object_size = s3_info.get('object', {}).get('size', 0)
            event_name = record.get('eventName', '')
            
            if not bucket_name or not object_key:
                logger.warning(f"Invalid S3 event record: {record}")
                continue
            
            logger.info(f"Processing S3 event: {event_name} for {bucket_name}/{object_key}")
            
            # Only process video files in the videos/ prefix
            if not object_key.startswith('videos/'):
                logger.info(f"Skipping non-video file: {object_key}")
                continue
            
            # Extract job ID from the S3 key path
            # Expected format: videos/{jobId}/original/{filename}
            path_parts = object_key.split('/')
            if len(path_parts) < 4:
                logger.warning(f"Unexpected S3 key format: {object_key}")
                continue
            
            job_id = path_parts[1]
            file_category = path_parts[2]  # Should be 'original'
            filename = path_parts[3]
            
            # Validate that this is an original file upload
            if file_category != 'original':
                logger.info(f"Skipping non-original file: {object_key}")
                continue
            
            # Process the uploaded video file
            processing_result = process_video_upload(
                bucket_name=bucket_name,
                object_key=object_key,
                job_id=job_id,
                filename=filename,
                file_size=object_size
            )
            
            processed_files.append(processing_result)
        
        return {
            'statusCode': 200,
            'body': {
                'message': f'Successfully processed {len(processed_files)} files',
                'processedFiles': processed_files
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing S3 event: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'message': 'Failed to process S3 event'
            }
        }


def process_video_upload(bucket_name: str, object_key: str, job_id: str, 
                        filename: str, file_size: int) -> Dict[str, Any]:
    """
    Process an uploaded video file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        job_id: Analysis job ID
        filename: Original filename
        file_size: File size in bytes
        
    Returns:
        Dict containing processing results
    """
    
    try:
        logger.info(f"Processing video upload: {bucket_name}/{object_key}")
        
        # Get file metadata from S3
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            last_modified = response.get('LastModified')
            content_type = response.get('ContentType', 'unknown')
            etag = response.get('ETag', '').strip('"')
            
            logger.info(f"File metadata - Size: {file_size}, Type: {content_type}, ETag: {etag}")
            
        except ClientError as e:
            logger.error(f"Failed to get object metadata: {str(e)}")
            raise
        
        # TODO: Implement video processing logic
        # This is where you would add your video processing steps:
        
        # TODO: 1. Validate video file format and integrity
        # - Check if the file is a valid video format
        # - Verify file is not corrupted
        # - Extract video metadata (duration, resolution, codec, etc.)
        
        # TODO: 2. Generate video thumbnails
        # - Extract key frames from the video
        # - Generate thumbnail images at different timestamps
        # - Store thumbnails in S3 under videos/{jobId}/thumbnails/
        
        # TODO: 3. Extract video metadata
        # - Duration, resolution, frame rate, codec information
        # - Store metadata in DynamoDB or as JSON in S3
        
        # TODO: 4. Trigger video analysis workflow
        # - Queue the video for Bedrock Nova Lite analysis
        # - Send message to SQS queue for batch processing
        # - Or directly invoke the main analysis Lambda function
        
        # TODO: 5. Generate preview clips
        # - Create short preview clips (first 30 seconds)
        # - Store previews in S3 under videos/{jobId}/previews/
        
        # TODO: 6. Update job status
        # - Update DynamoDB table with processing status
        # - Send notifications via SNS if configured
        
        # TODO: 7. Content validation
        # - Check for inappropriate content using AWS Rekognition
        # - Validate video meets security analysis requirements
        
        # For now, just log the processing steps
        logger.info("TODO: Implementing video processing steps...")
        logger.info("TODO: 1. Validate video file format and integrity")
        logger.info("TODO: 2. Generate video thumbnails")
        logger.info("TODO: 3. Extract video metadata")
        logger.info("TODO: 4. Trigger video analysis workflow")
        logger.info("TODO: 5. Generate preview clips")
        logger.info("TODO: 6. Update job status")
        logger.info("TODO: 7. Content validation")
        
        # Simulate processing time and create result
        processing_result = {
            'jobId': job_id,
            'filename': filename,
            'objectKey': object_key,
            'fileSize': file_size,
            'contentType': content_type,
            'etag': etag,
            'status': 'processed',
            'timestamp': last_modified.isoformat() if last_modified else None,
            'processingSteps': [
                {'step': 'file_validation', 'status': 'pending'},
                {'step': 'thumbnail_generation', 'status': 'pending'},
                {'step': 'metadata_extraction', 'status': 'pending'},
                {'step': 'analysis_trigger', 'status': 'pending'},
                {'step': 'preview_generation', 'status': 'pending'},
                {'step': 'status_update', 'status': 'pending'},
                {'step': 'content_validation', 'status': 'pending'}
            ]
        }
        
        logger.info(f"Processing completed for {object_key}")
        return processing_result
        
    except Exception as e:
        logger.error(f"Error processing video upload {object_key}: {str(e)}")
        return {
            'jobId': job_id,
            'filename': filename,
            'objectKey': object_key,
            'status': 'error',
            'error': str(e)
        }


def validate_video_file(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    TODO: Validate video file format and integrity.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dict containing validation results
    """
    # TODO: Implement video validation logic
    # - Download file header to check format
    # - Use FFmpeg or similar to validate video integrity
    # - Extract basic metadata
    pass


def generate_thumbnails(bucket_name: str, object_key: str, job_id: str) -> List[str]:
    """
    TODO: Generate thumbnails from video file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        job_id: Analysis job ID
        
    Returns:
        List of S3 keys for generated thumbnails
    """
    # TODO: Implement thumbnail generation
    # - Extract frames at specific intervals
    # - Resize to standard thumbnail sizes
    # - Upload to S3 under videos/{jobId}/thumbnails/
    pass


def extract_metadata(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    TODO: Extract video metadata.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dict containing video metadata
    """
    # TODO: Implement metadata extraction
    # - Use FFmpeg to extract detailed video information
    # - Duration, resolution, frame rate, codec, bitrate
    # - Store metadata in structured format
    pass


def trigger_analysis_workflow(bucket_name: str, object_key: str, job_id: str) -> bool:
    """
    TODO: Trigger the video analysis workflow.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        job_id: Analysis job ID
        
    Returns:
        Boolean indicating success
    """
    # TODO: Implement analysis workflow trigger
    # - Send message to SQS queue for batch processing
    # - Or directly invoke Bedrock Nova Lite analysis
    # - Update job status in database
    pass