"""
Job Status Handler

GET /video/{jobId}/status
Returns only the status field for a video processing job from the JobStatusTable.
"""

import json
import os
import logging
import boto3
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
JOB_STATUS_TABLE_NAME = os.environ.get("JOB_STATUS_TABLE_NAME")
job_status_table = dynamodb.Table(JOB_STATUS_TABLE_NAME) if JOB_STATUS_TABLE_NAME else None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        logger.info(f"Received job status request: {json.dumps(event)}")

        # Extract jobId from path parameters
        path_params = event.get("pathParameters") or {}
        job_id = path_params.get("jobId")

        if not job_id:
            return _response(400, {"error": "Missing jobId in path parameters"})

        if not job_status_table:
            return _response(500, {"error": "Job status table not configured"})

        # Query the most recent status record for this jobId
        # Table keys: PK jobId (S), SK uploadTimestamp (S)
        result = job_status_table.query(
            KeyConditionExpression="jobId = :jid",
            ExpressionAttributeValues={":jid": job_id},
            ScanIndexForward=False,  # latest first
            Limit=1,
        )
        items = result.get("Items", [])
        if not items:
            return _response(404, {"status": "not_found"})

        status = items[0].get("status", "unknown")
        return _response(200, {"status": status})

    except Exception as e:
        logger.exception("Error getting job status")
        return _response(500, {"error": str(e)})


def _response(code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body),
    }
