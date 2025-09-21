<template>
  <div class="container mx-auto">
    <!-- Back button -->
    <div class="mb-6">
      <Button
        variant="ghost"
        @click="$router.push('/')"
        class="flex items-center gap-2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Videos
      </Button>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="text-center py-8">
      <div
        class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"
      ></div>
      <p class="text-gray-600 dark:text-gray-400">Loading video...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error || !video" class="text-center py-8">
      <div class="text-red-500 mb-4">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-12 w-12 mx-auto"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
        Video not found
      </h2>
      <p class="text-gray-600 dark:text-gray-400 mb-4">
        The video you're looking for doesn't exist or has been deleted.
      </p>
      <Button @click="$router.push('/')">Go back to videos</Button>
    </div>

    <!-- Video detail view -->
    <div v-else class="flex flex-col gap-8">
      <!-- Video player and prompt section -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <!-- Video player section -->
        <div class="xl:col-span-2 h-full max-h-[500px]">
          <Card class="py-0 h-full">
            <CardContent class="p-0 h-full">
              <div
                class="bg-gray-100 dark:bg-gray-800 relative overflow-hidden rounded-lg h-full"
              >
                <!-- Video player for completed videos -->
                <video
                  v-if="
                    video.processingStatus === 'completed' && video.videoBlob
                  "
                  ref="videoPlayer"
                  class="w-full h-full object-contain"
                  autoplay
                  @loadedmetadata="onVideoLoaded"
                  @timeupdate="onTimeUpdate"
                  @error="onVideoError"
                  @loadstart="onLoadStart"
                  @canplay="onCanPlay"
                  @play="onPlay"
                  @pause="onPause"
                  @click="togglePlayPause"
                >
                  Your browser does not support the video tag.
                </video>

                <!-- Video progress overlay -->
                <div
                  v-if="
                    video.processingStatus === 'completed' && video.videoBlob
                  "
                  class="absolute bottom-0 left-0 right-0 p-2"
                >
                  <!-- Minimal progress bar -->
                  <div class="bg-black/30 backdrop-blur-sm rounded px-3 py-1.5">
                    <!-- Progress slider -->
                    <div class="flex items-center gap-2">
                      <!-- Play/Pause button -->
                      <button
                        @click="togglePlayPause"
                        class="flex items-center justify-center w-6 h-6 bg-white/20 hover:bg-white/30 rounded transition-all duration-200 text-white flex-shrink-0"
                      >
                        <!-- Play icon -->
                        <svg
                          v-if="!isPlaying"
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-3 w-3"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M8 5v14l11-7z" />
                        </svg>
                        <!-- Pause icon -->
                        <svg
                          v-else
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-3 w-3"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                        </svg>
                      </button>

                      <!-- Time display -->
                      <span
                        class="text-white text-xs font-medium whitespace-nowrap"
                      >
                        {{ formatDuration(currentTime) }}
                      </span>

                      <!-- Progress slider -->
                      <Slider
                        :model-value="progress"
                        :max="duration"
                        :step="1"
                        class="flex-1 cursor-pointer"
                        @update:model-value="onProgressChange"
                      />

                      <!-- Duration -->
                      <span
                        class="text-white text-xs font-medium whitespace-nowrap"
                      >
                        {{ formatDuration(duration) }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Thumbnail for non-completed videos -->
                <div
                  v-else
                  class="w-full h-full flex items-center justify-center min-h-[400px]"
                >
                  <img
                    v-if="video.thumbnail"
                    :src="video.thumbnail"
                    :alt="video.title"
                    class="w-full h-full object-cover"
                  />
                  <div v-else class="text-gray-400">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-24 w-24"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                </div>

                <!-- Processing overlay -->
                <div
                  v-if="video.processingStatus === 'processing'"
                  class="absolute inset-0 bg-black/50 flex items-center justify-center"
                >
                  <div class="text-white text-center">
                    <div
                      class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-4 mx-auto"
                    ></div>
                    <p class="text-lg">Processing video...</p>
                    <p class="text-sm text-gray-300">
                      This may take a few minutes
                    </p>
                  </div>
                </div>

                <!-- Error overlay -->
                <div
                  v-if="video.processingStatus === 'error'"
                  class="absolute inset-0 bg-red-500/20 flex items-center justify-center"
                >
                  <div class="text-white text-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-8 w-8 mx-auto mb-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <p class="text-lg">Processing failed</p>
                    <Button
                      variant="outline"
                      size="sm"
                      class="mt-2 bg-white/10 border-white/20 text-white hover:bg-white/20"
                      @click="retryProcessing"
                    >
                      Retry
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Video prompt section -->
        <div class="xl:col-span-1 h-full max-h-[500px]">
          <!-- Show skeleton loader when backend is not ready -->
          <VideoPromptSkeleton v-if="video?.id && !isBackendReady" />

          <!-- Show actual prompt when backend is ready -->
          <VideoPrompt
            v-else-if="video?.id && isBackendReady"
            ref="videoPromptRef"
            :video-id="video.id"
            @seek-to-timestamp="seekToTimestamp"
          />

          <!-- Loading fallback -->
          <div v-else class="h-full flex items-center justify-center">
            <p class="text-muted-foreground">Loading video...</p>
          </div>
        </div>
      </div>

      <!-- Video information -->
      <div>
        <Card>
          <CardHeader>
            <CardTitle class="text-2xl">{{ video?.title }}</CardTitle>
            <CardDescription class="text-base">
              Video details and information
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                >
                  Filename
                </label>
                <p class="text-sm">{{ video?.filename }}</p>
              </div>
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                >
                  File Size
                </label>
                <p class="text-sm">
                  {{ video?.size ? formatFileSize(video.size) : 'Unknown' }}
                </p>
              </div>
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                >
                  Duration
                </label>
                <p class="text-sm">
                  {{
                    video?.duration ? formatDuration(video.duration) : 'Unknown'
                  }}
                </p>
              </div>
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                >
                  Uploaded
                </label>
                <p class="text-sm">
                  {{
                    video?.uploadedAt ? formatDate(video.uploadedAt) : 'Unknown'
                  }}
                </p>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex gap-3 pt-4 border-t">
              <Button
                variant="outline"
                @click="downloadVideo"
                :disabled="video?.processingStatus !== 'completed'"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Download
              </Button>

              <Button variant="destructive" @click="deleteVideo">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Delete Video
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThrottleFn } from '@vueuse/core'
import { toast } from 'vue-sonner'
import { Button } from '~/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '~/components/ui/card'
import VideoPrompt from '~/components/VideoPrompt.vue'
import VideoPromptSkeleton from '~/components/VideoPromptSkeleton.vue'
import { Slider } from '~/components/ui/slider'
import { videoProcessingService, checkVideoStatus } from '~/lib/video-service'
import type { VideoRecord } from '~/lib/db'

// Router
const route = useRoute()
const router = useRouter()

// Reactive state
const video = ref<VideoRecord | null>(null)
const isLoading = ref(true)
const error = ref(false)
const videoPlayer = ref<HTMLVideoElement>()

// Backend processing status
const backendStatus = ref<'done' | 'processing' | 'pending' | 'error'>(
  'processing'
)
const isBackendReady = computed(() => backendStatus.value === 'done')

// Video overlay state
const currentTime = ref(0)
const duration = ref(0)
const isPlaying = ref(false)
const progress = ref([0])

// Auto-refresh for processing status
let refreshInterval: ReturnType<typeof setInterval> | null = null
let statusPollingInterval: ReturnType<typeof setInterval> | null = null

// Auto-prompting state
const hasAutoPrompted = ref(false)
const videoPromptRef = ref<InstanceType<typeof VideoPrompt> | null>(null)

// Lifecycle
onMounted(async () => {
  await loadVideo()
  startAutoRefresh()
  startStatusPolling()
})

// Watch for video changes and setup player
watch(
  [video, videoPlayer],
  async () => {
    if (
      video.value?.processingStatus === 'completed' &&
      video.value?.videoBlob &&
      videoPlayer.value
    ) {
      await nextTick()
      console.log('Watcher triggered - setting up video player')
      setupVideoPlayer()
    }
  },
  { immediate: false }
)

// Watch for backend status changes to trigger auto-prompting
watch(
  backendStatus,
  async (newStatus, oldStatus) => {
    if (
      newStatus === 'done' &&
      oldStatus !== 'done' &&
      !hasAutoPrompted.value &&
      videoPromptRef.value
    ) {
      console.log('Backend is ready, triggering auto-prompt...')
      hasAutoPrompted.value = true
      
      // Wait a bit for the VideoPrompt component to be fully mounted
      await nextTick()
      
      try {
        // Trigger the example prompt automatically
        await videoPromptRef.value.submitSuggestedPrompt('Identify suspicious activities')
        toast('Auto-analyzing video for suspicious activities...')
      } catch (error) {
        console.error('Failed to trigger auto-prompt:', error)
      }
    }
  }
)

onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
  }
  // Clean up video blob URL if exists
  if (videoPlayer.value?.src) {
    URL.revokeObjectURL(videoPlayer.value.src)
  }
})

// Methods
const loadVideo = async () => {
  try {
    isLoading.value = true
    error.value = false
    hasAutoPrompted.value = false // Reset auto-prompt flag for new video

    const videoId = route.params.id as string
    const videoData = await videoProcessingService.getVideo(videoId)

    if (!videoData) {
      error.value = true
      return
    }

    video.value = videoData

    // Check initial backend status if video is uploaded
    if (videoData.processingStatus === 'completed' && videoData.s3Uri) {
      try {
        const jobId = `upload-${videoId}`
        const statusResponse = await checkVideoStatus(jobId)
        backendStatus.value = statusResponse.status
      } catch (statusError) {
        console.error('Failed to check initial backend status:', statusError)
        backendStatus.value = 'processing'
      }
    }

    // Set up video player if video is ready
    if (videoData.processingStatus === 'completed' && videoData.videoBlob) {
      await nextTick()
      console.log('Video is completed, setting up player...')
      setupVideoPlayer()
    } else {
      console.log('Video not ready for playback:', {
        status: videoData.processingStatus,
        hasBlob: !!videoData.videoBlob,
      })
    }
  } catch (err) {
    console.error('Error loading video:', err)
    error.value = true
  } finally {
    isLoading.value = false
  }
}

const setupVideoPlayer = () => {
  if (!video.value?.videoBlob || !videoPlayer.value) {
    console.log('Cannot setup video player:', {
      hasBlob: !!video.value?.videoBlob,
      hasPlayerRef: !!videoPlayer.value,
    })
    return
  }

  // Clean up existing URL if any
  if (videoPlayer.value.src) {
    URL.revokeObjectURL(videoPlayer.value.src)
  }

  // Create object URL for the video blob
  const videoUrl = URL.createObjectURL(video.value.videoBlob)
  console.log('Setting video URL:', videoUrl)
  videoPlayer.value.src = videoUrl

  // Force load the video
  videoPlayer.value.load()
}

const onVideoLoaded = () => {
  console.log('Video loaded successfully', {
    duration: videoPlayer.value?.duration,
    videoWidth: videoPlayer.value?.videoWidth,
    videoHeight: videoPlayer.value?.videoHeight,
    readyState: videoPlayer.value?.readyState,
  })

  // Update duration for overlay
  if (videoPlayer.value?.duration) {
    duration.value = videoPlayer.value.duration
  }
}

const onTimeUpdate = useThrottleFn(() => {
  if (videoPlayer.value && videoPlayer.value.duration) {
    currentTime.value = videoPlayer.value.currentTime
    progress.value = [videoPlayer.value.currentTime]

    const progressPercent =
      (videoPlayer.value.currentTime / videoPlayer.value.duration) * 100
    // Could emit progress for future annotation features
    const currentTimeInSeconds = videoPlayer.value.currentTime
    console.log(
      `Video progress: ${progressPercent.toFixed(
        1
      )}% (${currentTimeInSeconds.toFixed()}s)`
    )
  }
}, 500)

const onVideoError = (event: Event) => {
  console.error('Video error:', event, {
    error: videoPlayer.value?.error,
    networkState: videoPlayer.value?.networkState,
    readyState: videoPlayer.value?.readyState,
  })
  toast('Error loading video')
}

const onLoadStart = () => {
  console.log('Video load started')
}

const onCanPlay = () => {
  console.log('Video can start playing')
}

// Video overlay and control methods
const onPlay = () => {
  isPlaying.value = true
}

const onPause = () => {
  isPlaying.value = false
}

const togglePlayPause = () => {
  if (!videoPlayer.value) return

  if (videoPlayer.value.paused) {
    videoPlayer.value.play()
  } else {
    videoPlayer.value.pause()
  }
}

const onProgressChange = (value: number[] | undefined) => {
  if (!videoPlayer.value || !value?.length) return

  const newTime = value[0]
  if (typeof newTime === 'number') {
    videoPlayer.value.currentTime = newTime
    currentTime.value = newTime
    progress.value = value
  }
}

const downloadVideo = () => {
  if (!video.value?.videoBlob) return

  const url = URL.createObjectURL(video.value.videoBlob)
  const a = document.createElement('a')
  a.href = url
  a.download = video.value.filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)

  toast('Download started')
}

const deleteVideo = async () => {
  if (!video.value?.id) return

  const confirmed = confirm(
    `Are you sure you want to delete "${video.value.title}"?`
  )
  if (!confirmed) return

  try {
    await videoProcessingService.deleteVideo(video.value.id)
    toast(`Video "${video.value.title}" deleted successfully`)
    router.push('/')
  } catch (err) {
    toast('Failed to delete video')
    console.error('Delete error:', err)
  }
}

const retryProcessing = async () => {
  if (!video.value?.id) return

  try {
    await videoProcessingService.retryProcessing(video.value.id)
    toast('Retrying video processing...')
    await loadVideo()
  } catch (err) {
    toast('Failed to retry processing')
    console.error('Retry error:', err)
  }
}

const startAutoRefresh = () => {
  // Refresh video status every 5 seconds if processing
  refreshInterval = setInterval(async () => {
    if (
      video.value &&
      (video.value.processingStatus === 'processing' ||
        video.value.processingStatus === 'pending')
    ) {
      await loadVideo()
    }
  }, 5000)
}

const startStatusPolling = () => {
  // Only poll if video is uploaded but backend not ready
  if (
    video.value?.processingStatus === 'completed' &&
    video.value?.s3Uri &&
    backendStatus.value !== 'done'
  ) {
    statusPollingInterval = setInterval(async () => {
      if (video.value?.id && backendStatus.value !== 'done') {
        try {
          const jobId = `upload-${video.value.id}`
          const statusResponse = await checkVideoStatus(jobId)
          backendStatus.value = statusResponse.status

          // Stop polling when done
          if (statusResponse.status === 'done' && statusPollingInterval) {
            clearInterval(statusPollingInterval)
            statusPollingInterval = null
          }
        } catch (error) {
          console.error('Failed to check backend status:', error)
        }
      }
    }, 3000)
  }
}

const seekToTimestamp = (timestamp: number) => {
  if (videoPlayer.value && video.value?.processingStatus === 'completed') {
    videoPlayer.value.currentTime = timestamp
    videoPlayer.value.play().catch(err => {
      console.error('Error playing video:', err)
    })
  } else {
    toast('Video is not ready for playback')
  }
}

// Utility functions
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

// Page metadata
useHead({
  title: computed(() =>
    video.value ? `${video.value.title} - Lookowl` : 'Video Details'
  ),
  meta: [{ name: 'description', content: 'View and manage video details' }],
})
</script>
