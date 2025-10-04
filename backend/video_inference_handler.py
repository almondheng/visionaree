import json
import logging
import base64
import tempfile
import os
import subprocess
import shlex
from typing import Dict, Any, Optional
from summarize import summarize_clip

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# FFmpeg path in Lambda layer
FFMPEG_PATH = '/opt/bin/ffmpeg'

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function to handle direct video segment uploads and run immediate Bedrock inference.
    
    This function accepts video files via API Gateway (multipart/form-data or base64),
    optionally re-encodes them for better compatibility, and runs Bedrock inference
    without storing the video in S3.
    
    Args:
        event: API Gateway event containing the video file
        context: Lambda context object
        
    Returns:
        Dict containing inference results
    """
    
    try:
        logger.info("=== Direct Video Inference Handler ===")
        logger.info("Processing direct video upload for immediate Bedrock inference")
        
        # Parse the request body
        if not event.get('body'):
            return create_error_response(400, "Request body is required")
        
        # Handle both base64 encoded and regular body
        is_base64_encoded = event.get('isBase64Encoded', False)
        body = event['body']
        
        if is_base64_encoded:
            try:
                body = base64.b64decode(body)
            except Exception as e:
                logger.error(f"Failed to decode base64 body: {str(e)}")
                return create_error_response(400, "Invalid base64 encoded body")
        
        # Extract content type to determine how to parse the video
        headers = event.get('headers', {})
        content_type = headers.get('content-type', headers.get('Content-Type', ''))
        
        logger.info(f"Content-Type: {content_type}")
        logger.info(f"Body size: {len(body)} bytes")
        logger.info(f"Is Base64 encoded: {is_base64_encoded}")
        
        # Handle different input formats
        video_data = None
        original_filename = None
        
        if content_type.startswith('multipart/form-data'):
            # Parse multipart form data
            video_data, original_filename = parse_multipart_video(body, content_type)
        elif content_type.startswith('video/') or content_type.startswith('application/octet-stream'):
            # Direct binary video upload
            video_data = body if isinstance(body, bytes) else body.encode()
            original_filename = headers.get('x-filename', 'video.mp4')
        else:
            return create_error_response(400, f"Unsupported content type: {content_type}")
        
        if not video_data:
            return create_error_response(400, "No video data found in request")
        
        logger.info(f"Extracted video data: {len(video_data)} bytes, filename: {original_filename}")
        
        # Validate file size (limit to 50MB for Lambda)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(video_data) > max_size:
            return create_error_response(413, f"File too large. Maximum size is {max_size // (1024*1024)}MB")
        
        # Process the video and run Bedrock inference
        inference_result = process_video_for_inference(video_data, original_filename)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps(inference_result, indent=2)
        }
        
    except Exception as e:
        logger.error(f"Error processing direct video inference: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")


def parse_multipart_video(body_bytes: bytes, content_type: str) -> tuple[Optional[bytes], Optional[str]]:
    """
    Parse multipart/form-data to extract video file.
    
    Args:
        body_bytes: Raw request body bytes
        content_type: Content-Type header value
        
    Returns:
        Tuple of (video_data, filename) or (None, None) if not found
    """
    try:
        # Extract boundary from content-type
        boundary = None
        if 'boundary=' in content_type:
            boundary = content_type.split('boundary=')[1].split(';')[0]
        
        if not boundary:
            logger.error("No boundary found in multipart content-type")
            return None, None
        
        boundary_bytes = f'--{boundary}'.encode()
        
        # Split by boundary
        parts = body_bytes.split(boundary_bytes)
        
        for part in parts:
            if b'Content-Disposition:' in part and b'filename=' in part:
                # Found a file part
                try:
                    # Extract filename
                    filename = None
                    lines = part.split(b'\r\n')
                    for line in lines:
                        if b'Content-Disposition:' in line and b'filename=' in line:
                            # Parse filename from Content-Disposition header
                            line_str = line.decode('utf-8', errors='ignore')
                            if 'filename="' in line_str:
                                filename = line_str.split('filename="')[1].split('"')[0]
                            elif 'filename=' in line_str:
                                filename = line_str.split('filename=')[1].split(';')[0].split(' ')[0]
                            break
                    
                    # Extract file data (after double CRLF)
                    if b'\r\n\r\n' in part:
                        file_data = part.split(b'\r\n\r\n', 1)[1]
                        # Remove trailing boundary markers
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                        
                        logger.info(f"Found video file: {filename}, size: {len(file_data)} bytes")
                        return file_data, filename
                        
                except Exception as e:
                    logger.error(f"Error parsing multipart file: {str(e)}")
                    continue
        
        logger.error("No video file found in multipart data")
        return None, None
        
    except Exception as e:
        logger.error(f"Error parsing multipart data: {str(e)}")
        return None, None


def process_video_for_inference(video_data: bytes, filename: str) -> Dict[str, Any]:
    """
    Process video data and run Bedrock inference.
    
    Args:
        video_data: Raw video file bytes
        filename: Original filename
        
    Returns:
        Dict containing inference results
    """
    
    temp_dir = None
    try:
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Save video to temporary file
        input_path = os.path.join(temp_dir, f"input_{filename}")
        with open(input_path, 'wb') as f:
            f.write(video_data)
        
        logger.info(f"Saved video to temporary file: {input_path}")
        
        # Get basic video info for response (optional, for debugging)
        video_info = get_simple_video_info(input_path)
        
        # Use original video directly - assume it's already in correct format
        inference_path = input_path
        logger.info("Using original video format directly (no re-encoding)")
        
        # Upload video to a temporary S3 location for Bedrock
        # We need S3 URI for Bedrock, so create a temporary upload
        temp_s3_uri = upload_temp_video_to_s3(inference_path)
        
        if not temp_s3_uri:
            return {
                'success': False,
                'error': 'Failed to upload video for Bedrock processing'
            }
        
        try:
            # Run Bedrock inference
            logger.info(f"Running Bedrock inference on video: {temp_s3_uri}")
            
            inference_result = summarize_clip(
                s3_uri=temp_s3_uri,
                job_id="direct-inference",
                start_time=0
            )
            
            # Clean up temporary S3 object
            # disable cleanup for faster response
            # cleanup_temp_s3_object(temp_s3_uri)
            
            # Prepare clean response with only essential data
            response = {
                'success': True,
                'filename': filename,
                'file_size': video_info.get('file_size', 0),
                'caption': inference_result.get('caption'),
                'status': inference_result.get('status')
            }
            
            # Only include error if there was one
            if inference_result.get('error'):
                response['error'] = inference_result.get('error')
            
            return response
            
        except Exception as e:
            # Make sure to clean up S3 object even if inference fails
            cleanup_temp_s3_object(temp_s3_uri)
            raise
        
    except Exception as e:
        logger.error(f"Error processing video for inference: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info("Cleaned up temporary directory")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {str(e)}")


def get_simple_video_info(video_path: str) -> Dict[str, Any]:
    """
    Get basic video information without detailed analysis.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dict containing basic video info
    """
    try:
        file_size = os.path.getsize(video_path)
        logger.info(f"Video file size: {file_size} bytes")
        
        return {
            'file_size': file_size,
            'format': 'video',
            'note': 'Using original format (no detailed analysis for speed)'
        }
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return {
            'file_size': 0,
            'format': 'unknown',
            'error': str(e)
        }


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Get video information using FFmpeg.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dict containing video metadata
    """
    try:
        # Use FFprobe to get detailed video information
        cmd = [
            FFMPEG_PATH.replace('ffmpeg', 'ffprobe'),  # Use ffprobe if available
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        # Fallback to FFmpeg if ffprobe not available
        if not os.path.exists(FFMPEG_PATH.replace('ffmpeg', 'ffprobe')):
            cmd = [FFMPEG_PATH, '-i', video_path, '-f', 'null', '-']
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if 'ffprobe' in cmd[0] and result.returncode == 0:
            # Parse JSON output from ffprobe
            try:
                probe_data = json.loads(result.stdout)
                format_info = probe_data.get('format', {})
                video_stream = next((s for s in probe_data.get('streams', []) if s.get('codec_type') == 'video'), {})
                
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'format': format_info.get('format_name', 'unknown'),
                    'codec': video_stream.get('codec_name', 'unknown'),
                    'width': video_stream.get('width', 0),
                    'height': video_stream.get('height', 0),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream.get('r_frame_rate') else 0,
                    'bitrate': int(format_info.get('bit_rate', 0)) if format_info.get('bit_rate') else 0
                }
            except Exception as e:
                logger.error(f"Error parsing ffprobe output: {str(e)}")
        
        # Fallback: parse FFmpeg stderr output
        return parse_basic_video_info(result.stderr)
        
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return {
            'duration': 0,
            'format': 'unknown',
            'codec': 'unknown',
            'width': 0,
            'height': 0,
            'fps': 0,
            'bitrate': 0,
            'error': str(e)
        }


def parse_basic_video_info(ffmpeg_output: str) -> Dict[str, Any]:
    """Parse basic video info from FFmpeg stderr output."""
    import re
    
    info = {
        'duration': 0,
        'format': 'unknown',
        'codec': 'unknown',
        'width': 0,
        'height': 0,
        'fps': 0,
        'bitrate': 0
    }
    
    try:
        # Parse duration
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', ffmpeg_output)
        if duration_match:
            h, m, s, cs = map(int, duration_match.groups())
            info['duration'] = h * 3600 + m * 60 + s + cs / 100
        
        # Parse codec and resolution
        video_match = re.search(r'Video: ([^,]+).*?(\d+)x(\d+).*?(\d+(?:\.\d+)?) fps', ffmpeg_output)
        if video_match:
            info['codec'] = video_match.group(1)
            info['width'] = int(video_match.group(2))
            info['height'] = int(video_match.group(3))
            info['fps'] = float(video_match.group(4))
        
        # Parse format
        format_match = re.search(r'Input #0, ([^,]+)', ffmpeg_output)
        if format_match:
            info['format'] = format_match.group(1)
            
    except Exception as e:
        logger.error(f"Error parsing basic video info: {str(e)}")
    
    return info



def upload_temp_video_to_s3(video_path: str) -> Optional[str]:
    """
    Upload video to a temporary S3 location for Bedrock processing.
    
    Args:
        video_path: Local path to video file
        
    Returns:
        S3 URI or None if upload failed
    """
    try:
        import boto3
        import uuid
        
        s3_client = boto3.client('s3')
        
        # Use the segments bucket for temporary files
        bucket_name = os.environ.get('SEGMENTS_BUCKET_NAME')
        if not bucket_name:
            logger.error("SEGMENTS_BUCKET_NAME environment variable not set")
            return None
        
        # Create unique key for temporary file
        temp_key = f"temp/direct-inference/{uuid.uuid4()}.mp4"
        
        # Upload file
        s3_client.upload_file(video_path, bucket_name, temp_key)
        
        s3_uri = f"s3://{bucket_name}/{temp_key}"
        logger.info(f"Uploaded video to temporary S3 location: {s3_uri}")
        
        return s3_uri
        
    except Exception as e:
        logger.error(f"Error uploading video to S3: {str(e)}")
        return None


def cleanup_temp_s3_object(s3_uri: str) -> None:
    """
    Clean up temporary S3 object.
    
    Args:
        s3_uri: S3 URI to delete
    """
    try:
        import boto3
        
        # Parse S3 URI
        uri_parts = s3_uri.replace('s3://', '').split('/', 1)
        if len(uri_parts) != 2:
            logger.error(f"Invalid S3 URI format: {s3_uri}")
            return
        
        bucket_name, object_key = uri_parts
        
        s3_client = boto3.client('s3')
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        
        logger.info(f"Cleaned up temporary S3 object: {s3_uri}")
        
    except Exception as e:
        logger.warning(f"Failed to clean up temporary S3 object {s3_uri}: {str(e)}")


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        API Gateway response dict
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps({
            'success': False,
            'error': message,
            'statusCode': status_code
        })
    }