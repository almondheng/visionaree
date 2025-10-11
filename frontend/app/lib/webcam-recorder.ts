import { analyzeVideoChunk } from './video-service'
import { reactive } from 'vue'

export interface RecordedChunk {
  blob: Blob
  startTime: number
  duration: number
  timestamp: number
  caption?: string
  captionError?: string
  captionProcessing?: boolean
  threat_level?: 'low' | 'medium' | 'high'
}

const DB_NAME = 'VisionareeDB'
const STORE_NAME = 'webcamChunks'
const RECORDING_ID = 'current-recording'

export class WebcamRecorder {
  private mediaRecorder: MediaRecorder | null = null
  private chunks = reactive<RecordedChunk[]>([])
  private currentChunkStartTime = 0
  private recordingStartTime = 0
  private chunkTimeout: ReturnType<typeof setTimeout> | null = null
  private isRecording = false
  private currentStream: MediaStream | null = null
  private dbInitialized = false
  private selectedMimeType = 'video/webm'

  async startRecording(stream: MediaStream) {
    await this.loadFromIndexedDB()
    this.currentStream = stream
    this.isRecording = true
    this.recordingStartTime = Date.now()

    // Use the same MIME type fallback logic as the working HTML version
    this.selectedMimeType = 'video/webm;codecs=vp9'
    if (!MediaRecorder.isTypeSupported(this.selectedMimeType)) {
      this.selectedMimeType = 'video/webm;codecs=vp8'
      if (!MediaRecorder.isTypeSupported(this.selectedMimeType)) {
        this.selectedMimeType = 'video/webm'
      }
    }

    console.log('WebcamRecorder: Selected MIME type:', this.selectedMimeType)
    console.log(
      'WebcamRecorder: WebM support:',
      MediaRecorder.isTypeSupported('video/webm')
    )

    // Start first 5-second segment with proper WebM headers
    this.startNewSegment()
  }

  stopRecording() {
    this.isRecording = false

    if (this.chunkTimeout) {
      clearTimeout(this.chunkTimeout)
      this.chunkTimeout = null
    }

    if (this.mediaRecorder) {
      if (this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop()
      }
      this.mediaRecorder = null
    }

    this.currentStream = null
  }

  getChunks(): RecordedChunk[] {
    const sorted = [...this.chunks].sort((a, b) => a.timestamp - b.timestamp)
    let accumulatedTime = 0
    return sorted.map(chunk => {
      const newChunk = {
        ...chunk,
        startTime: accumulatedTime,
      }
      accumulatedTime += chunk.duration
      return newChunk
    })
  }

  getTotalDuration(): number {
    return this.chunks.reduce((sum, chunk) => sum + chunk.duration, 0)
  }

  getChunkAtTime(time: number): RecordedChunk | null {
    return (
      this.chunks.find(
        chunk =>
          time >= chunk.startTime && time < chunk.startTime + chunk.duration
      ) || null
    )
  }

  getChunkCaptions(): Array<{
    timestamp: number
    startTime: number
    caption?: string
    captionError?: string
    captionProcessing?: boolean
    threat_level?: 'low' | 'medium' | 'high'
  }> {
    const sorted = [...this.chunks].sort((a, b) => a.timestamp - b.timestamp)
    let accumulatedTime = 0
    return sorted.map(chunk => {
      const result = {
        timestamp: chunk.timestamp,
        startTime: accumulatedTime,
        caption: chunk.caption,
        captionError: chunk.captionError,
        captionProcessing: chunk.captionProcessing,
        threat_level: chunk.threat_level,
      }
      accumulatedTime += chunk.duration
      return result
    })
  }

  getCaptionProcessingStatus(): {
    total: number
    processing: number
    completed: number
    failed: number
  } {
    const total = this.chunks.length
    const processing = this.chunks.filter(c => c.captionProcessing).length
    const completed = this.chunks.filter(
      c => c.caption && !c.captionProcessing
    ).length
    const failed = this.chunks.filter(
      c => c.captionError && !c.captionProcessing
    ).length

    return { total, processing, completed, failed }
  }

  clear() {
    this.chunks.splice(0, this.chunks.length)
    this.currentChunkStartTime = 0
    this.recordingStartTime = 0
  }

  private startNewSegment() {
    if (!this.isRecording || !this.currentStream) {
      return
    }

    // Create a new MediaRecorder for this 5-second segment - exactly like the HTML version
    this.mediaRecorder = new MediaRecorder(this.currentStream, {
      mimeType: this.selectedMimeType,
      videoBitsPerSecond: 500000, // 500 Kbps
    })

    // Collect data for this segment
    const segmentChunks: Blob[] = []
    const segmentStartTime = Date.now()

    this.mediaRecorder.ondataavailable = event => {
      if (event.data.size > 0) {
        segmentChunks.push(event.data)
      }
    }

    this.mediaRecorder.onstop = async () => {
      await this.processSegment(segmentChunks, segmentStartTime)
    }

    // Start recording exactly like the working HTML version
    this.mediaRecorder.start()
    console.log('WebcamRecorder: New 5-second segment started')

    // Schedule stop after 5 seconds
    this.chunkTimeout = setTimeout(() => {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop()
      }
    }, 5000)
  }

  private async processSegment(
    segmentChunks: Blob[],
    segmentStartTime: number
  ) {
    if (segmentChunks.length > 0) {
      // Create the segment blob exactly like the working HTML version
      const segmentBlob = new Blob(segmentChunks, { type: 'video/webm' })
      const actualDuration = (Date.now() - segmentStartTime) / 1000

      const chunk: RecordedChunk = {
        blob: segmentBlob,
        startTime: this.currentChunkStartTime,
        duration: actualDuration,
        timestamp: Date.now(),
        captionProcessing: true,
      }

      this.chunks.push(chunk)
      this.currentChunkStartTime += actualDuration

      // Save initial chunk to IndexedDB
      await this.saveChunkToIndexedDB(chunk)

      // Process caption in background (don't await to avoid blocking)
      this.processCaptionForChunk(chunk).catch((error: Error) => {
        console.error('Background caption processing failed:', error)
      })

      console.log(
        'WebcamRecorder: 5-second segment processed, duration:',
        actualDuration
      )
    }

    // Only start next segment if we're still recording
    if (this.isRecording) {
      this.startNewSegment() // Start next 5-second segment
    }
  }

  private async saveChunkToIndexedDB(chunk: RecordedChunk): Promise<void> {
    try {
      const db = await this.initDB()
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.close()
        return
      }
      const transaction = db.transaction([STORE_NAME], 'readwrite')
      const store = transaction.objectStore(STORE_NAME)

      // Store the actual blob along with metadata
      const chunkWithBlob = {
        blob: chunk.blob,
        startTime: chunk.startTime,
        duration: chunk.duration,
        timestamp: chunk.timestamp,
        caption: chunk.caption,
        captionError: chunk.captionError,
        captionProcessing: chunk.captionProcessing,
        threat_level: chunk.threat_level,
      }

      await new Promise<void>((resolve, reject) => {
        const request = store.put(chunkWithBlob, chunk.timestamp)
        request.onsuccess = () => resolve()
        request.onerror = () =>
          reject(request.error || 'Unknown IndexedDB error')
      })

      db.close()
    } catch (error) {
      // Silently handle IndexedDB errors to avoid console spam
    }
  }

  private async processCaptionForChunk(chunk: RecordedChunk): Promise<void> {
    try {
      // Generate a filename based on timestamp
      const filename = `chunk-${chunk.timestamp}.webm`

      // Call the inference API
      const response = await analyzeVideoChunk(chunk.blob, filename)

      if (response.success) {
        // Update chunk with caption directly in the reactive array
        const chunkIndex = this.chunks.findIndex(
          c => c.timestamp === chunk.timestamp
        )
        if (chunkIndex !== -1) {
          const chunk = this.chunks[chunkIndex]
          if (chunk) {
            chunk.caption = response.caption
            chunk.threat_level = response.threat_level
            chunk.captionProcessing = false
            delete chunk.captionError
            await this.saveChunkToIndexedDB(chunk)
          }
        }

        console.log(
          `Caption generated for chunk ${chunk.timestamp}:`,
          response.caption
        )
      } else {
        throw new Error('API returned unsuccessful response')
      }
    } catch (error) {
      console.error('Failed to process caption for chunk:', error)

      // Update chunk with error directly in the reactive array
      const chunkIndex = this.chunks.findIndex(
        c => c.timestamp === chunk.timestamp
      )
      if (chunkIndex !== -1) {
        const chunk = this.chunks[chunkIndex]
        if (chunk) {
          chunk.captionError =
            error instanceof Error ? error.message : 'Unknown error'
          chunk.captionProcessing = false
          await this.saveChunkToIndexedDB(chunk)
        }
      }
    }
  }

  private async initDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 2)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)

      request.onupgradeneeded = event => {
        const db = (event.target as IDBOpenDBRequest).result
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME)
        }
      }
    })
  }

  async saveToIndexedDB(): Promise<void> {
    try {
      const db = await this.initDB()
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.close()
        return
      }
      const transaction = db.transaction([STORE_NAME], 'readwrite')
      const store = transaction.objectStore(STORE_NAME)

      for (const chunk of this.chunks) {
        const chunkWithBlob = {
          blob: chunk.blob,
          startTime: chunk.startTime,
          duration: chunk.duration,
          timestamp: chunk.timestamp,
          caption: chunk.caption,
          captionError: chunk.captionError,
          captionProcessing: chunk.captionProcessing,
        }

        await new Promise<void>((resolve, reject) => {
          const request = store.put(chunkWithBlob, chunk.timestamp)
          request.onsuccess = () => resolve()
          request.onerror = () =>
            reject(request.error || 'Unknown IndexedDB error')
        })
      }

      db.close()
    } catch (error) {
      // Silently handle IndexedDB errors
    }
  }

  async loadFromIndexedDB(): Promise<void> {
    // Don't load from IndexedDB on startup to avoid empty blobs
    // Only load metadata when needed
  }

  async loadChunksForPlayback(): Promise<RecordedChunk[]> {
    try {
      const db = await this.initDB()
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.close()
        return this.chunks.filter(chunk => chunk.blob.size > 0)
      }
      const transaction = db.transaction([STORE_NAME], 'readonly')
      const store = transaction.objectStore(STORE_NAME)

      const chunks = await new Promise<any[]>((resolve, reject) => {
        const request = store.openCursor()
        const results: any[] = []
        request.onsuccess = event => {
          const cursor = (event.target as IDBRequest<IDBCursorWithValue | null>)
            .result
          if (cursor) {
            results.push(cursor.value)
            cursor.continue()
          } else {
            resolve(results)
          }
        }
        request.onerror = () => reject(request.error)
      })

      db.close()

      // Return chunks with actual blobs, sorted by timestamp
      return chunks
        .filter(chunk => chunk.blob && chunk.blob.size > 0)
        .sort((a, b) => a.timestamp - b.timestamp)
    } catch (error) {
      console.error('Failed to load chunks for playback:', error)
      // Fallback to current chunks that have blobs
      return this.chunks.filter(chunk => chunk.blob.size > 0)
    }
  }

  async clearFromIndexedDB(): Promise<void> {
    try {
      const db = await this.initDB()
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.close()
        return
      }
      const transaction = db.transaction([STORE_NAME], 'readwrite')
      const store = transaction.objectStore(STORE_NAME)

      await new Promise<void>((resolve, reject) => {
        const request = store.clear()
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })

      db.close()
    } catch (error) {
      console.error('Failed to clear from IndexedDB:', error)
    }
  }
}
