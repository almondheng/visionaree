export interface VideoRecord {
  id?: string
  filename: string
  title: string
  size: number
  duration?: number
  thumbnail?: string
  uploadedAt: Date
  processingStatus: 'pending' | 'processing' | 'completed' | 'error'
  videoBlob?: Blob
}

class VideoDatabase {
  private db: IDBDatabase | null = null
  private readonly dbName = 'VisionareeDB'
  private readonly dbVersion = 1
  private readonly storeName = 'videos'

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result
        
        if (!db.objectStoreNames.contains(this.storeName)) {
          const store = db.createObjectStore(this.storeName, { 
            keyPath: 'id', 
            autoIncrement: true 
          })
          store.createIndex('filename', 'filename', { unique: false })
          store.createIndex('uploadedAt', 'uploadedAt', { unique: false })
        }
      }
    })
  }

  async addVideo(video: Omit<VideoRecord, 'id'>): Promise<string> {
    if (!this.db) await this.init()
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite')
      const store = transaction.objectStore(this.storeName)
      
      const request = store.add({
        ...video,
        id: crypto.randomUUID()
      })
      
      request.onsuccess = () => resolve(request.result as string)
      request.onerror = () => reject(request.error)
    })
  }

  async getAllVideos(): Promise<VideoRecord[]> {
    if (!this.db) await this.init()
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly')
      const store = transaction.objectStore(this.storeName)
      const index = store.index('uploadedAt')
      
      // Open cursor in descending order (prev = descending)
      const request = index.openCursor(null, 'prev')
      const videos: VideoRecord[] = []
      
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result
        if (cursor) {
          videos.push(cursor.value)
          cursor.continue()
        } else {
          resolve(videos)
        }
      }
      
      request.onerror = () => reject(request.error)
    })
  }

  async getVideo(id: string): Promise<VideoRecord | null> {
    if (!this.db) await this.init()
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly')
      const store = transaction.objectStore(this.storeName)
      const request = store.get(id)
      
      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  async updateVideo(id: string, updates: Partial<VideoRecord>): Promise<void> {
    if (!this.db) await this.init()
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite')
      const store = transaction.objectStore(this.storeName)
      
      const getRequest = store.get(id)
      getRequest.onsuccess = () => {
        const video = getRequest.result
        if (!video) {
          reject(new Error('Video not found'))
          return
        }
        
        const updatedVideo = { ...video, ...updates }
        const putRequest = store.put(updatedVideo)
        
        putRequest.onsuccess = () => resolve()
        putRequest.onerror = () => reject(putRequest.error)
      }
      getRequest.onerror = () => reject(getRequest.error)
    })
  }

  async deleteVideo(id: string): Promise<void> {
    if (!this.db) await this.init()
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite')
      const store = transaction.objectStore(this.storeName)
      const request = store.delete(id)
      
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }
}

export const videoDatabase = new VideoDatabase()