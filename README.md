# Visionaree

Security footage insights using Amazon Bedrock Nova Lite model.

## Overview

Visionaree is a Python application that analyzes security footage by uploading video files to Amazon S3 and using Amazon Bedrock's Nova Lite model to generate detailed descriptions of the video content.

## Features

- Upload video files to Amazon S3 with encryption
- Analyze videos using Amazon Bedrock Nova Lite model (inference profile: `apac.amazon.nova-lite-v1:0`)
- Generate detailed descriptions focusing on security-relevant activities
- Command-line interface for easy usage
- Automatic S3 bucket creation and management
- Comprehensive error handling and logging

## Prerequisites

- Python 3.8 or higher
- AWS Account with appropriate permissions for:
  - Amazon S3 (create buckets, upload objects)
  - Amazon Bedrock (invoke Nova Lite model)
- AWS CLI configured with credentials or IAM role with appropriate permissions

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd visionaree
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure AWS credentials (if not already configured):
```bash
aws configure
```

## Usage

### Basic Usage

```bash
python main.py path/to/your/video.mp4
```

### Advanced Options

```bash
python main.py path/to/your/video.mp4 --bucket your-s3-bucket --region us-west-2 --verbose
```

### Command Line Arguments

- `video_file`: Path to the video file to analyze (required)
- `--bucket`: S3 bucket name (optional, will create one if not provided)
- `--region`: AWS region (default: us-east-1)
- `--verbose`: Enable verbose logging

## Example Output

```
2025-09-20 10:30:15,123 - INFO - Initialized VideoAnalyzer with bucket: visionaree-videos-abc12345
2025-09-20 10:30:16,456 - INFO - Uploading video to S3: /path/to/video.mp4
2025-09-20 10:30:25,789 - INFO - Video uploaded successfully. S3 URI: s3://visionaree-videos-abc12345/videos/def67890_video.mp4
2025-09-20 10:30:26,012 - INFO - Analyzing video with Bedrock Nova Lite: s3://visionaree-videos-abc12345/videos/def67890_video.mp4
2025-09-20 10:30:35,345 - INFO - Video analysis completed successfully

============================================================
VIDEO ANALYSIS COMPLETE
============================================================
Video uploaded to: s3://visionaree-videos-abc12345/videos/def67890_video.mp4

ANALYSIS DESCRIPTION:
----------------------------------------
The video shows a person walking through a parking lot during daylight hours. 
The individual appears to be carrying a backpack and moves in a normal walking 
pattern. There are several parked vehicles visible in the frame, and the 
lighting conditions suggest it was recorded during mid-day hours.
============================================================
```

## AWS Permissions

Your AWS credentials need the following permissions:

### S3 Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:HeadBucket",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::visionaree-videos-*",
                "arn:aws:s3:::visionaree-videos-*/*"
            ]
        }
    ]
}
```

### Bedrock Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "arn:aws:bedrock:*::foundation-model/amazon.nova-lite-v1:0"
        }
    ]
}
```

## Supported Video Formats

The application supports common video formats including:
- MP4
- MOV
- AVI
- MKV

## Error Handling

The application includes comprehensive error handling for:
- Missing AWS credentials
- File not found errors
- S3 upload failures
- Bedrock model invocation errors
- Network connectivity issues

## Logging

The application uses Python's logging module with configurable levels:
- INFO: General operation information
- DEBUG: Detailed debugging information (use `--verbose` flag)
- ERROR: Error messages and exceptions

## License

This project is licensed under the MIT License.