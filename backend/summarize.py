import boto3
import json
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Bedrock client
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Bedrock model configuration
MODEL_ID = "us.amazon.nova-pro-v1:0"


def summarize_clip(s3_uri: str, job_id: str = None, start_time: int = None) -> Dict[str, Any]:
    """
    Summarize a video segment using Amazon Bedrock Nova.
    
    Args:
        s3_uri: Full S3 URI of the video segment (e.g., s3://bucket/path/to/video.mp4)
        job_id: Analysis job ID (optional, for logging/tracking purposes)
        start_time: Start time of the segment in seconds (optional, for logging/tracking purposes)
        
    Returns:
        Dict containing caption and status information
    """
    try:
        # Extract identifiers from s3_uri if not provided
        if job_id is None or start_time is None:
            # Parse s3_uri to extract job_id and start_time
            # Expected format: s3://bucket/videos/{job_id}/segments/{start_time}.mp4
            uri_parts = s3_uri.replace("s3://", "").split("/")
            if len(uri_parts) >= 4 and uri_parts[1] == "videos" and uri_parts[3] == "segments":
                extracted_job_id = uri_parts[2]
                extracted_start_time = int(uri_parts[4].split(".")[0])
                job_id = job_id or extracted_job_id
                start_time = start_time if start_time is not None else extracted_start_time
        
        logger.info(f"Summarizing segment {start_time} for job {job_id} at {s3_uri}")
        
        system_msgs = [
            {
                "text": "You are an expert surveillance camera captioner. Output only one concise, descriptive caption in plain text. DO NOT include duration, explanations or extra formatting."
            }
        ]
        
        message_list = [
            {
                "role": "user",
                "content": [
                    {
                        "video": {
                            "format": "mp4",
                            "source": {
                                "s3Location": {
                                    "uri": s3_uri,
                                }
                            },
                        }
                    },
                    {
                        "text": (
                            "Summarize this segment of a full video in one sentence. "
                            "Focus only on new or important actions or events. "
                            "Ignore background or static details unless they change. "
                            "If suspicious or unusual activities occur, describe them clearly. "
                            "If nothing significant happens, return empty string. "
                            "Return only the caption, no extra text."
                        )
                    },
                ],
            }
        ]

        inference_config = {"maxTokens": 1500, "temperature": 0.0, "topP": 0.9}

        native_request = {
            "schemaVersion": "messages-v1",
            "messages": message_list,
            "system": system_msgs,
            "inferenceConfig": inference_config,
        }

        resp = bedrock_client.invoke_model(modelId=MODEL_ID, body=json.dumps(native_request))
        body = json.loads(resp["body"].read())
        output_text = body["output"]["message"]["content"][0]["text"]
        
        # Print detailed Bedrock inference information
        print(f"\n🤖 BEDROCK INFERENCE - Job: {job_id}, Segment: {start_time}s")
        print(f"📹 Video S3 URI: {s3_uri}")
        print(f"🧠 Model: {MODEL_ID}")
        print(f"💭 Response: {output_text}")
        print("-" * 60)
        
        logger.info(f"Bedrock response for segment {start_time}: {output_text}")
        
        return {
            "job_id": job_id,
            "start_time": start_time,
            "caption": output_text,
            "status": "success",
        }
        
    except Exception as e:
        logger.error(f"Error summarizing segment {start_time}: {str(e)}")
        return {
            "job_id": job_id,
            "start_time": start_time,
            "caption": None,
            "status": "error",
            "error": str(e),
        }