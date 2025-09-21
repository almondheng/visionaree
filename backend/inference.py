import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "us.amazon.nova-pro-v1:0"

system_msgs = [
    {
        "text": "You are an expert surveillance camera captioner. Output only one concise, descriptive caption in plain text. DO NOT include duration, explanations or extra formatting."
    }
]


def summarize_clip(job_id, start_time):
    message_list = [
        {
            "role": "user",
            "content": [
                {
                    "video": {
                        "format": "mp4",
                        "source": {
                            "s3Location": {
                                "uri": f"s3://visionaree-bucket/videos/{job_id}/segments/{start_time}.mp4",
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

    resp = client.invoke_model(modelId=MODEL_ID, body=json.dumps(native_request))
    body = json.loads(resp["body"].read())
    # response text usually at:
    output_text = body["output"]["message"]["content"][0]["text"]
    print("Raw model output:", output_text)
    return output_text


def process_segment(args):
    """Process a single segment. Used for thread pool execution."""
    job_id, start_time = args
    try:
        print(f"Processing segment: {start_time}")
        caption = summarize_clip(job_id, start_time)
        return {
            "job_id": job_id,
            "start_time": start_time,
            "caption": caption,
            "status": "success",
        }
    except Exception as e:
        print(f"Error processing segment {start_time}: {e}")
        return {
            "job_id": job_id,
            "start_time": start_time,
            "caption": None,
            "status": "error",
            "error": str(e),
        }


if __name__ == "__main__":
    import sys
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if len(sys.argv) != 2:
        print("Usage: python model.py <job_id>")
        print("Example: python model.py 123")
        sys.exit(1)

    job_id = sys.argv[1]

    # Get all segments from S3
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("visionaree-bucket")
    prefix = f"videos/{job_id}/segments/"

    # Collect all segment start times
    segments = []
    for obj in bucket.objects.filter(Prefix=prefix):
        start_time = int(obj.key.split("/")[-1].split(".")[0])
        segments.append((job_id, start_time))

    # Sort segments by start time
    segments.sort(key=lambda x: x[1])

    print(f"Found {len(segments)} segments to process")

    # Process segments concurrently
    results = []
    max_workers = min(
        5, len(segments)
    )  # Limit concurrent requests to avoid rate limits

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_segment = {
            executor.submit(process_segment, segment): segment for segment in segments
        }

        # Collect results as they complete
        for future in as_completed(future_to_segment):
            segment = future_to_segment[future]
            try:
                result = future.result()
                results.append(result)
                if result["status"] == "success":
                    print(f"✓ Completed segment {result['start_time']}")
                else:
                    print(f"✗ Failed segment {result['start_time']}: {result['error']}")
            except Exception as e:
                print(f"✗ Exception processing segment {segment[1]}: {e}")
                results.append(
                    {
                        "job_id": segment[0],
                        "start_time": segment[1],
                        "caption": None,
                        "status": "error",
                        "error": str(e),
                    }
                )

    # Sort results by start time and display summary
    results.sort(key=lambda x: x["start_time"])

    print("\nProcessing complete!")
    print(
        f"Successfully processed: {sum(1 for r in results if r['status'] == 'success')}/{len(results)} segments"
    )

    for result in results:
        if result["status"] == "success":
            print(f"Segment {result['start_time']}: {result['caption']}")
        else:
            print(f"Segment {result['start_time']}: ERROR - {result['error']}")

    # TODO: Save all captions with job_id and start_time to database/file
