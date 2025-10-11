<template>
  <Card class="py-0 h-full">
    <CardContent class="p-0 h-full">
      <div class="bg-black relative overflow-hidden rounded-lg h-full">
        <video
          ref="videoPlayer"
          class="w-full h-full object-contain"
          :muted="true"
          @timeupdate="onTimeUpdate"
          @click="togglePlayPause"
        />

        <div class="absolute bottom-0 left-0 right-0 p-2">
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
                :model-value="[currentTime]"
                :max="totalDuration"
                :step="0.1"
                class="flex-1 cursor-pointer"
                @update:model-value="onProgressChange"
              />
              <span class="text-white text-xs font-medium whitespace-nowrap">{{
                formatDuration(totalDuration)
              }}</span>
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { Card, CardContent } from '~/components/ui/card'
import { Slider } from '~/components/ui/slider'
import type { RecordedChunk } from '~/lib/webcam-recorder'

const props = defineProps<{
  chunks: RecordedChunk[]
  totalDuration: number
}>()

const emit = defineEmits<{
  'time-update': [time: number]
}>()

const videoPlayer = ref<HTMLVideoElement>()
const currentTime = ref(0)
const isPlaying = ref(false)
let mediaSource: MediaSource | null = null
let sourceBuffer: SourceBuffer | null = null
let appendedChunks = 0

const setupMediaSource = async () => {
  if (!videoPlayer.value) return

  mediaSource = new MediaSource()
  videoPlayer.value.src = URL.createObjectURL(mediaSource)

  mediaSource.addEventListener('sourceopen', async () => {
    if (!mediaSource) return

    // Use the same MIME type fallback logic as webcam-recorder.ts
    let mimeType = 'video/webm;codecs=vp9'
    if (!MediaSource.isTypeSupported(mimeType)) {
      mimeType = 'video/webm;codecs=vp8'
      if (!MediaSource.isTypeSupported(mimeType)) {
        mimeType = 'video/webm'
      }
    }

    if (!MediaSource.isTypeSupported(mimeType)) {
      console.error('MIME type not supported:', mimeType)
      return
    }

    sourceBuffer = mediaSource.addSourceBuffer(mimeType)
    sourceBuffer.mode = 'sequence'

    sourceBuffer.addEventListener('updateend', () => {
      if (
        appendedChunks < props.chunks.length &&
        sourceBuffer &&
        !sourceBuffer.updating
      ) {
        appendNextChunk()
      }
    })

    appendNextChunk()
  })
}

const appendNextChunk = async () => {
  if (
    !sourceBuffer ||
    sourceBuffer.updating ||
    appendedChunks >= props.chunks.length
  )
    return

  const chunk = props.chunks[appendedChunks]
  if (!chunk || !chunk.blob || chunk.blob.size === 0) {
    appendedChunks++
    return
  }

  const arrayBuffer = await chunk.blob.arrayBuffer()

  try {
    sourceBuffer.appendBuffer(arrayBuffer)
    appendedChunks++

    // Update duration as chunks are appended
    if (
      mediaSource &&
      mediaSource.readyState === 'open' &&
      appendedChunks === props.chunks.length
    ) {
      try {
        mediaSource.endOfStream()
      } catch (e) {
        console.warn('Failed to end stream:', e)
      }
    }
  } catch (e) {
    console.error('Error appending chunk:', e)
  }
}

const onTimeUpdate = () => {
  if (videoPlayer.value) {
    currentTime.value = videoPlayer.value.currentTime
    emit('time-update', currentTime.value)
  }
}

const togglePlayPause = () => {
  if (!videoPlayer.value) return

  if (videoPlayer.value.paused) {
    videoPlayer.value.play()
    isPlaying.value = true
  } else {
    videoPlayer.value.pause()
    isPlaying.value = false
  }
}

const onProgressChange = (value: number[] | undefined) => {
  if (!value?.length || !videoPlayer.value) return

  const targetTime = value[0]
  if (targetTime === undefined) return

  // Clamp seek time to available duration
  const clampedTime = Math.min(
    targetTime,
    videoPlayer.value.duration || props.totalDuration
  )

  try {
    videoPlayer.value.currentTime = clampedTime
    currentTime.value = clampedTime
  } catch (e) {
    console.warn('Seek failed:', e)
    // Fallback to current time if seek fails
    currentTime.value = videoPlayer.value.currentTime
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

watch(
  () => props.chunks.length,
  newLength => {
    if (newLength > 0 && !mediaSource) {
      // Only setup if we have chunks with actual blobs
      const hasValidChunks = props.chunks.some(
        chunk => chunk.blob && chunk.blob.size > 0
      )
      if (hasValidChunks) {
        setupMediaSource()
      }
    } else if (
      newLength > appendedChunks &&
      sourceBuffer &&
      !sourceBuffer.updating
    ) {
      appendNextChunk()
    }
  },
  { immediate: true }
)

watch(
  () => videoPlayer.value,
  () => {
    if (videoPlayer.value && !mediaSource) {
      setupMediaSource()
    }
  },
  { immediate: true }
)

const seekTo = (time: number) => {
  if (!videoPlayer.value) return

  // Clamp seek time to available duration
  const clampedTime = Math.min(
    time,
    videoPlayer.value.duration || props.totalDuration
  )

  try {
    videoPlayer.value.currentTime = clampedTime
    currentTime.value = clampedTime
  } catch (e) {
    console.warn('Seek failed:', e)
    // Fallback to current time if seek fails
    currentTime.value = videoPlayer.value.currentTime
  }
}

const play = async () => {
  if (!videoPlayer.value) return

  try {
    await videoPlayer.value.play()
    isPlaying.value = true
  } catch (e) {
    console.warn('Play failed:', e)
  }
}

defineExpose({
  seekTo,
  play,
})

onBeforeUnmount(() => {
  if (videoPlayer.value?.src) {
    URL.revokeObjectURL(videoPlayer.value.src)
  }
})
</script>
