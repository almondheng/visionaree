import { videoDatabase, type VideoRecord } from './db'
import { generateVideoThumbnail, createVideoBlob, getVideoFileInfo } from './video-utils'

export class VideoProcessingService {
  async processVideo(file: File): Promise<string> {
    try {
      // Get basic file info
      const fileInfo = getVideoFileInfo(file)
      
      // Create initial video record
      const videoId = await videoDatabase.addVideo({
        ...fileInfo,
        uploadedAt: new Date(),
        processingStatus: 'pending'
      })
      
      // Start processing in background
      this.processVideoInBackground(videoId, file)
      
      return videoId
    } catch (error) {
      console.error('Failed to start video processing:', error)
      throw new Error('Failed to process video')
    }
  }
  
  private async processVideoInBackground(videoId: string, file: File): Promise<void> {
    try {
      // Update status to processing
      await videoDatabase.updateVideo(videoId, {
        processingStatus: 'processing'
      })
      
      // Generate thumbnail and metadata
      const metadata = await generateVideoThumbnail(file)
      
      // Create video blob for storage
      const videoBlob = await createVideoBlob(file)
      
      // Simulate backend upload (placeholder)
      await this.simulateBackendUpload(file)
      
      // Update video record with processed data
      await videoDatabase.updateVideo(videoId, {
        duration: metadata.duration,
        thumbnail: metadata.thumbnail,
        videoBlob,
        processingStatus: 'completed'
      })
      
      console.log(`Video ${videoId} processed successfully`)
    } catch (error) {
      console.error(`Failed to process video ${videoId}:`, error)
      
      // Update status to error
      await videoDatabase.updateVideo(videoId, {
        processingStatus: 'error'
      })
    }
  }
  
  private async simulateBackendUpload(file: File): Promise<void> {
    // Placeholder for backend upload
    // In a real implementation, this would upload the file to your backend
    return new Promise((resolve) => {
      setTimeout(() => {
        console.log(`Simulated upload of ${file.name} to backend`)
        resolve()
      }, 1000 + Math.random() * 2000) // Random delay between 1-3 seconds
    })
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
        type: video.videoBlob.type 
      })
      
      await this.processVideoInBackground(id, file)
    } catch (error) {
      console.error(`Failed to retry processing for video ${id}:`, error)
      throw new Error('Failed to retry processing')
    }
  }
}

export const videoProcessingService = new VideoProcessingService()