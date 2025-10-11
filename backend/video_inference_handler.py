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
        user_prompt = None
        
        if content_type.startswith('multipart/form-data'):
            # Parse multipart form data
            video_data, original_filename, user_prompt = parse_multipart_video(body, content_type)
        elif (content_type.startswith('video/') or 
              content_type.startswith('application/octet-stream') or
              content_type in ['video/mp4', 'video/quicktime', 'video/x-matroska', 
                              'video/webm', 'video/x-msvideo', 'video/x-flv', 
                              'video/mpeg', 'video/mp2t']):
            # Direct binary video upload
            video_data = body if isinstance(body, bytes) else body.encode()
            
            # Determine filename based on content-type if x-filename not provided
            default_filename = headers.get('x-filename')
            if not default_filename:
                content_type_to_extension = {
                    'video/mp4': 'video.mp4',
                    'video/webm': 'video.webm', 
                    'video/quicktime': 'video.mov',
                    'video/x-matroska': 'video.mkv',
                    'video/x-msvideo': 'video.avi',
                    'video/x-flv': 'video.flv',
                    'video/mpeg': 'video.mpeg',
                    'video/mp2t': 'video.ts'
                }
                default_filename = content_type_to_extension.get(content_type, 'video.mp4')
            
            original_filename = default_filename
            # For binary uploads, check for user_prompt in headers
            user_prompt = headers.get('x-user-prompt')
            logger.info(f"Binary upload detected: content-type={content_type}, filename={original_filename}, user_prompt={user_prompt}")
        else:
            return create_error_response(400, f"Unsupported content type: {content_type}. Please use multipart/form-data or a supported video MIME type.")
        
        if not video_data:
            return create_error_response(400, "No video data found in request")
        
        logger.info(f"Extracted video data: {len(video_data)} bytes, filename: {original_filename}")
        
        # Validate video format
        format_validation = validate_video_format(original_filename, video_data)
        if not format_validation['valid']:
            return create_error_response(400, format_validation['error'])
        
        # Validate file size (limit to 50MB for Lambda)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(video_data) > max_size:
            return create_error_response(413, f"File too large. Maximum size is {max_size // (1024*1024)}MB")
        
        # Process the video and run Bedrock inference
        video_format = format_validation.get('format', '.mp4').lstrip('.')  # Remove leading dot
        inference_result = process_video_for_inference(video_data, original_filename, video_format, user_prompt)
        
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


def parse_multipart_video(body_bytes: bytes, content_type: str) -> tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Parse multipart/form-data to extract video file and optional user prompt.
    
    Args:
        body_bytes: Raw request body bytes
        content_type: Content-Type header value
        
    Returns:
        Tuple of (video_data, filename, user_prompt) or (None, None, None) if not found
    """
    try:
        # Extract boundary from content-type
        boundary = None
        if 'boundary=' in content_type:
            boundary = content_type.split('boundary=')[1].split(';')[0]
        
        if not boundary:
            logger.error("No boundary found in multipart content-type")
            return None, None, None
        
        boundary_bytes = f'--{boundary}'.encode()
        
        # Split by boundary
        parts = body_bytes.split(boundary_bytes)
        
        video_data = None
        filename = None
        user_prompt = None
        
        for part in parts:
            if b'Content-Disposition:' not in part:
                continue
                
            # Parse Content-Disposition header
            lines = part.split(b'\r\n')
            content_disposition = None
            for line in lines:
                if b'Content-Disposition:' in line:
                    content_disposition = line.decode('utf-8', errors='ignore')
                    break
            
            if not content_disposition:
                continue
            
            # Extract field name
            field_name = None
            if 'name="' in content_disposition:
                field_name = content_disposition.split('name="')[1].split('"')[0]
            elif 'name=' in content_disposition:
                field_name = content_disposition.split('name=')[1].split(';')[0].split(' ')[0]
            
            # Extract field data (after double CRLF)
            if b'\r\n\r\n' in part:
                field_data = part.split(b'\r\n\r\n', 1)[1]
                # Remove trailing boundary markers
                if field_data.endswith(b'\r\n'):
                    field_data = field_data[:-2]
                
                if field_name == 'video' and b'filename=' in content_disposition.encode():
                    # This is the video file
                    # Extract filename
                    if 'filename="' in content_disposition:
                        filename = content_disposition.split('filename="')[1].split('"')[0]
                    elif 'filename=' in content_disposition:
                        filename = content_disposition.split('filename=')[1].split(';')[0].split(' ')[0]
                    
                    video_data = field_data
                    logger.info(f"Found video file: {filename}, size: {len(field_data)} bytes")
                
                elif field_name == 'user_prompt':
                    # This is the user prompt text field
                    user_prompt = field_data.decode('utf-8', errors='ignore').strip()
                    logger.info(f"Found user prompt: {user_prompt}")
        
        if video_data is None:
            logger.error("No video file found in multipart data")
            return None, None, None
        
        return video_data, filename, user_prompt
        
    except Exception as e:
        logger.error(f"Error parsing multipart data: {str(e)}")
        return None, None, None


def process_video_for_inference(video_data: bytes, filename: str, video_format: str = 'mp4', user_prompt: str = None) -> Dict[str, Any]:
    """
    Process video data and run Bedrock inference.
    
    Args:
        video_data: Raw video file bytes
        filename: Original filename
        video_format: Video format (e.g., 'mp4', 'webm', 'mov')
        user_prompt: Optional custom prompt from user to guide the analysis
        
    Returns:
        Dict containing inference results
    """
    
    try:
        # Get basic video info for response
        video_info = {
            'file_size': len(video_data),
            'format': video_format
        }
        logger.info(f"Processing video: {len(video_data)} bytes, format: {video_format}")
        
        # Use original video directly - encode as base64 for Bedrock
        logger.info("Encoding video as base64 for direct Bedrock processing (no S3 upload)")
        
        # Encode video data to base64
        video_base64 = base64.b64encode(video_data).decode('utf-8')
        logger.info(f"Encoded video to base64: {len(video_base64)} characters")
        
        try:
            # Run Bedrock inference with base64 data
            logger.info("Running Bedrock inference with base64 video data")
            
            inference_result = summarize_clip(
                job_id="direct-inference",
                start_time=0,
                video_format=video_format,
                video_base64=video_base64,
                include_threat_assessment=True,
                user_prompt=user_prompt
            )
            
            # Prepare clean response with only essential data
            response = {
                'success': True,
                'file_size': video_info.get('file_size', 0),
                'caption': inference_result.get('caption'),
                'threat_level': inference_result.get('threat_level', 'low'),
                'status': inference_result.get('status'),
                'token_usage': inference_result.get('token_usage', {})
            }
            
            # Only include error if there was one
            if inference_result.get('error'):
                response['error'] = inference_result.get('error')
            
            return response
            
        except Exception as e:
            # No cleanup needed for base64 processing
            raise
        
    except Exception as e:
        logger.error(f"Error processing video for inference: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
    finally:
        # No cleanup needed for base64 processing
        pass


def validate_video_format(filename: str, video_data: bytes) -> Dict[str, Any]:
    """
    Validate that the uploaded file is MP4 format (required by Bedrock Nova).
    
    Args:
        filename: Original filename
        video_data: Raw video file bytes
        
    Returns:
        Dict with 'valid' boolean and 'error' message if invalid
    """
    
    # Bedrock Nova supported formats (from AWS docs)
    SUPPORTED_FORMATS = {
        '.mp4': {'mime': 'video/mp4', 'signatures': [b'ftyp']},
        '.mov': {'mime': 'video/quicktime', 'signatures': [b'ftyp', b'moov']},
        '.mkv': {'mime': 'video/x-matroska', 'signatures': [b'\x1a\x45\xdf\xa3']},
        '.webm': {'mime': 'video/webm', 'signatures': [b'\x1a\x45\xdf\xa3']},
        '.avi': {'mime': 'video/x-msvideo', 'signatures': [b'RIFF']},
        '.flv': {'mime': 'video/x-flv', 'signatures': [b'FLV']},
        '.mpeg': {'mime': 'video/mpeg', 'signatures': [b'\x00\x00\x01\xba', b'\x00\x00\x01\xb3']},
        '.mpg': {'mime': 'video/mpeg', 'signatures': [b'\x00\x00\x01\xba', b'\x00\x00\x01\xb3']},
        '.ts': {'mime': 'video/mp2t', 'signatures': [b'G']}
    }
    
    try:
        # Check file extension
        if not filename:
            return {'valid': False, 'error': 'No filename provided'}
        
        file_extension = None
        for ext in SUPPORTED_FORMATS.keys():
            if filename.lower().endswith(ext):
                file_extension = ext
                break
        
        if not file_extension:
            supported_list = ', '.join(SUPPORTED_FORMATS.keys())
            return {
                'valid': False, 
                'error': f'Unsupported file format. Supported formats: {supported_list}'
            }
        
        # Basic file signature validation (magic bytes check)
        if len(video_data) < 12:  # Need at least 12 bytes to check signatures
            return {'valid': False, 'error': 'File too small to be a valid video'}
        
        # Check for expected magic bytes/signatures
        format_info = SUPPORTED_FORMATS[file_extension]
        signature_found = False
        
        for signature in format_info['signatures']:
            # Check first 50 bytes for signature (some formats have signatures not at the very beginning)
            search_bytes = video_data[:50]
            if signature in search_bytes:
                signature_found = True
                break
        
        if not signature_found:
            logger.warning(f"No expected signature found for {file_extension} format, but proceeding anyway")
            # Don't fail here - signature check is just a warning, file extension is sufficient
            # Note: WebM and MKV both use Matroska container with same signature
        
        logger.info(f"Video format validation passed: {filename} -> {file_extension} (MIME: {format_info['mime']})")
        return {
            'valid': True,
            'format': file_extension,
            'mime_type': format_info['mime']
        }
        
    except Exception as e:
        logger.error(f"Error validating video format: {str(e)}")
        return {'valid': False, 'error': f'Format validation error: {str(e)}'}


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



# Commented out - using base64 instead of S3 upload
# def upload_temp_video_to_s3(video_path: str) -> Optional[str]:
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
        
        # Preserve original file extension for Bedrock format detection
        file_extension = os.path.splitext(video_path)[1] or '.mp4'
        temp_key = f"temp/direct-inference/{uuid.uuid4()}{file_extension}"
        
        # Upload file
        s3_client.upload_file(video_path, bucket_name, temp_key)
        
        s3_uri = f"s3://{bucket_name}/{temp_key}"
        logger.info(f"Uploaded video to temporary S3 location: {s3_uri}")
        
        return s3_uri
        
    except Exception as e:
        logger.error(f"Error uploading video to S3: {str(e)}")
        return None


# Commented out - using base64 instead of S3 upload
# def cleanup_temp_s3_object(s3_uri: str) -> None:
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