import json
import boto3
import subprocess
import shlex
import os
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError
from typing import Dict, Any, List
import logging
from urllib.parse import unquote_plus
from summarize import summarize_clip
from job_status_update import create_job_status_record, update_job_status_record
from segment_caption_update import save_batch_segment_captions

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

# FFmpeg path in Lambda layer
FFMPEG_PATH = '/opt/bin/ffmpeg'

# Get bucket names from environment variables
SEGMENTS_BUCKET_NAME = os.environ.get('SEGMENTS_BUCKET_NAME')


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
        logger.info("=== S3 Event Processor - Processing Rules ===")
        logger.info("✓ ONLY process files matching: videos/{jobId}/original/{filename}")
        logger.info("✗ SKIP files matching: videos/{jobId}/segments/{filename}")
        logger.info("✗ SKIP files matching: videos/{jobId}/thumbnails/{filename}")
        logger.info("✗ SKIP files matching: videos/{jobId}/metadata/{filename}")
        logger.info("✗ SKIP files matching: videos/{jobId}/previews/{filename}")
        logger.info("=== End Processing Rules ===")
        
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
                logger.info(f"Skipping non-video file (not in videos/ prefix): {object_key}")
                continue
            
            # Extract job ID from the S3 key path
            # Expected format: videos/{jobId}/original/{filename}
            # Do NOT process: videos/{jobId}/segments/{filename} or videos/{jobId}/thumbnails/{filename}
            path_parts = object_key.split('/')
            if len(path_parts) < 4:
                logger.warning(f"Unexpected S3 key format (insufficient path parts): {object_key}")
                logger.warning(f"Expected format: videos/{{jobId}}/original/{{filename}}, got {len(path_parts)} parts: {path_parts}")
                continue
            
            # Ensure we have exactly the expected structure
            if len(path_parts) != 4:
                logger.warning(f"Unexpected S3 key format (too many path parts): {object_key}")
                logger.warning(f"Expected format: videos/{{jobId}}/original/{{filename}}, got {len(path_parts)} parts: {path_parts}")
                continue
            
            job_id = path_parts[1]
            file_category = path_parts[2]  # Should be 'original'
            filename = path_parts[3]
            
            # Validate job_id is not empty
            if not job_id or job_id.strip() == '':
                logger.warning(f"Invalid job_id in S3 key: {object_key}")
                continue
            
            # Validate filename is not empty and has an extension
            if not filename or filename.strip() == '' or '.' not in filename:
                logger.warning(f"Invalid filename in S3 key: {object_key}")
                continue
            
            # CRITICAL: Only process files in the 'original' directory to avoid infinite loops
            # This prevents reprocessing of:
            # - segments: videos/{jobId}/segments/{filename}
            # - thumbnails: videos/{jobId}/thumbnails/{filename}  
            # - metadata: videos/{jobId}/metadata/{filename}
            # - previews: videos/{jobId}/previews/{filename}
            if file_category != 'original':
                logger.info(f"Skipping non-original file (category: '{file_category}'): {object_key}")
                logger.info("Only processing files in 'videos/{jobId}/original/' directory")
                continue
            
            # Additional safety check: ensure we're processing a video file
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v']
            if not any(filename.lower().endswith(ext) for ext in video_extensions):
                logger.info(f"Skipping non-video file (extension check): {object_key}")
                continue
            
            logger.info(f"✓ Processing original video file: {filename} (job_id: {job_id})")
            
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
        
        # Create upload timestamp for job tracking
        upload_timestamp = last_modified.isoformat() if last_modified else None
        if not upload_timestamp:
            from datetime import datetime
            upload_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Create initial job status record
        initial_metadata = {
            'filename': filename,
            's3_uri': f"s3://{bucket_name}/{object_key}",
            'size': file_size,
            'content_type': content_type,
            'duration': 0,  # Will be updated after metadata extraction
            'resolution': 'unknown',
            'video_codec': 'unknown'
        }
        
        create_job_status_record(job_id, upload_timestamp, initial_metadata)
        
        # TODO: Implement video processing logic
        # This is where you would add your video processing steps:
        
        # Step 1: Validate video file format and integrity
        logger.info("Step 1: Validating video file format and integrity...")
        validation_result = validate_video_file(bucket_name, object_key)
        
        if not validation_result.get('valid', False):
            logger.error(f"Video validation failed: {validation_result.get('message', 'Unknown error')}")
            
            # Update job status to failed
            update_job_status_record(job_id, upload_timestamp, 'failed', {
                'errorMessage': validation_result.get('error', 'Validation failed')
            })
            
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
        
        # Update job status with video metadata
        if not metadata.get('error'):
            video_duration = metadata.get('file_info', {}).get('duration', 0)
            video_info = metadata.get('video_info', {})
            resolution = f"{video_info.get('width', 0)}x{video_info.get('height', 0)}" if video_info else 'unknown'
            video_codec = video_info.get('codec_name', 'unknown') if video_info else 'unknown'
            
            update_job_status_record(job_id, upload_timestamp, 'pending', {
                'videoDuration': video_duration,
                'metadata': {
                    'resolution': resolution,
                    'codec': video_codec,
                    'contentType': content_type
                }
            })
        
        # Step 4: Split video into segments using FFmpeg's native segmentation
        logger.info("Step 4: Splitting video into segments using FFmpeg's native segmentation...")
        segment_result = split_video_into_segments(bucket_name, object_key, job_id)
        
        if segment_result.get('error'):
            logger.error(f"Video splitting failed: {segment_result.get('error')}")
            update_job_status_record(job_id, upload_timestamp, 'failed', {
                'error': f"Video splitting failed: {segment_result.get('error')}"
            })
        else:
            logger.info(f"Successfully created {len(segment_result.get('segments', []))} video segments")
            # Update job status with segment count
            update_job_status_record(job_id, upload_timestamp, 'pending', {
                'totalSegments': len(segment_result.get('segments', [])),
                'processedSegments': 0,
                'segments': segment_result.get('segments', [])
            })
        
        # Step 5: Summarize video segments using Bedrock Nova
        summarization_result = {'success': False, 'total_segments': 0, 'processed_segments': 0, 'results': []}
        if not segment_result.get('error') and segment_result.get('segments'):
            logger.info("Step 5: Summarizing video segments using Amazon Bedrock Nova...")
            summarization_result = summarize_video_segments(
                job_id=job_id, 
                uploaded_segments=segment_result.get('segments', []),
                segment_duration=segment_result.get('segment_duration', 5)
            )
            
            if summarization_result.get('success'):
                logger.info(f"Successfully summarized {summarization_result.get('successful_segments', 0)}/{summarization_result.get('total_segments', 0)} segments")
                # Update job status to done with final results
                update_job_status_record(job_id, upload_timestamp, 'done', {
                    'processedSegments': summarization_result.get('successful_segments', 0),
                    'summarizationResults': summarization_result.get('results', []),
                    'completedAt': int(time.time() * 1000)
                })
            else:
                logger.error(f"Video summarization failed: {summarization_result.get('error', 'Unknown error')}")
                update_job_status_record(job_id, upload_timestamp, 'failed', {
                    'error': f"Video summarization failed: {summarization_result.get('error', 'Unknown error')}"
                })
        else:
            logger.info("Step 5: Skipping video summarization (no segments to process)")
            if segment_result.get('error'):
                # Already updated in Step 4, don't update again
                pass
            else:
                # No segments but no error - mark as done
                update_job_status_record(job_id, upload_timestamp, 'done', {
                    'processedSegments': 0,
                    'completedAt': int(time.time() * 1000),
                    'note': 'No segments to process'
                })
        
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
        logger.info("✓ 4. Video split into segments")
        logger.info(f"✓ 5. Video summarization using Bedrock Nova ({'successful' if summarization_result.get('success') else 'failed'})")
        logger.info("TODO: 6. Generate video thumbnails")
        logger.info("TODO: 7. Generate preview clips")
        logger.info("TODO: 8. Update job status")
        logger.info("TODO: 9. Content validation")
        
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
            'segmentation': {
                'success': not segment_result.get('error'),
                'total_segments': segment_result.get('total_segments', 0),
                'uploaded_segments': segment_result.get('uploaded_segments', 0),
                'segment_duration': segment_result.get('segment_duration', 5),
                'segments': segment_result.get('segments', []),
                'error': segment_result.get('error')
            },
            'summarization': {
                'success': summarization_result.get('success', False),
                'total_segments': summarization_result.get('total_segments', 0),
                'processed_segments': summarization_result.get('processed_segments', 0),
                'successful_segments': summarization_result.get('successful_segments', 0),
                'failed_segments': summarization_result.get('failed_segments', 0),
                'results': summarization_result.get('results', []),
                'error': summarization_result.get('error')
            },
            'processingSteps': [
                {'step': 'file_validation', 'status': 'completed'},
                {'step': 'metadata_extraction', 'status': 'completed'},
                {'step': 'metadata_logging', 'status': 'completed'},
                {'step': 'video_segmentation', 'status': 'completed' if not segment_result.get('error') else 'failed'},
                {'step': 'video_summarization', 'status': 'completed' if summarization_result.get('success') else 'failed'},
                {'step': 'thumbnail_generation', 'status': 'pending'},
                {'step': 'preview_generation', 'status': 'pending'},
                {'step': 'status_update', 'status': 'pending'},
                {'step': 'content_validation', 'status': 'pending'}
            ]
        }
        
        logger.info(f"Processing completed for {object_key}")
        if not metadata.get('error'):
            logger.info(f"Video metadata: {processing_result['metadata']['duration']:.2f}s, {processing_result['metadata']['resolution']}, {processing_result['metadata']['video_codec']}")
        if not segment_result.get('error'):
            logger.info(f"Video segmentation: {segment_result.get('uploaded_segments', 0)}/{segment_result.get('total_segments', 0)} segments uploaded")
        if summarization_result.get('success'):
            logger.info(f"Video summarization: {summarization_result.get('successful_segments', 0)}/{summarization_result.get('total_segments', 0)} segments summarized")
        
        return processing_result
        
    except Exception as e:
        logger.error(f"Error processing video upload {object_key}: {str(e)}")
        
        # Update job status to failed on any unhandled exception
        try:
            update_job_status_record(job_id, upload_timestamp, 'failed', {
                'error': f"Unexpected error: {str(e)}"
            })
        except Exception as status_error:
            logger.error(f"Failed to update job status after error: {status_error}")
        
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


def split_video_into_segments(bucket_name: str, object_key: str, job_id: str, segment_duration: int = 5) -> Dict[str, Any]:
    """
    Split video into segments using FFmpeg's native segmentation and upload to S3 segments bucket.
    
    Args:
        bucket_name: S3 bucket name containing the original video
        object_key: S3 object key of the original video
        job_id: Analysis job ID
        segment_duration: Duration of each segment in seconds (default: 5)
        
    Returns:
        Dict containing segmentation results with segments uploaded to the dedicated segments bucket
    """
    try:
        logger.info(f"Starting video segmentation for {bucket_name}/{object_key}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video to temporary directory
            filename = Path(object_key).name
            local_video_path = os.path.join(temp_dir, filename)
            
            try:
                s3_client.download_file(bucket_name, object_key, local_video_path)
                logger.info(f"Downloaded video to {local_video_path}")
            except Exception as e:
                logger.error(f"Failed to download video: {str(e)}")
                return {'error': f'Failed to download video: {str(e)}'}
            
            # Get video duration first
            duration = get_video_duration_ffmpeg(local_video_path)
            if duration <= 0:
                logger.error("Could not determine video duration")
                return {'error': 'Could not determine video duration'}
            
            # Calculate expected number of segments
            num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)
            logger.info(f"Video duration: {duration:.2f}s, expecting ~{num_segments} segments of {segment_duration}s each")
            
            # Create segments directory
            segments_dir = os.path.join(temp_dir, "segments")
            os.makedirs(segments_dir, exist_ok=True)
            
            # Use FFmpeg's segment muxer for efficient video splitting
            segment_pattern = os.path.join(segments_dir, "%d.mp4")
            
            # FFmpeg command using segment muxer with optimized settings
            ffmpeg_cmd = [
                FFMPEG_PATH,
                '-i', local_video_path,
                '-c:v', 'libx264',  # Video codec
                '-preset', 'ultrafast',  # Fastest encoding preset for Lambda
                '-crf', '23',  # Good quality compression
                '-g', '30',  # GOP size for consistent keyframes
                '-keyint_min', '30',  # Minimum keyframe interval
                '-sc_threshold', '0',  # Disable scene change detection
                '-f', 'segment',  # Use segment muxer
                '-segment_time', str(segment_duration),  # Segment duration
                '-reset_timestamps', '1',  # Reset timestamps for each segment
                '-movflags', '+faststart',  # Move metadata to beginning for faster loading
                '-an',  # Remove audio (not needed for video analysis)
                '-y',  # Overwrite output files
                segment_pattern
            ]
            
            logger.info(f"Running FFmpeg segmentation: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg segmentation
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minute timeout for entire segmentation
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg segmentation failed: {result.stderr}")
                return {'error': f'FFmpeg segmentation failed: {result.stderr}'}
            
            # Debug: List all files created in segments directory
            try:
                all_files = os.listdir(segments_dir)
                logger.info(f"Files in segments directory after FFmpeg: {all_files}")
            except Exception as e:
                logger.error(f"Could not list segments directory: {str(e)}")
            
            # Find all created segment files
            segment_files = []
            for file in os.listdir(segments_dir):
                if file.endswith('.mp4') and file[:-4].isdigit():
                    segment_files.append(os.path.join(segments_dir, file))
            
            # Sort by segment number
            segment_files.sort(key=lambda x: int(Path(x).stem))
            
            if not segment_files:
                logger.error("No segments were created by FFmpeg")
                return {'error': 'No segments were created by FFmpeg'}
            
            logger.info(f"FFmpeg created {len(segment_files)} segments: {[Path(f).name for f in segment_files]}")
            
            logger.info(f"Successfully created {len(segment_files)} segments, uploading to S3...")
            
            # Validate all segment files exist before uploading
            missing_files = []
            for segment_path in segment_files:
                if not os.path.exists(segment_path):
                    missing_files.append(Path(segment_path).name)
            
            if missing_files:
                logger.error(f"Missing segment files before upload: {missing_files}")
                return {'error': f'Missing segment files: {missing_files}'}
            
            # Upload segments to S3 segments bucket with concurrent uploads
            uploaded_segments = []
            upload_tasks = []
            
            # Get segments bucket name from environment
            segments_bucket = SEGMENTS_BUCKET_NAME
            if not segments_bucket:
                logger.error("SEGMENTS_BUCKET_NAME environment variable not set")
                return {'error': 'Segments bucket not configured'}
            
            for segment_path in segment_files:
                segment_filename = Path(segment_path).name
                segment_key = f"videos/{job_id}/segments/{segment_filename}"
                upload_tasks.append((segment_path, segments_bucket, segment_key))
            
            # Use ThreadPoolExecutor for concurrent uploads
            max_workers = min(5, len(upload_tasks))  # Limit concurrent uploads in Lambda
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all upload tasks
                future_to_task = {
                    executor.submit(upload_segment_to_s3, task): task 
                    for task in upload_tasks
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_task):
                    try:
                        s3_url = future.result()
                        uploaded_segments.append(s3_url)
                        logger.info(f"✓ Uploaded: {Path(s3_url).name}")
                    except Exception as e:
                        task = future_to_task[future]
                        logger.error(f"✗ Upload failed for {Path(task[0]).name}: {str(e)}")
                        # Continue with other uploads even if one fails
            
            logger.info(f"Segmentation completed: {len(uploaded_segments)}/{len(segment_files)} segments uploaded successfully")
            
            return {
                'success': True,
                'segments': uploaded_segments,
                'total_segments': len(segment_files),
                'uploaded_segments': len(uploaded_segments),
                'segment_duration': segment_duration,
                'video_duration': duration
            }
            
    except subprocess.TimeoutExpired:
        logger.error(f"Video segmentation timeout for {object_key}")
        return {'error': 'Video segmentation timeout'}
    except Exception as e:
        logger.error(f"Error splitting video {object_key}: {str(e)}")
        return {'error': str(e)}


def get_video_duration_ffmpeg(video_path: str) -> float:
    """
    Get video duration using FFmpeg.
    
    Args:
        video_path: Local path to video file
        
    Returns:
        Duration in seconds, or 0 if failed
    """
    try:
        # Use FFmpeg to get duration (output goes to stderr)
        ffmpeg_cmd = [FFMPEG_PATH, '-i', video_path, '-f', 'null', '-']
        
        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        # Parse duration from stderr output
        import re
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', result.stderr)
        if duration_match:
            hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            return total_seconds
        
        logger.warning("Could not parse duration from FFmpeg output")
        return 0.0
        
    except Exception as e:
        logger.error(f"Error getting video duration: {str(e)}")
        return 0.0


def upload_segment_to_s3(task_args) -> str:
    """
    Upload a single segment to S3. Used for thread pool execution.
    
    Args:
        task_args: Tuple of (segment_path, bucket_name, segment_key)
        
    Returns:
        S3 URL of uploaded segment
    """
    segment_path, bucket_name, segment_key = task_args
    
    try:
        # Verify file exists before attempting upload
        if not os.path.exists(segment_path):
            raise FileNotFoundError(f"Segment file does not exist: {segment_path}")
        
        # Log file size for debugging
        file_size = os.path.getsize(segment_path)
        logger.info(f"Uploading {Path(segment_path).name} ({file_size} bytes) to S3")
        
        s3_client.upload_file(segment_path, bucket_name, segment_key)
        return f"s3://{bucket_name}/{segment_key}"
    except Exception as e:
        logger.error(f"Failed to upload segment {Path(segment_path).name}: {str(e)}")
        raise


def summarize_video_segments(job_id: str, uploaded_segments: List[str], segment_duration: int = 5) -> Dict[str, Any]:
    """
    Process all video segments through Bedrock for summarization.
    
    Args:
        job_id: Analysis job ID
        uploaded_segments: List of S3 URLs for uploaded segments
        segment_duration: Duration of each segment in seconds
        
    Returns:
        Dict containing summarization results
    """
    try:
        logger.info(f"Starting video summarization for {len(uploaded_segments)} segments")
        
        # Extract segment indices from URLs and create mapping with calculated start times
        # URL format: s3://bucket/videos/{job_id}/segments/{segment_index}.mp4 (0.mp4, 1.mp4, 2.mp4, etc.)
        segment_mapping = {}  # start_time -> s3_uri
        for segment_url in uploaded_segments:
            try:
                # Extract segment index from filename
                filename = Path(segment_url).name  # e.g., "2.mp4"
                segment_index = int(filename.split('.')[0])  # e.g., 2
                # Calculate start time from segment index, file name starts from 1
                start_time = segment_index * segment_duration  # e.g. second file (2 - 1) * 5 = 5
                segment_mapping[start_time] = segment_url
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse start time from segment URL {segment_url}: {str(e)}")
                continue
        
        # Sort segments by start time
        segment_times = sorted(segment_mapping.keys())
        
        if not segment_times:
            logger.error("No valid segment times found")
            return {
                'success': False,
                'error': 'No valid segment times found',
                'total_segments': len(uploaded_segments),
                'processed_segments': 0,
                'results': []
            }
        
        logger.info(f"Processing {len(segment_times)} segments: {segment_times}")
        
        # Process segments concurrently (but limit concurrency for Lambda)
        results = []
        max_workers = min(2, len(segment_times))  # Limit concurrent Bedrock requests to 2
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all summarization tasks
            future_to_time = {
                executor.submit(summarize_clip, segment_mapping[start_time], job_id, start_time): start_time 
                for start_time in segment_times
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_time):
                start_time = future_to_time[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result["status"] == "success":
                        logger.info(f"✓ Summarized segment {result['start_time']}: {result['caption']}")
                        # Print detailed inference result
                        token_usage = result.get('token_usage', {})
                        print(f"🔍 BEDROCK INFERENCE RESULT - Segment {result['start_time']}s:")
                        print(f"   Job ID: {result['job_id']}")
                        print(f"   Caption: {result['caption']}")
                        print(f"   Status: {result['status']}")
                        print(f"   Tokens: {token_usage.get('input_tokens', 0)} input + {token_usage.get('output_tokens', 0)} output = {token_usage.get('total_tokens', 0)} total")
                        print("---")
                    else:
                        logger.error(f"✗ Failed to summarize segment {result['start_time']}: {result.get('error', 'Unknown error')}")
                        print(f"❌ BEDROCK INFERENCE FAILED - Segment {result['start_time']}s:")
                        print(f"   Job ID: {result['job_id']}")
                        print(f"   Error: {result.get('error', 'Unknown error')}")
                        print(f"   Status: {result['status']}")
                        print("---")
                except Exception as e:
                    logger.error(f"✗ Exception summarizing segment {start_time}: {str(e)}")
                    results.append({
                        "job_id": job_id,
                        "start_time": start_time,
                        "caption": None,
                        "status": "error",
                        "error": str(e),
                    })
        
        # Sort results by start time
        results.sort(key=lambda x: x["start_time"])
        
        success_count = sum(1 for r in results if r["status"] == "success")
        
        logger.info(f"Video summarization completed: {success_count}/{len(results)} segments processed successfully")
        
        # Print all results for now (as requested)
        print("\n" + "="*80)
        print("🎬 VIDEO SEGMENT SUMMARIES - BEDROCK INFERENCE RESULTS")
        print("="*80)
        for result in results:
            if result["status"] == "success":
                print(f"⏱️  Segment {result['start_time']}s → {result['caption']}")
                logger.info(f"Segment {result['start_time']}s: {result['caption']}")
            else:
                print(f"❌ Segment {result['start_time']}s → ERROR: {result.get('error', 'Unknown error')}")
                logger.info(f"Segment {result['start_time']}s: ERROR - {result.get('error', 'Unknown error')}")
        print("="*80)
        print(f"📊 Summary: {success_count} successful, {len(results) - success_count} failed out of {len(results)} total segments")
        print("="*80 + "\n")
        
        # Save inference results to DynamoDB VideoAnalysisTable
        logger.info("Saving segment captions to DynamoDB VideoAnalysisTable...")
        save_result = save_batch_segment_captions(results)
        
        if save_result['success']:
            logger.info(f"✓ Successfully saved {save_result['saved_count']} segment captions to DynamoDB")
        else:
            logger.error(f"✗ Failed to save segment captions to DynamoDB: {save_result['failed_count']} failures")
            for error in save_result.get('errors', []):
                logger.error(f"  - {error}")
        
        return {
            'success': True,
            'total_segments': len(segment_times),
            'processed_segments': len(results),
            'successful_segments': success_count,
            'failed_segments': len(results) - success_count,
            'results': results,
            'dynamodb_save_result': save_result
        }
        
    except Exception as e:
        logger.error(f"Error in video summarization workflow: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'total_segments': len(uploaded_segments) if uploaded_segments else 0,
            'processed_segments': 0,
            'results': []
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