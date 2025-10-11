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


def summarize_clip(
    s3_uri: str = None,
    job_id: str = None,
    start_time: int = None,
    video_format: str = None,
    video_base64: str = None,
    include_threat_assessment: bool = False,
    user_prompt: str = None,
) -> Dict[str, Any]:
    """
    Summarize a video segment using Amazon Bedrock Nova.

    Args:
        s3_uri: Full S3 URI of the video segment (for backward compatibility)
        job_id: Analysis job ID (optional, for logging/tracking purposes)
        start_time: Start time of the segment in seconds (optional, for logging/tracking purposes)
        video_format: Video format (e.g., 'mp4', 'webm', 'mov'). If None, will auto-detect from URI extension
        video_base64: Base64 encoded video data (alternative to s3_uri for direct processing)
        include_threat_assessment: If True, includes threat level assessment in the response
        user_prompt: Optional custom prompt from user to guide the analysis

    Returns:
        Dict containing caption, status information, and optionally threat level
    """
    try:
        # Extract identifiers from s3_uri if not provided
        if job_id is None or start_time is None:
            # Parse s3_uri to extract job_id and start_time
            # Expected format: s3://bucket/videos/{job_id}/segments/{start_time}.mp4
            uri_parts = s3_uri.replace("s3://", "").split("/")
            if (
                len(uri_parts) >= 4
                and uri_parts[1] == "videos"
                and uri_parts[3] == "segments"
            ):
                extracted_job_id = uri_parts[2]
                extracted_start_time = int(uri_parts[4].split(".")[0])
                job_id = job_id or extracted_job_id
                start_time = (
                    start_time if start_time is not None else extracted_start_time
                )

        # Validate input - need either s3_uri or video_base64
        if not s3_uri and not video_base64:
            raise ValueError("Either s3_uri or video_base64 must be provided")

        # Auto-detect format from file extension if not provided
        if video_format is None:
            if s3_uri:
                file_extension = s3_uri.split(".")[-1].lower()
            else:
                file_extension = "mp4"  # Default for base64 input

            # Map common extensions to Bedrock format names
            format_mapping = {
                "mp4": "mp4",
                "mov": "mov",
                "mkv": "mkv",
                "webm": "webm",
                "avi": "avi",
                "flv": "flv",
                "mpeg": "mpeg",
                "mpg": "mpeg",
                "ts": "ts",
            }
            video_format = format_mapping.get(
                file_extension, "mp4"
            )  # Default to mp4 if unknown

        input_source = "base64 data" if video_base64 else s3_uri
        logger.info(
            f"Summarizing segment {start_time} for job {job_id} from {input_source} (format: {video_format})"
        )

        if include_threat_assessment:
            system_msgs = [
                {
                    "text": "You are an expert surveillance analyst with specialized knowledge in security assessment and threat detection. Analyze the video content and provide both a descriptive caption and a threat level assessment. "
                }
            ]
        else:
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
                            "format": video_format,
                            "source": (
                                {
                                    "s3Location": {
                                        "uri": s3_uri,
                                    }
                                }
                                if s3_uri
                                else {"bytes": video_base64}
                            ),
                        }
                    },
                    {
                        "text": (
                            # Base instruction - always include the original analysis prompt
                            "Summarize this segment of a full video in one sentence. "
                            "Focus only on new or important events. "
                            "Ignore background or static details unless they change. "
                            "If suspicious or unusual activities occur, describe the observation without assumption. "
                            "If nothing significant happens, return empty string. " +
                            # Add user's custom request if provided
                            (
                                f"\n\nAdditionally, please address this specific user request: {user_prompt}"
                                if user_prompt
                                else ""
                            )
                            +
                            # Simple response format instruction based on mode
                            (
                                "\n\nReturn only the caption, no extra text."
                                if not include_threat_assessment
                                else "Assess the threat level based on these criteria:\n"
                                "- HIGH: Immediate security concerns, suspicious behavior, potential crimes, emergencies, unauthorized access, weapons\n"
                                "- MEDIUM: Unusual activities, policy violations, maintenance issues, crowd gatherings\n"
                                "- LOW: Normal activities, routine observations\n\n"
                                'Return your response as JSON: {"caption": "description", "threat_level": "low|medium|high"}'
                            )
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

        resp = bedrock_client.invoke_model(
            modelId=MODEL_ID, body=json.dumps(native_request)
        )
        body = json.loads(resp["body"].read())
        output_text = body["output"]["message"]["content"][0]["text"]

        # Extract token usage information
        usage = body.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        total_tokens = input_tokens + output_tokens

        # Print detailed Bedrock inference information
        print(f"\n🤖 BEDROCK INFERENCE - Job: {job_id}, Segment: {start_time}s")
        print(f"📹 Video Source: {'S3' if s3_uri else 'Base64'}")
        print(f"🧠 Model: {MODEL_ID}")
        print(
            f"🔢 Token Usage: {input_tokens} input + {output_tokens} output = {total_tokens} total"
        )
        print(f"💭 Response: {output_text}")
        print("-" * 60)

        logger.info(f"Bedrock response for segment {start_time}: {output_text}")
        logger.info(
            f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}"
        )

        # Parse response based on whether threat assessment was requested
        if include_threat_assessment:
            try:
                # Try to parse JSON response
                import json as json_module

                response_data = json_module.loads(output_text.strip())
                return {
                    "job_id": job_id,
                    "start_time": start_time,
                    "caption": response_data.get("caption", output_text),
                    "threat_level": response_data.get("threat_level", "low"),
                    "status": "success",
                    "token_usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    },
                }
            except json_module.JSONDecodeError:
                # Fallback if JSON parsing fails
                logger.warning(
                    f"Failed to parse threat assessment JSON, using text response: {output_text}"
                )
                return {
                    "job_id": job_id,
                    "start_time": start_time,
                    "caption": output_text,
                    "threat_level": "low",  # Default to low if parsing fails
                    "status": "success",
                    "token_usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    },
                }
        else:
            return {
                "job_id": job_id,
                "start_time": start_time,
                "caption": output_text,
                "status": "success",
                "token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                },
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
