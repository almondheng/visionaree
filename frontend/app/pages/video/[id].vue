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
          <VideoPlayer
            ref="videoPlayerRef"
            :video-blob="video.videoBlob"
            :processing-status="video.processingStatus"
            :thumbnail="video.thumbnail"
            :title="video.title"
            @retry="retryProcessing"
          />
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
import VideoPlayer from '~/components/VideoPlayer.vue'
import { videoProcessingService, checkVideoStatus } from '~/lib/video-service'
import type { VideoRecord } from '~/lib/db'

// Router
const route = useRoute()
const router = useRouter()

// Reactive state
const video = ref<VideoRecord | null>(null)
const isLoading = ref(true)
const error = ref(false)
const videoPlayerRef = ref<InstanceType<typeof VideoPlayer> | null>(null)

// Backend processing status
const backendStatus = ref<'done' | 'processing' | 'pending' | 'error'>(
  'processing'
)
const isBackendReady = computed(() => backendStatus.value === 'done')

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



// Watch for backend status changes to trigger auto-prompting
watch(backendStatus, async (newStatus, oldStatus) => {
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
      await videoPromptRef.value.submitSuggestedPrompt(
        'Identify suspicious activities'
      )
      toast('Auto-analyzing video for suspicious activities...')
    } catch (error) {
      console.error('Failed to trigger auto-prompt:', error)
    }
  }
})

onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
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
  } catch (err) {
    console.error('Error loading video:', err)
    error.value = true
  } finally {
    isLoading.value = false
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
  videoPlayerRef.value?.seekTo(timestamp)
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
