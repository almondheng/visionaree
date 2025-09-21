# Video Query API

This document describes how to use the new video query API endpoint to ask questions about video content.

## Endpoint

**URL**: `POST /video/{jobId}/ask`

**Description**: Query video analysis results with natural language questions

## Parameters

### Path Parameters
- `jobId` (string, required): The video analysis job ID

### Request Body
```json
{
  "query": "string (required) - Natural language question about the video content"
}
```

## Example Usage

### Request
```bash
curl -X POST \
  'https://your-api-gateway-url/prod/video/job123/ask' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Is there a person walking in the video?"
  }'
```

### Response (Success)
```json
{
  "jobId": "job123",
  "query": "Is there a person walking in the video?",
  "status": "success",
  "jobInfo": {
    "videoFileName": "security_footage.mp4",
    "videoDuration": 120.5,
    "totalSegments": 24,
    "processedSegments": 24,
    "jobStatus": "done"
  },
  "searchResults": {
    "totalSegments": 24,
    "relevantSegments": 3,
    "segments": [
      {
        "segmentStartTime": 15,
        "caption": "A person walks across the parking lot carrying a briefcase",
        "relevanceScore": 12,
        "matchedTerms": ["phrase:'person walking'", "person", "walking"],
        "timestamp": "2025-09-21T10:30:25.123Z",
        "metadata": {
          "status": "success",
          "model_id": "us.amazon.nova-pro-v1:0",
          "inference_timestamp": "2025-09-21T10:30:25.123Z"
        }
      },
      {
        "segmentStartTime": 45,
        "caption": "Person walking towards the building entrance",
        "relevanceScore": 10,
        "matchedTerms": ["person", "walking"],
        "timestamp": "2025-09-21T10:30:55.456Z",
        "metadata": {
          "status": "success",
          "model_id": "us.amazon.nova-pro-v1:0",
          "inference_timestamp": "2025-09-21T10:30:55.456Z"
        }
      },
      {
        "segmentStartTime": 75,
        "caption": "Individual walking past parked cars",
        "relevanceScore": 6,
        "matchedTerms": ["walking"],
        "timestamp": "2025-09-21T10:31:25.789Z",
        "metadata": {
          "status": "success",
          "model_id": "us.amazon.nova-pro-v1:0",
          "inference_timestamp": "2025-09-21T10:31:25.789Z"
        }
      }
    ]
  },
  "summary": {
    "message": "Found 3 segments related to 'Is there a person walking in the video?'",
    "timeRange": {
      "earliest": 15,
      "latest": 75,
      "span": 60
    },
    "relevanceInfo": {
      "maxScore": 12,
      "highRelevanceCount": 2,
      "averageScore": 9.33
    },
    "topMatches": [
      {
        "time": 15,
        "caption": "A person walks across the parking lot carrying a briefcase",
        "score": 12
      },
      {
        "time": 45,
        "caption": "Person walking towards the building entrance",
        "score": 10
      },
      {
        "time": 75,
        "caption": "Individual walking past parked cars",
        "score": 6
      }
    ]
  }
}
```

### Response (No Results)
```json
{
  "jobId": "job123",
  "query": "Are there any cats in the video?",
  "status": "success",
  "jobInfo": {
    "videoFileName": "security_footage.mp4",
    "videoDuration": 120.5,
    "totalSegments": 24,
    "processedSegments": 24,
    "jobStatus": "done"
  },
  "searchResults": {
    "totalSegments": 24,
    "relevantSegments": 0,
    "segments": []
  },
  "summary": {
    "message": "No relevant segments found for query: 'Are there any cats in the video?'",
    "suggestions": [
      "Try different keywords or phrases",
      "Check if the video analysis has completed",
      "Use more general terms if being too specific"
    ]
  }
}
```

### Response (Error - Job Not Found)
```json
{
  "jobId": "invalid-job",
  "query": "What happens in the video?",
  "status": "error",
  "message": "Job not found or analysis not completed",
  "results": []
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing search query",
  "message": "A search query is required to find relevant video segments"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "Failed to process video query",
  "details": "Error details here"
}
```

## Search Features

The API supports sophisticated text matching:

1. **Exact Phrase Matching**: Highest relevance score (score: +10)
   - Example: "person walking" matches "A person walking across the lot"

2. **Individual Word Matching**: Medium relevance score (score: +2 per word)
   - Example: "walking" matches any caption containing "walking"

3. **Partial Word Matching**: Lower relevance score (score: +1)
   - Example: "walk" partially matches "walking"

## Query Examples

- **Activity Questions**: "Is someone running?", "What is happening at 30 seconds?"
- **Object Detection**: "Are there any cars?", "Do you see a person?"
- **Time-based Queries**: "What happens first?", "Show me movement"
- **Descriptive Queries**: "Describe the suspicious activity", "Find unusual behavior"

## Relevance Scoring

Results are ranked by relevance score:
- **High relevance** (8+): Exact phrase matches or multiple word matches
- **Medium relevance** (4-7): Single word matches or partial matches
- **Low relevance** (1-3): Partial word matches only

Results are sorted by relevance score (highest first), then by segment start time.