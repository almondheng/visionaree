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

            # Update the response with AI-filtered results
            segments_result.update(
                {
                    "query": query,
                    "ai_analysis": ai_result,
                }
            )

        else:
            logger.warning(
                f"No segments available for query processing: {segments_result.get('status')}"
            )
            segments_result.update(
                {
                    "query": query,
                    "ai_analysis": {
                        "status": "no_segments",
                        "insights": "No segments available for analysis",
                        "total_relevant_segments": 0,
                    },
                }
            )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": json.dumps(segments_result, indent=2, cls=DecimalEncoder),
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

        # Prepare simplified segment data
        segments = []
        for segment in segment_captions:
            segments.append(
                {
                    "segmentStartTime": segment.get("segmentStartTime", 0),
                    "caption": segment.get("caption", ""),
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


system_prompt = """You are an AI assistant that helps users find relevant video segments of surveillance footage and provides insights based on their queries. 

You will be given:
1. A list of video segments with timestamps and captions
2. A user query

Your task is to:
1. Identify the most relevant segments that answer or relate to the user's query
2. Provide a concise summary of insights based on the relevant segments
3. Return the results in the specified JSON format

Return your response as a JSON with this exact structure:
{
    "relevant_segments": [
        {
            "segment_id": <number>,
            "relevance_score": <number between 0 and 1>,
            "relevance_reason": "<brief explanation>",
            "threat_level": <"low", "medium", "high">
        }
    ],
    "insights": "<comprehensive summary of findings>"
}

Only include segments that are actually relevant to the query. Be selective and focus on quality over quantity."""


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

        user_prompt = f"""Query: {query}

Video Segments:
{json.dumps(segments_context, indent=2)}

Please analyze these segments and provide relevant results based on the query.
Return only the JSON response as specified in the system prompt, no extra text."""

        # Prepare the request for Nova Pro
        request_body = {
            "system": [{"text": system_prompt}],
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {
                "max_new_tokens": 4000,
                "temperature": 0.1,
                "top_p": 0.9,
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
                ai_response = json.loads(content)

                # Map the AI response back to original segments
                filtered_segments = []
                for relevant_seg in ai_response.get("relevant_segments", []):
                    segment_id = relevant_seg.get("segment_id")
                    if 0 <= segment_id < len(segments):
                        original_segment = segments[segment_id].copy()
                        original_segment["relevance_score"] = relevant_seg.get(
                            "relevance_score", 0
                        )
                        original_segment["relevance_reason"] = relevant_seg.get(
                            "relevance_reason", ""
                        )
                        filtered_segments.append(original_segment)

                return {
                    "status": "success",
                    "filtered_segments": filtered_segments,
                    "insights": ai_response.get("insights", "No insights generated"),
                    "total_relevant_segments": len(filtered_segments),
                }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Nova Pro JSON response: {str(e)}")
                return {
                    "status": "error",
                    "message": "Failed to parse AI response",
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
