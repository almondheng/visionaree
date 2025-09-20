import json
import boto3
import subprocess
import shlex
from botocore.exceptions import ClientError
from typing import Dict, Any, List
import logging
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

# FFmpeg path in Lambda layer
FFMPEG_PATH = '/opt/bin/ffmpeg'

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
        
        # Step 1: Validate video file format and integrity
        logger.info("Step 1: Validating video file format and integrity...")
        validation_result = validate_video_file(bucket_name, object_key)
        
        if not validation_result.get('valid', False):
            logger.error(f"Video validation failed: {validation_result.get('message', 'Unknown error')}")
            return {
                'jobId': job_id,
                'filename': filename,
                'objectKey': object_key,
                'status': 'validation_failed',
                'error': validation_result.get('error', 'Validation failed'),
                'validation': validation_result
            }
        
        logger.info(f"Video validation successful: {validation_result.get('message', 'Valid')}")
        
        # TODO: 2. Generate video thumbnails
        # - Extract key frames from the video
        # - Generate thumbnail images at different timestamps
        # - Store thumbnails in S3 under videos/{jobId}/thumbnails/
        
        # Step 3: Extract video metadata using FFmpeg
        logger.info("Step 3: Extracting video metadata using FFmpeg...")
        metadata = extract_metadata(bucket_name, object_key)
        
        # Print metadata output instead of storing
        logger.info("=== Video Metadata ===")
        logger.info(json.dumps(metadata, indent=2))
        logger.info("=== End Metadata ===")
        
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
        
        # Create processing result with metadata
        logger.info("Video processing steps:")
        logger.info("✓ 1. File validation (basic)")
        logger.info("✓ 2. Video metadata extraction with FFmpeg")
        logger.info("✓ 3. Metadata logged to CloudWatch")
        logger.info("TODO: 4. Generate video thumbnails")
        logger.info("TODO: 5. Trigger video analysis workflow")
        logger.info("TODO: 6. Generate preview clips")
        logger.info("TODO: 7. Update job status")
        logger.info("TODO: 8. Content validation")
        
        # Create processing result with metadata
        processing_result = {
            'jobId': job_id,
            'filename': filename,
            'objectKey': object_key,
            'fileSize': file_size,
            'contentType': content_type,
            'etag': etag,
            'status': 'processed',
            'timestamp': last_modified.isoformat() if last_modified else None,
            'metadata': {
                'duration': metadata.get('file_info', {}).get('duration', 0) if 'file_info' in metadata else 0,
                'resolution': f"{metadata.get('video_info', {}).get('width', 0)}x{metadata.get('video_info', {}).get('height', 0)}" if metadata.get('video_info') else 'unknown',
                'video_codec': metadata.get('video_info', {}).get('codec_name', 'unknown') if metadata.get('video_info') else 'unknown',
                'audio_codec': metadata.get('audio_info', {}).get('codec_name', 'unknown') if metadata.get('audio_info') else 'unknown',
                'has_error': 'error' in metadata
            },
            'processingSteps': [
                {'step': 'file_validation', 'status': 'completed'},
                {'step': 'metadata_extraction', 'status': 'completed'},
                {'step': 'metadata_logging', 'status': 'completed'},
                {'step': 'thumbnail_generation', 'status': 'pending'},
                {'step': 'analysis_trigger', 'status': 'pending'},
                {'step': 'preview_generation', 'status': 'pending'},
                {'step': 'status_update', 'status': 'pending'},
                {'step': 'content_validation', 'status': 'pending'}
            ]
        }
        
        logger.info(f"Processing completed for {object_key}")
        if not metadata.get('error'):
            logger.info(f"Video metadata: {processing_result['metadata']['duration']:.2f}s, {processing_result['metadata']['resolution']}, {processing_result['metadata']['video_codec']}")
        
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
    Validate video file format and integrity using FFmpeg.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dict containing validation results
    """
    try:
        logger.info(f"Validating video file: {bucket_name}/{object_key}")
        
        # Download file to /tmp for FFprobe analysis
        local_file_path = f"/tmp/{object_key.split('/')[-1]}"
        
        try:
            s3_client.download_file(bucket_name, object_key, local_file_path)
            logger.info(f"Downloaded {object_key} to {local_file_path}")
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            return {
                'valid': False,
                'error': str(e),
                'message': 'Failed to download file for validation'
            }
        
        # Simple FFmpeg command to validate the file by attempting to read it
        # If FFmpeg can read the file without errors, it's likely a valid video
        ffmpeg_cmd = f'{FFMPEG_PATH} -v error -i "{local_file_path}" -t 1 -f null -'
        command = shlex.split(ffmpeg_cmd)
        
        logger.info("Running FFmpeg validation...")
        
        # Execute FFmpeg for validation
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30  # 30 second timeout for validation
        )
        
        # Clean up temporary file
        try:
            subprocess.run(['rm', '-f', local_file_path], check=False)
        except Exception:
            pass  # Ignore cleanup errors
        
        if result.returncode == 0:
            logger.info("Video validation successful")
            return {
                'valid': True,
                'message': 'Video file is valid and readable by FFmpeg'
            }
        else:
            logger.error(f"Video validation failed: {result.stderr}")
            return {
                'valid': False,
                'error': result.stderr,
                'message': 'Video file validation failed'
            }
            
    except subprocess.TimeoutExpired:
        logger.error(f"Video validation timeout for {object_key}")
        return {
            'valid': False,
            'error': 'Validation timeout',
            'message': 'Video validation timed out'
        }
    except Exception as e:
        logger.error(f"Error validating video file {object_key}: {str(e)}")
        return {
            'valid': False,
            'error': str(e),
            'message': 'Video validation error'
        }


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
    Extract video metadata using FFmpeg.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Dict containing video metadata
    """
    try:
        logger.info(f"Extracting metadata for {bucket_name}/{object_key}")
        
        # Download file to /tmp for FFprobe analysis
        local_file_path = f"/tmp/{object_key.split('/')[-1]}"
        
        try:
            s3_client.download_file(bucket_name, object_key, local_file_path)
            logger.info(f"Downloaded {object_key} to {local_file_path}")
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            return {'error': f'Failed to download file: {str(e)}'}
        
        # FFmpeg command to extract metadata
        # Use -f null to avoid creating output, just analyze the input
        ffmpeg_cmd = f'{FFMPEG_PATH} -i "{local_file_path}" -f null -'
        command = shlex.split(ffmpeg_cmd)
        
        logger.info("Running FFmpeg for metadata extraction...")
        
        # Execute FFmpeg (metadata goes to stderr)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        # Clean up temporary file
        try:
            subprocess.run(['rm', '-f', local_file_path], check=False)
        except Exception:
            pass  # Ignore cleanup errors
        
        # FFmpeg outputs metadata to stderr, even on success
        # We'll parse the text output instead of JSON
        metadata_text = result.stderr
        
        if result.returncode not in [0, 1]:  # FFmpeg returns 1 when using -f null, but still provides metadata
            logger.error(f"FFmpeg failed with return code {result.returncode}")
            logger.error(f"FFmpeg stderr: {result.stderr}")
            return {
                'error': f'FFmpeg failed: {result.stderr}',
                'returncode': result.returncode
            }
        
        # Parse FFmpeg output to extract metadata
        extracted_metadata = parse_ffmpeg_output(metadata_text, object_key)
        return extracted_metadata
        
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout for {object_key}")
        return {'error': 'FFmpeg timeout', 'timeout': True}
    except Exception as e:
        logger.error(f"Error extracting metadata for {object_key}: {str(e)}")
        return {'error': str(e)}


def parse_ffmpeg_output(metadata_text: str, object_key: str) -> Dict[str, Any]:
    """
    Parse FFmpeg text output to extract video metadata.
    
    Args:
        metadata_text: FFmpeg stderr output containing metadata
        object_key: S3 object key for filename reference
        
    Returns:
        Dict containing parsed metadata
    """
    import re
    
    try:
        logger.info("Parsing FFmpeg metadata output...")
        
        # Initialize metadata structure
        extracted_metadata = {
            'file_info': {
                'filename': object_key,
                'format_name': None,
                'duration': 0.0,
                'size': 0,
                'bit_rate': 0
            },
            'video_info': None,
            'audio_info': None,
            'raw_output': metadata_text
        }
        
        # Parse duration (format: Duration: HH:MM:SS.ss)
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', metadata_text)
        if duration_match:
            hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            extracted_metadata['file_info']['duration'] = total_seconds
        
        # Parse bitrate (format: bitrate: XXXX kb/s)
        bitrate_match = re.search(r'bitrate: (\d+) kb/s', metadata_text)
        if bitrate_match:
            extracted_metadata['file_info']['bit_rate'] = int(bitrate_match.group(1)) * 1000  # Convert to bps
        
        # Parse container format
        format_match = re.search(r'Input #0, ([^,]+)', metadata_text)
        if format_match:
            extracted_metadata['file_info']['format_name'] = format_match.group(1)
        
        # Parse video stream info (format: Stream #0:0: Video: codec, format, WIDTHxHEIGHT, fps)
        video_match = re.search(r'Stream #\d+:\d+.*Video: ([^,]+)(?:,\s*([^,]+))?(?:,\s*(\d+)x(\d+))?.*?(\d+(?:\.\d+)?) fps', metadata_text)
        if video_match:
            codec = video_match.group(1)
            pixel_format = video_match.group(2) if video_match.group(2) else None
            width = int(video_match.group(3)) if video_match.group(3) else 0
            height = int(video_match.group(4)) if video_match.group(4) else 0
            fps = float(video_match.group(5)) if video_match.group(5) else 0
            
            extracted_metadata['video_info'] = {
                'codec_name': codec,
                'width': width,
                'height': height,
                'fps': fps,
                'pix_fmt': pixel_format
            }
        
        # Parse audio stream info (format: Stream #0:1: Audio: codec, sample_rate Hz, channels)
        audio_match = re.search(r'Stream #\d+:\d+.*Audio: ([^,]+)(?:,\s*(\d+) Hz)?(?:,\s*([^,]+))?', metadata_text)
        if audio_match:
            codec = audio_match.group(1)
            sample_rate = int(audio_match.group(2)) if audio_match.group(2) else 0
            channels_info = audio_match.group(3) if audio_match.group(3) else None
            
            # Extract channel count from channel info (e.g., "stereo", "mono", "5.1")
            channels = 0
            if channels_info:
                if 'stereo' in channels_info.lower():
                    channels = 2
                elif 'mono' in channels_info.lower():
                    channels = 1
                elif '5.1' in channels_info:
                    channels = 6
                else:
                    # Try to extract number from string
                    channel_match = re.search(r'(\d+)', channels_info)
                    if channel_match:
                        channels = int(channel_match.group(1))
            
            extracted_metadata['audio_info'] = {
                'codec_name': codec,
                'sample_rate': sample_rate,
                'channels': channels,
                'channel_layout': channels_info
            }
        
        logger.info(f"Successfully parsed FFmpeg metadata for {object_key}")
        logger.info(f"Video duration: {extracted_metadata['file_info']['duration']} seconds")
        if extracted_metadata['video_info']:
            logger.info(f"Video resolution: {extracted_metadata['video_info']['width']}x{extracted_metadata['video_info']['height']}")
        if extracted_metadata['audio_info']:
            logger.info(f"Audio: {extracted_metadata['audio_info']['sample_rate']}Hz, {extracted_metadata['audio_info']['channels']} channels")
        
        return extracted_metadata
        
    except Exception as e:
        logger.error(f"Error parsing FFmpeg output: {str(e)}")
        return {
            'error': f'Failed to parse FFmpeg output: {str(e)}',
            'raw_output': metadata_text
        }


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