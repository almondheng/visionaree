# Visionaree API Documentation

## Presigned URL Endpoint

The API provides an endpoint to generate presigned URLs for uploading video files to S3.

### Endpoint Details

- **URL**: `https://{api-gateway-url}/prod/presigned-url`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Format

#### Request Body
```json
{
  "filename": "my-video.mp4",
  "jobId": "analysis-job-123",
  "contentType": "video/mp4"
}
```

#### Required Fields
- `filename` (string): The name of the video file to upload
  - Must include a valid video file extension (.mp4, .mov, .avi, .mkv, .webm)
  - Example: "security-footage-001.mp4"
- `jobId` (string): Unique identifier for the analysis job
  - Must contain only alphanumeric characters, dashes, and underscores
  - Will be included in the S3 file path for organization
  - Example: "analysis-job-123", "security-scan-2024-09-20"

#### Optional Fields
- `contentType` (string): MIME type of the video file
  - Default: "video/mp4"
  - Must start with "video/"
  - Examples: "video/mp4", "video/quicktime", "video/x-msvideo"

### Response Format

#### Success Response (200)
```json
{
  "presignedUrl": "https://bucket-name.s3.amazonaws.com/videos/analysis-job-123/original/my-video.mp4?X-Amz-Algorithm=...",
  "key": "videos/analysis-job-123/original/my-video.mp4",
  "bucket": "visionaree-video-bucket",
  "expiresIn": 3600
}
```

#### Error Response (400/500)
```json
{
  "error": "jobId is required in request body",
  "details": "Additional error information"
}
```

### Usage Examples

#### 1. JavaScript/Fetch
```javascript
// Step 1: Get presigned URL
const getPresignedUrl = async (filename, jobId, contentType = 'video/mp4') => {
  const response = await fetch('https://your-api-gateway-url/prod/presigned-url', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: filename,
      jobId: jobId,
      contentType: contentType
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
};

// Step 2: Upload file using presigned URL
const uploadFile = async (file, jobId) => {
  try {
    // Get presigned URL
    const { presignedUrl, key, bucket } = await getPresignedUrl(file.name, jobId, file.type);
    
    // Upload file to S3
    const uploadResponse = await fetch(presignedUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type
      }
    });
    
    if (uploadResponse.ok) {
      console.log('File uploaded successfully!');
      console.log('S3 Key:', key);
      console.log('S3 URI:', `s3://${bucket}/${key}`);
      return { success: true, s3Uri: `s3://${bucket}/${key}`, key };
    } else {
      throw new Error('Upload failed');
    }
  } catch (error) {
    console.error('Upload error:', error);
    return { success: false, error: error.message };
  }
};

// Usage with file input
document.getElementById('fileInput').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  const jobId = `analysis-${Date.now()}`; // Generate or get job ID
  
  if (file) {
    const result = await uploadFile(file, jobId);
    if (result.success) {
      // File uploaded successfully, you can now use result.s3Uri with Bedrock
      console.log('Ready for analysis:', result.s3Uri);
    }
  }
});
```

#### 2. Python
```python
import requests
import json

def get_presigned_url(api_url, filename, job_id, content_type='video/mp4'):
    """Get presigned URL for S3 upload"""
    response = requests.post(
        f"{api_url}/presigned-url",
        headers={'Content-Type': 'application/json'},
        json={
            'filename': filename,
            'jobId': job_id,
            'contentType': content_type
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get presigned URL: {response.text}")

def upload_file_to_s3(file_path, presigned_url, content_type):
    """Upload file using presigned URL"""
    with open(file_path, 'rb') as file:
        response = requests.put(
            presigned_url,
            data=file,
            headers={'Content-Type': content_type}
        )
    
    if response.status_code == 200:
        return True
    else:
        raise Exception(f"Upload failed: {response.status_code}")

# Usage example
def upload_video(api_url, video_file_path, job_id):
    try:
        filename = os.path.basename(video_file_path)
        
        # Get presigned URL
        result = get_presigned_url(api_url, filename, job_id)
        
        # Upload file
        upload_file_to_s3(
            video_file_path,
            result['presignedUrl'],
            'video/mp4'
        )
        
        print(f"Video uploaded successfully!")
        print(f"S3 URI: s3://{result['bucket']}/{result['key']}")
        
        return f"s3://{result['bucket']}/{result['key']}"
        
    except Exception as e:
        print(f"Upload failed: {e}")
        return None

# Example usage
api_url = "https://your-api-gateway-url/prod"
job_id = f"analysis-{int(time.time())}"  # Generate unique job ID
s3_uri = upload_video(api_url, "path/to/your/video.mp4", job_id)
```

#### 3. cURL
```bash
# Step 1: Get presigned URL
curl -X POST https://your-api-gateway-url/prod/presigned-url \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "security-footage.mp4",
    "jobId": "analysis-job-001",
    "contentType": "video/mp4"
  }'

# Response:
# {
#   "presignedUrl": "https://bucket.s3.amazonaws.com/videos/analysis-job-001/original/security-footage.mp4?...",
#   "key": "videos/analysis-job-001/original/security-footage.mp4",
#   "bucket": "visionaree-video-bucket",
#   "expiresIn": 3600
# }

# Step 2: Upload file using the presigned URL
curl -X PUT "https://bucket.s3.amazonaws.com/videos/analysis-job-001/original/security-footage.mp4?..." \
  -H "Content-Type: video/mp4" \
  --data-binary @security-footage.mp4
```

### Error Handling

The API returns these error conditions:

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Missing filename | The `filename` field is required |
| 400 | Missing jobId | The `jobId` field is required |
| 400 | Invalid jobId format | jobId must contain only alphanumeric characters, dashes, and underscores |
| 400 | Invalid file type | File extension not in allowed list |
| 400 | Invalid content type | Content type must start with "video/" |
| 500 | AWS error | S3 or internal server error |

### Security Notes

1. **File Type Validation**: Only video files are allowed (.mp4, .mov, .avi, .mkv, .webm)
2. **Content Type Validation**: Must start with "video/"
3. **Presigned URL Expiration**: URLs expire after 1 hour (3600 seconds)
4. **CORS**: Currently configured for all origins (configure for your domain in production)
5. **Server-Side Encryption**: Files are encrypted with AES256 when uploaded

### Integration with Visionaree Analysis

After uploading a video using the presigned URL, you can use the returned S3 URI with the main Visionaree analysis script:

```bash
# The S3 URI from the API response can be used directly
# Note: Files are now organized in videos/jobId/original/ structure
python main.py s3://visionaree-video-bucket/videos/analysis-job-001/original/security-footage.mp4 your-bucket-name
```

### Health Check Endpoint

- **URL**: `https://{api-gateway-url}/prod/health`
- **Method**: `GET`
- **Response**: `{"status": "healthy", "timestamp": "..."}`

This endpoint can be used to verify that the API is running correctly.

## Direct Video Inference Endpoint

For immediate analysis of short video segments without storing them permanently.

### Endpoint Details

- **URL**: `https://{api-gateway-url}/prod/video/analyze-direct`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data` or `video/*` or `application/octet-stream`

### Request Format

#### Option 1: Multipart Form Data
```http
POST /prod/video/analyze-direct
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...

------WebKitFormBoundary...
Content-Disposition: form-data; name="video"; filename="clip.mp4"
Content-Type: video/mp4

[binary video data]
------WebKitFormBoundary...--
```

#### Option 2: Direct Binary Upload
```http
POST /prod/video/analyze-direct
Content-Type: video/mp4
X-Filename: clip.mp4

[binary video data]
```

### Requirements and Limitations

- **File Size**: Maximum 50MB
- **Supported Formats**: MP4, MOV, MKV, WebM, AVI, FLV, MPEG, MPG, TS (supported by Bedrock Nova)
- **Processing**: Videos are used directly without re-encoding for faster response times
- **Bedrock Compatibility**: All supported formats are natively accepted by Bedrock Nova model

### Response Format

#### Success Response (200)
```json
{
  "success": true,
  "filename": "clip.mp4",
  "file_size": 2048576,
  "caption": "A person walks across a parking lot carrying a red backpack during daylight hours.",
  "status": "success"
}
```



#### Error Response (400/413/500)
```json
{
  "success": false,
  "error": "File too large. Maximum size is 50MB"
}
```

### Usage Examples

#### 1. JavaScript with FormData (Recommended)
```javascript
async function analyzeVideoDirectly(videoFile) {
  const formData = new FormData();
  formData.append('video', videoFile);
  
  try {
    const response = await fetch('https://your-api-gateway-url/prod/video/analyze-direct', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    
    if (result.success) {
          if (result.success) {
      console.log('Video analysis result:', result.caption);
      console.log('File size:', result.file_size, 'bytes');
    } else {
      console.error('Analysis failed:', result.error);
    }
      if (result.reencoded) {
        console.log('Video was re-encoded for compatibility');
      }
    } else {
      console.error('Analysis failed:', result.error);
    }
    
    return result;
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}

// Usage with file input
document.getElementById('videoInput').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (file && file.type.startsWith('video/')) {
    try {
      const result = await analyzeVideoDirectly(file);
      // Handle result
    } catch (error) {
      // Handle error
    }
  }
});
```

#### 2. JavaScript with Direct Binary Upload
```javascript
async function analyzeVideoBinary(videoFile) {
  try {
    const response = await fetch('https://your-api-gateway-url/prod/video/analyze-direct', {
      method: 'POST',
      headers: {
        'Content-Type': videoFile.type,
        'X-Filename': videoFile.name
      },
      body: videoFile
    });
    
    return await response.json();
  } catch (error) {
    console.error('Analysis failed:', error);
    throw error;
  }
}
```

#### 3. cURL Examples
```bash
# Using multipart form data
curl -X POST https://your-api-gateway-url/prod/video/analyze-direct \
  -H "Content-Type: multipart/form-data" \
  -F "video=@path/to/video.mp4"

# Using direct binary upload
curl -X POST https://your-api-gateway-url/prod/video/analyze-direct \
  -H "Content-Type: video/mp4" \
  -H "X-Filename: video.mp4" \
  --data-binary @path/to/video.mp4
```

#### 4. Python Example
```python
import requests

def analyze_video_direct(video_path):
    """Analyze video using direct inference endpoint"""
    
    with open(video_path, 'rb') as video_file:
        files = {'video': video_file}
        
        response = requests.post(
            'https://your-api-gateway-url/prod/video/analyze-direct',
            files=files
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"Analysis: {result['caption']}")
                print(f"File size: {result['file_size']} bytes")
                return result
            else:
                print(f"Analysis failed: {result['error']}")
        else:
            print(f"Request failed: {response.status_code}")
    
    return None

# Usage
result = analyze_video_direct("path/to/your/video.mp4")
```

### Video Processing

The endpoint processes videos for immediate Bedrock analysis:

1. **Direct Processing**: Videos are used in their original format for faster response
2. **Format Assumption**: Assumes videos are already in Bedrock-compatible format
3. **No Re-encoding**: Optimized for speed by skipping video conversion steps

### Error Handling

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Request body required | No video data in request |
| 400 | Unsupported content type | Content-Type not supported |
| 400 | Unsupported file format | File extension not in supported list (MP4, MOV, MKV, WebM, AVI, FLV, MPEG, MPG, TS) |
| 400 | No video data found | Could not extract video from request |
| 400 | File too small | File too small to be a valid video |
| 413 | File too large | Video exceeds 50MB limit |
| 500 | Processing error | Video processing or Bedrock inference failed |

### Performance Notes

- **Processing Time**: Typically 3-10 seconds (base64 encoding, no S3 upload/cleanup overhead)
- **Memory Usage**: Up to 1GB for video processing and base64 encoding
- **Concurrent Requests**: Limited by Lambda concurrency (can be adjusted)
- **Direct Processing**: Videos are encoded as base64 and sent directly to Bedrock (no S3 storage required)

### Security Considerations

- Videos are not permanently stored - they're deleted immediately after processing
- Temporary S3 objects are automatically cleaned up
- All processing happens in isolated Lambda environment
- API supports CORS for web applications

### Integration with Main Workflow

This endpoint is independent of the main video upload workflow (`/presigned-url` → S3 → Lambda processing). Use this for:
- Quick analysis of short clips
- Real-time video understanding
- Testing and development
- Mobile app integrations

For longer videos or when you need to store results permanently, use the main workflow instead.