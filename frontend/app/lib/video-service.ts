import { videoDatabase, type VideoRecord } from './db'
import {
  generateVideoThumbnail,
  createVideoBlob,
  getVideoFileInfo,
} from './video-utils'

// API Configuration
const API_BASE_URL =
  'https://g6mq8j3qre.execute-api.us-east-1.amazonaws.com/prod'

// Types for API responses
interface PresignedUrlResponse {
  presignedUrl: string
  key: string
  bucket: string
  expiresIn: number
}

interface PresignedUrlRequest {
  filename: string
  jobId: string
  contentType: string
}

interface VideoQueryRequest {
  query: string
}

export interface FilteredSegment {
  segmentStartTime: string
  caption: string
  timestamp: string
  metadata: {
    inference_timestamp: string
    status: string
    model_id: string
  }
  relevance_score: number
  relevance_reason: string
  threat_level: 'low' | 'medium' | 'high'
}

interface JobInfo {
  videoFileName: string
  videoDuration: string
  totalSegments: string
  processedSegments: string
  jobStatus: string
}

interface AiAnalysis {
  status: string
  filtered_segments: FilteredSegment[]
  insights: string
  total_relevant_segments: number
}

export interface VideoQueryResponse {
  jobId: string
  status: string
  query: string
  jobInfo: JobInfo
  ai_analysis: AiAnalysis
}

// API service functions
export async function getPresignedUrl(
  filename: string,
  jobId: string,
  contentType: string
): Promise<PresignedUrlResponse> {
  const response = await fetch(`${API_BASE_URL}/presigned-url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename,
      jobId,
      contentType,
    } as PresignedUrlRequest),
  })

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export async function queryVideo(
  jobId: string,
  query: string
): Promise<VideoQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/video/${jobId}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
    } as VideoQueryRequest),
  })

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

// Types for video status check
interface VideoStatusResponse {
  status: 'done' | 'processing' | 'pending' | 'error'
}

export async function checkVideoStatus(
  jobId: string
): Promise<VideoStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/video/${jobId}/status`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export async function uploadFileToS3(
  presignedUrl: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    // Track upload progress
    if (onProgress) {
      xhr.upload.addEventListener('progress', event => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100)
          onProgress(progress)
        }
      })
    }

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve()
      } else {
        reject(new Error(`Upload failed with status: ${xhr.status}`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed due to network error'))
    })

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload was aborted'))
    })

    xhr.open('PUT', presignedUrl)
    xhr.setRequestHeader('Content-Type', file.type)
    xhr.send(file)
  })
}

export async function uploadVideoToS3(
  videoId: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<{ s3Uri: string; key: string; bucket: string }> {
  // Generate a unique job ID
  const jobId = `upload-${videoId}`

  try {
    // Get presigned URL
    const { presignedUrl, key, bucket } = await getPresignedUrl(
      file.name,
      jobId,
      file.type
    )

    // Upload file to S3
    await uploadFileToS3(presignedUrl, file, onProgress)

    // Return S3 URI and metadata
    const s3Uri = `s3://${bucket}/${key}`
    return { s3Uri, key, bucket }
  } catch (error) {
    console.error('Upload to S3 failed:', error)
    throw error
  }
}

export class VideoProcessingService {
  async processVideo(file: File): Promise<string> {
    try {
      // Get basic file info
      const fileInfo = getVideoFileInfo(file)

      // Create initial video record
      const videoId = await videoDatabase.addVideo({
        ...fileInfo,
        uploadedAt: new Date(),
        processingStatus: 'pending',
      })

      // Start processing in background
      this.processVideoInBackground(videoId, file)

      return videoId
    } catch (error) {
      console.error('Failed to start video processing:', error)
      throw new Error('Failed to process video')
    }
  }

  private async processVideoInBackground(
    videoId: string,
    file: File
  ): Promise<void> {
    try {
      // Update status to processing
      await videoDatabase.updateVideo(videoId, {
        processingStatus: 'processing',
      })

      // Generate thumbnail and metadata
      const metadata = await generateVideoThumbnail(file)

      // Upload to S3 using presigned URL
      const uploadResult = await uploadVideoToS3(videoId, file, progress => {
        console.log(`Upload progress for ${videoId}: ${progress}%`)
      })

      // Create video blob for local storage (optional - you might want to remove this for large files)
      const videoBlob = await createVideoBlob(file)

      // Update video record with processed data
      await videoDatabase.updateVideo(videoId, {
        duration: metadata.duration,
        thumbnail: metadata.thumbnail,
        videoBlob,
        s3Uri: uploadResult.s3Uri,
        processingStatus: 'completed',
      })

      console.log(
        `Video ${videoId} processed and uploaded successfully to ${uploadResult.s3Uri}`
      )
    } catch (error) {
      console.error(`Failed to process video ${videoId}:`, error)

      // Update status to error
      await videoDatabase.updateVideo(videoId, {
        processingStatus: 'error',
      })
    }
  }

  async getAllVideos(): Promise<VideoRecord[]> {
    try {
      return await videoDatabase.getAllVideos()
    } catch (error) {
      console.error('Failed to fetch videos:', error)
      return []
    }
  }

  async getVideo(id: string): Promise<VideoRecord | null> {
    try {
      return await videoDatabase.getVideo(id)
    } catch (error) {
      console.error(`Failed to fetch video ${id}:`, error)
      return null
    }
  }

  async deleteVideo(id: string): Promise<void> {
    try {
      await videoDatabase.deleteVideo(id)
      console.log(`Video ${id} deleted successfully`)
    } catch (error) {
      console.error(`Failed to delete video ${id}:`, error)
      throw new Error('Failed to delete video')
    }
  }

  async retryProcessing(id: string): Promise<void> {
    try {
      const video = await videoDatabase.getVideo(id)
      if (!video || !video.videoBlob) {
        throw new Error('Video not found or no video data available')
      }

      // Convert blob back to file for reprocessing
      const file = new File([video.videoBlob], video.filename, {
        type: video.videoBlob.type,
      })

      await this.processVideoInBackground(id, file)
    } catch (error) {
      console.error(`Failed to retry processing for video ${id}:`, error)
      throw new Error('Failed to retry processing')
    }
  }

  async checkBackendStatus(
    videoId: string
  ): Promise<'done' | 'processing' | 'pending' | 'error'> {
    try {
      // Use the format: upload-{videoId} for the job ID as defined in uploadVideoToS3
      const jobId = `upload-${videoId}`
      const statusResponse = await checkVideoStatus(jobId)
      return statusResponse.status
    } catch (error) {
      console.error(
        `Failed to check backend status for video ${videoId}:`,
        error
      )
      // Return 'processing' as default to keep polling
      return 'processing'
    }
  }
}

export const videoProcessingService = new VideoProcessingService()
