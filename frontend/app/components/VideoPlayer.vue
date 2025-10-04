<template>
  <Card class="py-0 h-full">
    <CardContent class="p-0 h-full">
      <div class="bg-black relative overflow-hidden rounded-lg h-full">
        <video
          v-if="
            (processingStatus === 'completed' && videoBlob) ||
            (isWebcam && webcamStream)
          "
          ref="videoPlayer"
          class="w-full h-full object-contain"
          :muted="true"
          :autoplay="isWebcam"
          :playsinline="isWebcam"
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

        <div
          v-if="processingStatus === 'completed' && videoBlob && !isWebcam"
          class="absolute bottom-0 left-0 right-0 p-2"
        >
          <div class="bg-black/30 backdrop-blur-sm rounded px-3 py-1.5">
            <div class="flex items-center gap-2">
              <button
                @click="togglePlayPause"
                class="flex items-center justify-center w-6 h-6 bg-white/20 hover:bg-white/30 rounded transition-all duration-200 text-white flex-shrink-0"
              >
                <svg
                  v-if="!isPlaying"
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-3 w-3"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
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
              <span class="text-white text-xs font-medium whitespace-nowrap">{{
                formatDuration(currentTime)
              }}</span>
              <Slider
                :model-value="progress"
                :max="duration"
                :step="1"
                class="flex-1 cursor-pointer"
                @update:model-value="onProgressChange"
              />
              <span class="text-white text-xs font-medium whitespace-nowrap">{{
                formatDuration(duration)
              }}</span>
            </div>
          </div>
        </div>

        <div
          v-else
          class="w-full h-full flex items-center justify-center min-h-[400px]"
        >
          <img
            v-if="thumbnail"
            :src="thumbnail"
            :alt="title"
            class="w-full h-full object-cover"
          />
          <div v-else class="text-gray-400 text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-24 w-24 mx-auto mb-4"
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
            <p v-if="isWebcam" class="text-lg mb-2">Camera not active</p>
            <p v-if="isWebcam" class="text-sm text-gray-500">
              Click Start Camera to begin
            </p>
          </div>
        </div>

        <div
          v-if="processingStatus === 'processing'"
          class="absolute inset-0 bg-black/50 flex items-center justify-center"
        >
          <div class="text-white text-center">
            <div
              class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-4 mx-auto"
            ></div>
            <p class="text-lg">Processing video...</p>
            <p class="text-sm text-gray-300">This may take a few minutes</p>
          </div>
        </div>

        <div
          v-if="processingStatus === 'error'"
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
            <p class="text-lg">
              {{ isWebcam && webcamError ? webcamError : 'Processing failed' }}
            </p>
            <Button
              v-if="!isWebcam"
              variant="outline"
              size="sm"
              class="mt-2 bg-white/10 border-white/20 text-white hover:bg-white/20"
              @click="$emit('retry')"
            >
              Retry
            </Button>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { useThrottleFn } from '@vueuse/core'
import { toast } from 'vue-sonner'
import { Card, CardContent } from '~/components/ui/card'
import { Slider } from '~/components/ui/slider'
import { Button } from '~/components/ui/button'

const props = defineProps<{
  videoBlob?: Blob
  processingStatus: 'pending' | 'processing' | 'completed' | 'error'
  thumbnail?: string
  title?: string
  isWebcam?: boolean
  webcamStream?: MediaStream | null
  webcamError?: string
}>()

const emit = defineEmits<{
  retry: []
}>()

const videoPlayer = ref<HTMLVideoElement>()
const currentTime = ref(0)
const duration = ref(0)
const isPlaying = ref(false)
const progress = ref([0])

watch(
  [() => props.videoBlob, () => props.webcamStream, videoPlayer],
  async () => {
    if (props.isWebcam && props.webcamStream && videoPlayer.value) {
      await nextTick()
      videoPlayer.value.srcObject = props.webcamStream
    } else if (
      props.processingStatus === 'completed' &&
      props.videoBlob &&
      videoPlayer.value
    ) {
      await nextTick()
      setupVideoPlayer()
    }
  },
  { immediate: false }
)

onBeforeUnmount(() => {
  if (videoPlayer.value?.src) {
    URL.revokeObjectURL(videoPlayer.value.src)
  }
})

const setupVideoPlayer = () => {
  if (!props.videoBlob || !videoPlayer.value) return
  if (videoPlayer.value.src) {
    URL.revokeObjectURL(videoPlayer.value.src)
  }
  const videoUrl = URL.createObjectURL(props.videoBlob)
  videoPlayer.value.src = videoUrl
  videoPlayer.value.load()
}

const onVideoLoaded = () => {
  if (videoPlayer.value?.duration) {
    duration.value = videoPlayer.value.duration
  }
}

const onTimeUpdate = useThrottleFn(() => {
  if (videoPlayer.value && videoPlayer.value.duration) {
    currentTime.value = videoPlayer.value.currentTime
    progress.value = [videoPlayer.value.currentTime]
  }
}, 500)

const onVideoError = () => {
  toast('Error loading video')
}

const onLoadStart = () => {}
const onCanPlay = () => {}

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

const seekTo = (timestamp: number) => {
  if (videoPlayer.value && props.processingStatus === 'completed') {
    videoPlayer.value.currentTime = timestamp
    videoPlayer.value.play().catch(err => {
      console.error('Error playing video:', err)
    })
  } else {
    toast('Video is not ready for playback')
  }
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

defineExpose({ seekTo })
</script>
