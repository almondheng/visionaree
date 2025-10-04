<template>
  <VideoPlayer
    v-if="!showRecording"
    :processing-status="processingStatus"
    :is-webcam="true"
    :webcam-stream="stream"
    :webcam-error="error"
  />
  <WebcamRecordingPlayer
    v-else
    :chunks="recorder.getChunks()"
    :total-duration="recorder.getTotalDuration()"
  />
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

const isStreaming = computed(() => !!stream.value)

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
      video: true,
      audio: false,
    })
    recorder.startRecording(stream.value)
  } catch (err) {
    error.value = 'Failed to access camera'
    console.error('Camera error:', err)
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

defineExpose({
  startCamera,
  stopCamera,
  isStreaming,
  showRecording,
  clearRecording,
})
</script>
