"""
Video Query Handler

This Lambda function handles queries about video analysis results.
It returns all segment captions for a given job ID.
"""

import json
import boto3
import logging
import os
from typing import Dict, Any, List
from decimal import Decimal
from segment_caption_update import list_job_segment_captions


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")

# Initialize Bedrock client for Nova Pro
bedrock_client = boto3.client("bedrock-runtime")

# Get table names from environment variables
VIDEO_ANALYSIS_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
JOB_STATUS_TABLE_NAME = os.environ.get("JOB_STATUS_TABLE_NAME")

video_analysis_table = (
    dynamodb.Table(VIDEO_ANALYSIS_TABLE_NAME) if VIDEO_ANALYSIS_TABLE_NAME else None
)
job_status_table = (
    dynamodb.Table(JOB_STATUS_TABLE_NAME) if JOB_STATUS_TABLE_NAME else None
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function to handle video segment requests.

    This function returns all segment captions for a given job ID.

    Args:
        event: API Gateway event containing the job ID
        context: Lambda context object

    Returns:
        Dict containing all segments for the job in JSON format
    """

    try:
        logger.info(f"Received video query event: {json.dumps(event, indent=2)}")

        # Extract job ID from path parameters
        path_parameters = event.get("pathParameters", {})
        job_id = path_parameters.get("jobId") if path_parameters else None

        # Extract query from request body
        body = event.get("body")
        if body:
            try:
                body_data = json.loads(body)
                query = body_data.get("query")
            except json.JSONDecodeError:
                query = None
        else:
            query = None

        if not job_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                },
                "body": json.dumps(
                    {
                        "error": "Missing jobId in path parameters",
                        "message": "Job ID is required to get video segments",
                    }
                ),
            }

        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                },
                "body": json.dumps(
                    {
                        "error": "Missing query in request body",
                        "message": "Query is required to get video insights",
                    }
                ),
            }

        logger.info(f"Getting segments for job {job_id}")

        # Get all segments for the job
        segments_result = get_job_segments(job_id)

        # Check if we have segments to process
        if segments_result.get("status") == "success" and segments_result.get(
            "segments"
        ):
            logger.info(
                f"Processing query '{query}' for {len(segments_result['segments'])} segments"
            )

            # Invoke Nova Pro to filter segments and provide insights based on query
            ai_result = filter_segments_with_nova_pro(
                segments_result["segments"], query
            )

            if ai_result.get("status") == "error":
                return {
                    "statusCode": 500,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type,Authorization",
                        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    },
                    "body": json.dumps(
                        {
                            "error": "AI analysis failed",
                            "message": ai_result.get("message"),
                        }
                    ),
                }

            # Update the response with AI-filtered results only
            response = {
                "jobId": job_id,
                "status": "success",
                "query": query,
                "jobInfo": segments_result.get("jobInfo", {}),
                "ai_analysis": ai_result,
            }

        else:
            logger.warning(
                f"No segments available for query processing: {segments_result.get('status')}"
            )
            response = {
                "jobId": job_id,
                "status": segments_result.get("status", "error"),
                "query": query,
                "jobInfo": segments_result.get("jobInfo", {}),
                "ai_analysis": {
                    "status": "no_segments",
                    "insights": "No segments available for analysis",
                    "total_relevant_segments": 0,
                },
            }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": json.dumps(response, indent=2, cls=DecimalEncoder),
        }

    except Exception as e:
        logger.error(f"Error processing video query: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": json.dumps(
                {
                    "error": "Internal server error",
                    "message": "Failed to get video segments",
                    "details": str(e),
                }
            ),
        }


def get_job_segments(job_id: str) -> Dict[str, Any]:
    """
    Get all segment captions for a given job ID.

    Args:
        job_id: The video job ID to get segments for

    Returns:
        Dict containing all segments for the job
    """

    try:
        # Get job status information
        job_info = get_job_status(job_id)

        if not job_info:
            return {
                "jobId": job_id,
                "status": "error",
                "message": "Job not found or analysis not completed",
                "segments": [],
            }

        # Get all segment captions for this job
        segment_captions = list_job_segment_captions(job_id)

        if not segment_captions:
            return {
                "jobId": job_id,
                "status": "no_data",
                "message": "No segment captions found for this video",
                "jobInfo": {
                    "videoFileName": job_info.get("videoFileName", ""),
                    "videoDuration": job_info.get("videoDuration", 0),
                    "totalSegments": job_info.get("totalSegments", 0),
                    "processedSegments": job_info.get("processedSegments", 0),
                    "jobStatus": job_info.get("status", "unknown"),
                },
                "segments": [],
            }

        # Sort segments by start time
        segment_captions.sort(key=lambda x: x.get("segmentStartTime", 0))

        # Prepare simplified segment data (omit segments with empty/missing caption)
        segments = []
        for segment in segment_captions:
            caption = segment.get("caption")
            # Skip if caption is None or empty/whitespace
            if caption is None:
                continue
            if isinstance(caption, str) and caption.strip() == "":
                continue
            segments.append(
                {
                    "segmentStartTime": segment.get("segmentStartTime", 0),
                    "caption": caption,
                    "timestamp": segment.get("timestamp"),
                    "metadata": segment.get("inferenceMetadata", {}),
                }
            )

        # Prepare the response
        response = {
            "jobId": job_id,
            "status": "success",
            "jobInfo": {
                "videoFileName": job_info.get("videoFileName", ""),
                "videoDuration": job_info.get("videoDuration", 0),
                "totalSegments": job_info.get("totalSegments", 0),
                "processedSegments": job_info.get("processedSegments", 0),
                "jobStatus": job_info.get("status", "unknown"),
            },
            "segments": segments,
        }

        logger.info(f"Retrieved {len(segments)} segments for job {job_id}")

        return response

    except Exception as e:
        logger.error(f"Error getting segments for job {job_id}: {str(e)}")
        raise e


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get job status information from DynamoDB.

    Args:
        job_id: The job ID to look up

    Returns:
        Job status information or None if not found
    """

    if not job_status_table:
        logger.warning("Job status table not configured")
        return None

    try:
        # Query the job status table for this job ID
        response = job_status_table.query(
            KeyConditionExpression="jobId = :job_id",
            ExpressionAttributeValues={":job_id": job_id},
            ScanIndexForward=False,  # Get most recent first
            Limit=1,
        )

        items = response.get("Items", [])
        if items:
            return items[0]
        else:
            logger.warning(f"No job status found for job {job_id}")
            return None

    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {str(e)}")
        return None


system_prompt = """You are an expert video surveillance analyst with specialized knowledge in security assessment and threat detection. Your role is to analyze video segment captions from surveillance footage and provide actionable insights based on user queries.

## Context
You are analyzing segments from surveillance video footage. Each segment contains:
- A unique segment_id (integer starting from 0)
- A start_time (in seconds from video beginning)
- A caption (AI-generated description of what's happening in that segment)

## Analysis Guidelines

### Relevance Assessment
- Only include segments that directly address or relate to the user's query
- Consider both explicit matches (direct mentions) and implicit relevance (related activities/contexts)
- Prioritize segments with clear, actionable information over vague descriptions
- If no segments are relevant, return an empty relevant_segments array

### Threat Level Classification
- **HIGH**: Immediate security concerns, suspicious behavior, potential crimes, emergencies, unauthorized access
- **MEDIUM**: Unusual activities, policy violations, maintenance issues, crowd gatherings
- **LOW**: Normal activities that happen to match the query, routine observations

### Insights Generation
- Provide a comprehensive summary that synthesizes information across relevant segments
- Include temporal patterns (when events occurred)
- Highlight any security implications or recommendations
- Note any data limitations or gaps in coverage
- Use clear, professional language suitable for security personnel
- DO NOT mention the segment_id

## Response Format
Return ONLY a valid JSON object with this exact structure:
{
    "relevant_segments": [
        {
            "segment_id": <integer>,
            "relevance_reason": "<clear, specific explanation of why this segment matches the query>",
            "threat_level": "<low|medium|high>"
        }
    ],
    "insights": "<detailed summary of findings, patterns, and security implications>"
}

## Quality Standards
- Be selective: quality over quantity in segment selection
- Provide specific, actionable relevance reasons
- Ensure insights add value beyond just listing segment contents
- Maintain consistency in threat level assessment
- Handle edge cases gracefully (no segments, unclear queries, etc.)"""


def filter_segments_with_nova_pro(
    segments: List[Dict[str, Any]], query: str
) -> Dict[str, Any]:
    """
    Use Nova Pro to filter segments and provide insights based on the query.

    Args:
        segments: List of video segments with captions
        query: User's query to filter and analyze segments

    Returns:
        Dictionary containing filtered segments and insights
    """
    try:
        # Prepare the context from segments
        segments_context = []
        for i, segment in enumerate(segments):
            segments_context.append(
                {
                    "segment_id": i,
                    "start_time": float(segment.get("segmentStartTime", 0)),
                    "caption": segment.get("caption", ""),
                }
            )

        # Format segments for better readability
        formatted_segments = []
        for segment in segments_context:
            start_time = segment["start_time"]
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            formatted_segments.append(
                f"Segment {segment['segment_id']}: [{minutes:02d}:{seconds:02d}] {segment['caption']}"
            )

        segments_text = "\n".join(formatted_segments)

        user_prompt = f"""## Analysis Request

**User Query:** "{query}"

**Video Segments Available for Analysis:**
Total segments: {len(segments_context)}

{segments_text}

## Instructions
Analyze the above video segments in the context of the user query. Focus on:
1. Direct relevance to the query subject matter
2. Security implications and threat assessment  
3. Temporal patterns or sequences of events
4. Any notable behaviors or anomalies

Return your analysis as a JSON object following the exact format specified in the system prompt. Include only segments that genuinely relate to the query."""

        # Prepare the request for Nova Pro with optimized parameters for analysis
        request_body = {
            "system": [{"text": system_prompt}],
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {
                "max_new_tokens": 3000,  # Reduced for more focused responses
                "temperature": 0.0,  # Deterministic for consistent analysis
                "top_p": 0.8,  # Balanced creativity/precision
            },
        }

        # Invoke Nova Pro model
        response = bedrock_client.invoke_model(
            modelId="us.amazon.nova-pro-v1:0",  # Nova Pro model ID
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        # Parse the response
        response_body = json.loads(response["body"].read())
        logger.info(f"Nova Pro response: {json.dumps(response_body, indent=2)}")

        # Extract the content from the response (Nova Pro format)
        if "output" in response_body and "message" in response_body["output"]:
            message = response_body["output"]["message"]
            if "content" in message and len(message["content"]) > 0:
                content = message["content"][0]["text"]

            # Try to parse the JSON response
            try:
                # Clean the response to handle potential formatting issues
                content_cleaned = content.strip()
                if content_cleaned.startswith("```json"):
                    content_cleaned = content_cleaned[7:]
                if content_cleaned.endswith("```"):
                    content_cleaned = content_cleaned[:-3]
                content_cleaned = content_cleaned.strip()

                ai_response = json.loads(content_cleaned)

                # Validate response structure
                if not isinstance(ai_response, dict):
                    raise ValueError("Response is not a JSON object")

                if "relevant_segments" not in ai_response:
                    ai_response["relevant_segments"] = []

                if "insights" not in ai_response:
                    ai_response["insights"] = "No insights provided"

                # Map the AI response back to original segments with validation
                filtered_segments = []
                for relevant_seg in ai_response.get("relevant_segments", []):
                    segment_id = relevant_seg.get("segment_id")
                    if segment_id is None:
                        logger.warning("Segment missing segment_id, skipping")
                        continue

                    if not (0 <= segment_id < len(segments)):
                        logger.warning(f"Invalid segment_id {segment_id}, skipping")
                        continue

                    original_segment = segments[segment_id].copy()
                    original_segment["relevance_reason"] = relevant_seg.get(
                        "relevance_reason", "No reason provided"
                    )
                    threat_level = relevant_seg.get("threat_level", "").lower()
                    if threat_level not in ["low", "medium", "high"]:
                        threat_level = "low"  # Default to low if invalid
                    original_segment["threat_level"] = threat_level
                    filtered_segments.append(original_segment)

                return {
                    "status": "success",
                    "filtered_segments": filtered_segments,
                    "insights": ai_response.get("insights", "No insights generated"),
                    "total_relevant_segments": len(filtered_segments),
                    "query_processed": query,
                }

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse Nova Pro JSON response: {str(e)}")
                logger.error(f"Raw content: {content}")
                return {
                    "status": "error",
                    "message": f"Failed to parse AI response: {str(e)}",
                    "raw_response": content[:500] if len(content) > 500 else content,
                }
        else:
            logger.error("No output/message in Nova Pro response")
            return {
                "status": "error",
                "message": "No output in AI response",
            }

    except Exception as e:
        logger.error(f"Error invoking Nova Pro: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to invoke Nova Pro: {str(e)}",
        }
