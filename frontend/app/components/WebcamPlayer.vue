<template>
  <div class="aspect-video w-full h-full">
    <VideoPlayer
      v-if="!showRecording"
      :processing-status="processingStatus"
      :is-webcam="true"
      :webcam-stream="stream"
      :webcam-error="error"
    />
    <WebcamRecordingPlayer
      v-else
      ref="recordingPlayerRef"
      :chunks="recorder.getChunks()"
      :total-duration="recorder.getTotalDuration()"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import VideoPlayer from '~/components/VideoPlayer.vue'
import WebcamRecordingPlayer from '~/components/WebcamRecordingPlayer.vue'
import { WebcamRecorder } from '~/lib/webcam-recorder'

const stream = ref<MediaStream | null>(null)
const error = ref<string>('')
const recorder = new WebcamRecorder()
const showRecording = ref(false)
const recordingPlayerRef = ref<InstanceType<
  typeof WebcamRecordingPlayer
> | null>(null)

const isStreaming = computed(() => !!stream.value)
const captions = computed(() => recorder.getChunkCaptions())
const captionProcessingStatus = computed(() =>
  recorder.getCaptionProcessingStatus()
)

const processingStatus = computed(() => {
  if (error.value) return 'error' as const
  if (isStreaming.value) return 'completed' as const
  return 'pending' as const
})

const startCamera = async () => {
  try {
    error.value = ''
    showRecording.value = false
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: {
        width: 640,
        height: 480,
        frameRate: 15,
      },
      audio: false,
    })
    recorder.startRecording(stream.value)
  } catch (err) {
    error.value = 'Failed to access camera'
    console.error('Camera error:', err)
  }
}

const switchToPlayback = async () => {
  // Keep recording but switch to playback view
  if (recorder.getChunks().length > 0) {
    await recorder.saveToIndexedDB()
    showRecording.value = true
  }
}

const stopCamera = async () => {
  recorder.stopRecording()
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop())
    stream.value = null
  }
  // Wait a bit for the last chunk to be processed
  setTimeout(async () => {
    if (recorder.getChunks().length > 0) {
      await recorder.saveToIndexedDB()
      showRecording.value = true
    }
  }, 100)
}

const clearRecording = async () => {
  await recorder.clearFromIndexedDB()
  recorder.clear()
  showRecording.value = false
}

onMounted(startCamera)

onBeforeUnmount(() => {
  stopCamera()
})

const seekTo = (time: number) => {
  recordingPlayerRef.value?.seekTo(time)
}

const switchToLive = () => {
  showRecording.value = false
}

defineExpose({
  startCamera,
  stopCamera,
  switchToPlayback,
  switchToLive,
  isStreaming,
  showRecording,
  clearRecording,
  captions,
  captionProcessingStatus,
  seekTo,
})
</script>
