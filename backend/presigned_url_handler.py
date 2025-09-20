import json
import boto3
import uuid
import os
from botocore.exceptions import ClientError
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function to generate presigned URLs for S3 video uploads.
    
    Expected request body:
    {
        "filename": "video.mp4",
        "jobId": "analysis-job-123",
        "contentType": "video/mp4"
    }
    
    Returns:
    {
        "presignedUrl": "https://...",
        "key": "videos/analysis-job-123_unique-id_video.mp4",
        "bucket": "bucket-name"
    }
    }
    """
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',  # Configure this for your domain in production
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    # Handle preflight CORS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Get environment variables
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable not set")
        
        # Parse request body
        if 'body' not in event:
            raise ValueError("Request body is required")
        
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Validate required fields
        filename = body.get('filename')
        job_id = body.get('jobId')
        content_type = body.get('contentType', 'video/mp4')
        
        if not filename:
            raise ValueError("filename is required in request body")
        
        if not job_id:
            raise ValueError("jobId is required in request body")
        
        # Validate jobId format (alphanumeric, dashes, underscores only)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', job_id):
            raise ValueError("jobId must contain only alphanumeric characters, dashes, and underscores")
        
        # Validate file extension for security
        allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension not in allowed_extensions:
            raise ValueError(f"File type {file_extension} not allowed. Supported types: {', '.join(allowed_extensions)}")
        
        # Generate unique key for the video file with jobId
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"videos/{job_id}_{unique_id}_{filename}"
        
        # Generate presigned URL for PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type,
                'ServerSideEncryption': 'AES256'
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        
        logger.info(f"Generated presigned URL for key: {s3_key}")
        
        # Return success response
        response_body = {
            'presignedUrl': presigned_url,
            'key': s3_key,
            'bucket': bucket_name,
            'expiresIn': 3600
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body)
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': str(e)
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to generate presigned URL'
            })
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }