export interface VideoMetadata {
  duration: number
  width: number
  height: number
  thumbnail: string
}

export const generateVideoThumbnail = (file: File): Promise<VideoMetadata> => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    if (!ctx) {
      reject(new Error('Canvas context not available'))
      return
    }
    
    video.preload = 'metadata'
    video.muted = true
    
    video.onloadedmetadata = () => {
      // Set canvas dimensions
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      
      // Seek to 10% of video duration for thumbnail
      video.currentTime = video.duration * 0.1
    }
    
    video.onseeked = () => {
      try {
        // Draw video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        
        // Convert canvas to data URL
        const thumbnail = canvas.toDataURL('image/jpeg', 0.8)
        
        resolve({
          duration: video.duration,
          width: video.videoWidth,
          height: video.videoHeight,
          thumbnail
        })
        
        // Clean up
        URL.revokeObjectURL(video.src)
      } catch (error) {
        reject(new Error('Failed to generate thumbnail'))
      }
    }
    
    video.onerror = () => {
      reject(new Error('Failed to load video'))
    }
    
    // Create object URL and load video
    video.src = URL.createObjectURL(file)
  })
}

export const createVideoBlob = async (file: File): Promise<Blob> => {
  // In a real app, you might want to compress or process the video here
  // For now, we'll just return the original file
  return file
}

export const getVideoFileInfo = (file: File) => {
  return {
    filename: file.name,
    size: file.size,
    type: file.type,
    title: file.name.replace(/\.[^/.]+$/, '') // Remove file extension
  }
}