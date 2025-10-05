import { analyzeVideoChunk } from './video-service'

export interface RecordedChunk {
  blob: Blob
  startTime: number
  duration: number
  timestamp: number
  caption?: string
  captionError?: string
  captionProcessing?: boolean
}

const DB_NAME = 'VisionareeDB'
const STORE_NAME = 'webcamChunks'
const RECORDING_ID = 'current-recording'

export class WebcamRecorder {
  private mediaRecorder: MediaRecorder | null = null
  private chunks: RecordedChunk[] = []
  private currentChunkStartTime = 0
  private recordingStartTime = 0
  private chunkInterval: ReturnType<typeof setInterval> | null = null
  private dbInitialized = false

  async startRecording(stream: MediaStream) {
    await this.loadFromIndexedDB()
    this.recordingStartTime = Date.now()

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm')
      ? 'video/webm'
      : ''

    this.mediaRecorder = new MediaRecorder(
      stream,
      mimeType ? { mimeType } : undefined
    )

    this.mediaRecorder.ondataavailable = async event => {
      if (event.data.size > 0) {
        const actualDuration = (Date.now() - this.recordingStartTime) / 1000
        const chunk: RecordedChunk = {
          blob: event.data,
          startTime: this.currentChunkStartTime,
          duration: actualDuration,
          timestamp: Date.now(),
          captionProcessing: true,
        }
        this.chunks.push(chunk)
        this.currentChunkStartTime += actualDuration
        this.recordingStartTime = Date.now()

        // Save initial chunk to IndexedDB
        await this.saveChunkToIndexedDB(chunk)

        // Process caption in background (don't await to avoid blocking)
        this.processCaptionForChunk(chunk).catch((error: Error) => {
          console.error('Background caption processing failed:', error)
        })
      }
    }

    this.mediaRecorder.start()

    this.chunkInterval = setInterval(() => {
      if (this.mediaRecorder?.state === 'recording') {
        this.mediaRecorder.requestData()
      }
    }, 5000)
  }

  stopRecording() {
    if (this.chunkInterval) {
      clearInterval(this.chunkInterval)
      this.chunkInterval = null
    }

    if (this.mediaRecorder) {
      if (this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop()
      }
      this.mediaRecorder = null
    }
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
    caption?: string
    captionError?: string
    captionProcessing?: boolean
  }> {
    return this.chunks.map(chunk => ({
      timestamp: chunk.timestamp,
      caption: chunk.caption,
      captionError: chunk.captionError,
      captionProcessing: chunk.captionProcessing,
    }))
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
    this.chunks = []
    this.currentChunkStartTime = 0
    this.recordingStartTime = 0
  }

  private async saveChunkToIndexedDB(chunk: RecordedChunk): Promise<void> {
    try {
      const db = await this.initDB()
      if (db.objectStoreNames.contains(STORE_NAME)) {
        const transaction = db.transaction([STORE_NAME], 'readwrite')
        const store = transaction.objectStore(STORE_NAME)
        await new Promise<void>((resolve, reject) => {
          const request = store.put(chunk, chunk.timestamp)
          request.onsuccess = () => resolve()
          request.onerror = () => reject(request.error)
        })
      }
      db.close()
    } catch (error) {
      console.error('Failed to save chunk to IndexedDB:', error)
    }
  }

  private async processCaptionForChunk(chunk: RecordedChunk): Promise<void> {
    try {
      // Generate a filename based on timestamp
      const filename = `chunk-${chunk.timestamp}.webm`

      // Call the inference API
      const response = await analyzeVideoChunk(chunk.blob, filename)

      if (response.success) {
        // Update chunk with caption
        chunk.caption = response.caption
        chunk.captionProcessing = false
        delete chunk.captionError

        // Update the chunk in the array
        const chunkIndex = this.chunks.findIndex(
          c => c.timestamp === chunk.timestamp
        )
        if (chunkIndex !== -1) {
          this.chunks[chunkIndex] = chunk
        }

        // Save updated chunk to IndexedDB
        await this.saveChunkToIndexedDB(chunk)

        console.log(
          `Caption generated for chunk ${chunk.timestamp}:`,
          response.caption
        )
      } else {
        throw new Error('API returned unsuccessful response')
      }
    } catch (error) {
      console.error('Failed to process caption for chunk:', error)

      // Update chunk with error
      chunk.captionError =
        error instanceof Error ? error.message : 'Unknown error'
      chunk.captionProcessing = false

      // Update the chunk in the array
      const chunkIndex = this.chunks.findIndex(
        c => c.timestamp === chunk.timestamp
      )
      if (chunkIndex !== -1) {
        this.chunks[chunkIndex] = chunk
      }

      // Save updated chunk to IndexedDB
      await this.saveChunkToIndexedDB(chunk)
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
        await new Promise<void>((resolve, reject) => {
          const request = store.put(chunk, chunk.timestamp)
          request.onsuccess = () => resolve()
          request.onerror = () => reject(request.error)
        })
      }

      db.close()
    } catch (error) {
      console.error('Failed to save to IndexedDB:', error)
    }
  }

  async loadFromIndexedDB(): Promise<void> {
    try {
      const db = await this.initDB()
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.close()
        return
      }
      const transaction = db.transaction([STORE_NAME], 'readonly')
      const store = transaction.objectStore(STORE_NAME)

      const chunks = await new Promise<RecordedChunk[]>((resolve, reject) => {
        const request = store.openCursor()
        const results: RecordedChunk[] = []
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

      if (chunks.length > 0) {
        this.chunks = chunks
        const sorted = chunks.sort((a, b) => a.timestamp - b.timestamp)
        const lastChunk = sorted[sorted.length - 1]
        if (lastChunk) {
          this.currentChunkStartTime = lastChunk.startTime + lastChunk.duration
        }
      }

      db.close()
    } catch (error) {
      // Silently handle - no existing recording
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
