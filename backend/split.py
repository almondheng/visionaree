#!/usr/bin/env python3
"""
Video splitting script that downloads a video from S3, splits it into segments,
and uploads the segments back to S3.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError


class VideoSplitter:
    def __init__(self):
        self.s3_client = boto3.client("s3")

    def parse_s3_url(self, s3_url):
        """Parse S3 URL to extract bucket and key."""
        parsed = urlparse(s3_url)
        if parsed.scheme != "s3":
            raise ValueError(f"Invalid S3 URL: {s3_url}")

        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        return bucket, key

    def download_from_s3(self, bucket, key, local_path):
        """Download file from S3 to local path."""
        try:
            print(f"Downloading s3://{bucket}/{key} to {local_path}")
            self.s3_client.download_file(bucket, key, local_path)
            print("Download completed successfully")
        except ClientError as e:
            print(f"Error downloading from S3: {e}")
            raise

    def upload_to_s3(self, local_path, bucket, key):
        """Upload file from local path to S3."""
        try:
            print(f"Uploading {local_path} to s3://{bucket}/{key}")
            self.s3_client.upload_file(local_path, bucket, key)
            print("Upload completed successfully")
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            raise

    def upload_segment_to_s3(self, args):
        """Upload a single segment to S3. Used for thread pool execution."""
        segment_path, bucket, segment_key = args
        try:
            segment_filename = Path(segment_path).name
            print(f"Uploading {segment_filename} to s3://{bucket}/{segment_key}")
            self.s3_client.upload_file(segment_path, bucket, segment_key)
            return f"s3://{bucket}/{segment_key}"
        except ClientError as e:
            print(f"Error uploading {segment_filename} to S3: {e}")
            raise

    def get_video_duration(self, video_path):
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(video_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stderr
                )

            duration = float(result.stdout.strip())
            print(f"Video duration: {duration:.2f} seconds")
            return duration
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"Error getting video duration: {e}")
            raise

    def split_video(self, input_path, output_dir, segment_duration=5):
        """Split video into segments using ffmpeg."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Get video duration to calculate number of segments
            total_duration = self.get_video_duration(input_path)

            # Calculate segments properly
            num_segments = int(total_duration / segment_duration)
            if total_duration % segment_duration > 0:
                num_segments += 1

            print(
                f"Splitting video into {num_segments} segments of {segment_duration} seconds each"
            )

            # Split video into segments with timestamp-based naming
            segment_paths = []
            for i in range(num_segments):
                start_time = i * segment_duration

                # For the last segment, go to the end of the video
                if i == num_segments - 1:
                    end_time = total_duration
                else:
                    end_time = (i + 1) * segment_duration

                actual_duration = end_time - start_time

                # Skip segments that are too short (less than 0.5 seconds)
                if actual_duration < 0.5:
                    print(f"Skipping segment {i+1} (too short: {actual_duration:.2f}s)")
                    continue

                # Create simple seconds-based filename
                # Format: 0.mp4, 5.mp4, 10.mp4 (start time in seconds, no padding)
                segment_filename = f"{int(start_time)}.mp4"
                segment_path = os.path.join(output_dir, segment_filename)

                cmd = [
                    "ffmpeg",
                    "-i",
                    str(input_path),
                    "-ss",
                    str(start_time),
                    "-t",
                    str(actual_duration),
                    "-vf",
                    "setpts=PTS-STARTPTS",  # Reset video timestamps to prevent black frames
                    "-an",  # Drop audio track (no audio needed for video analysis)
                    "-c:v",
                    "libx264",  # Re-encode video to ensure clean segments
                    "-preset",
                    "fast",  # Fast encoding preset
                    "-crf",
                    "23",  # Good quality compression
                    "-avoid_negative_ts",
                    "make_zero",
                    "-y",  # Overwrite output files
                    segment_path,
                ]

                print(f"Creating segment {i+1}/{num_segments}: {segment_filename}")
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    print(f"ffmpeg stderr: {result.stderr}")
                    raise subprocess.CalledProcessError(
                        result.returncode, cmd, result.stderr
                    )

                segment_paths.append(segment_path)

            # Get list of created segments for verification
            segments = sorted([f for f in os.listdir(output_dir) if f.endswith(".mp4")])
            print(f"Created {len(segments)} segments: {segments}")

            return segment_paths

        except subprocess.CalledProcessError as e:
            print(f"Error splitting video: {e}")
            raise

    def split_s3_video(self, s3_url, segment_duration=5, output_prefix=None):
        """
        Main function to split an S3 video into segments.

        Args:
            s3_url: S3 URL of the video file
            segment_duration: Duration of each segment in seconds
            output_prefix: Prefix for output segment keys (optional)
        """
        # Parse S3 URL
        bucket, key = self.parse_s3_url(s3_url)

        # Generate output prefix if not provided
        if output_prefix is None:
            job_id = Path(key).parent.parent
            output_prefix = f"{job_id}/segments"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video to temporary directory
            video_filename = Path(key).name
            local_video_path = os.path.join(temp_dir, video_filename)
            self.download_from_s3(bucket, key, local_video_path)

            # Create segments directory
            segments_dir = os.path.join(temp_dir, "segments")

            # Split video into segments
            segment_paths = self.split_video(
                local_video_path, segments_dir, segment_duration
            )

            # Upload segments back to S3 using thread pool for concurrent uploads
            print(f"\nUploading {len(segment_paths)} segments to S3 concurrently...")
            upload_tasks = []
            for segment_path in segment_paths:
                segment_filename = Path(segment_path).name
                segment_key = f"{output_prefix}/{segment_filename}"
                upload_tasks.append((segment_path, bucket, segment_key))

            uploaded_segments = []
            max_workers = min(10, len(segment_paths))  # Limit concurrent uploads

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all upload tasks
                future_to_task = {
                    executor.submit(self.upload_segment_to_s3, task): task
                    for task in upload_tasks
                }

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    try:
                        s3_url = future.result()
                        uploaded_segments.append(s3_url)
                        print(f"✓ Upload completed: {Path(s3_url).name}")
                    except Exception as e:
                        task = future_to_task[future]
                        print(f"✗ Upload failed for {Path(task[0]).name}: {e}")
                        raise

            print(f"\nSuccessfully uploaded {len(uploaded_segments)} segments:")
            for segment_url in sorted(uploaded_segments):
                print(f"  {segment_url}")

            return uploaded_segments


def main():
    """Main function to run the video splitter."""
    if len(sys.argv) < 2:
        print("Usage: python split.py <s3_video_url> [segment_duration]")
        print(
            "Example: python split.py s3://visionaree-bucket/videos/123/original/123.mp4 5"
        )
        sys.exit(1)

    s3_url = sys.argv[1]
    segment_duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is not installed or not in PATH")
        print("Please install ffmpeg first:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt install ffmpeg")
        sys.exit(1)

    try:
        splitter = VideoSplitter()
        segments = splitter.split_s3_video(s3_url, segment_duration)
        print("\nVideo splitting completed successfully!")
        print(f"Created {len(segments)} segments of {segment_duration} seconds each.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
