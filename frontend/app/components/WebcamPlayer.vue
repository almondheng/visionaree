<template>
  <div class="aspect-video w-full h-full relative">
    <div class="absolute inset-0">
      <VideoPlayer
        v-if="!showRecording"
        :processing-status="processingStatus"
        :is-webcam="true"
        :webcam-stream="stream"
        :webcam-error="error"
        class="h-full"
      />
      <WebcamRecordingPlayer
        v-else
        ref="recordingPlayerRef"
        :chunks="recorder.getChunks()"
        :total-duration="recorder.getTotalDuration()"
        class="h-full"
        @time-update="onRecordingTimeUpdate"
      />
    </div>

    <!-- Centralized Progress Bar -->
    <div v-if="totalDuration > 0" class="absolute bottom-4 left-4 right-4">
      <div class="bg-black/70 backdrop-blur-sm rounded-lg px-4 py-3">
        <div class="flex items-center gap-3">
          <span class="text-white text-xs font-medium whitespace-nowrap">
            {{ formatDuration(currentProgress) }}
          </span>
          <Slider
            :model-value="[currentProgress]"
            :max="totalDuration"
            :step="0.1"
            class="flex-1 cursor-pointer"
            @update:model-value="onProgressChange"
          />
          <span class="text-white text-xs font-medium whitespace-nowrap">
            {{ formatDuration(totalDuration) }}
          </span>
          <div class="flex items-center gap-1">
            <div
              class="w-2 h-2 rounded-full transition-colors"
              :class="
                showRecording ? 'bg-blue-400' : 'bg-red-500 animate-pulse'
              "
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, watch, nextTick } from 'vue'
import VideoPlayer from '~/components/VideoPlayer.vue'
import WebcamRecordingPlayer from '~/components/WebcamRecordingPlayer.vue'
import { WebcamRecorder } from '~/lib/webcam-recorder'
import { Slider } from '~/components/ui/slider'

const stream = ref<MediaStream | null>(null)
const error = ref<string>('')
const recorder = new WebcamRecorder()
const showRecording = ref(false)
const recordingPlayerRef = ref<InstanceType<
  typeof WebcamRecordingPlayer
> | null>(null)
const currentProgress = ref(0)

const isStreaming = computed(() => !!stream.value)
const totalDuration = computed(() => recorder.getTotalDuration())
const captions = computed(() => recorder.getChunkCaptions())

// Camera settings computed properties
const cameraSettings = computed(() => {
  if (!stream.value) {
    return {
      resolution: 'Not Available',
      frameRate: 'Not Available',
      source: 'Not Available',
    }
  }

  const videoTrack = stream.value.getVideoTracks()[0]
  if (!videoTrack) {
    return {
      resolution: 'No Video Track',
      frameRate: 'No Video Track',
      source: 'No Video Track',
    }
  }

  const settings = videoTrack.getSettings()
  const capabilities = videoTrack.getCapabilities()

  return {
    resolution:
      settings.width && settings.height
        ? `${settings.width}x${settings.height}`
        : 'Auto',
    frameRate: settings.frameRate
      ? `${Math.round(settings.frameRate)} FPS`
      : 'Auto',
    source: videoTrack.label || 'Default Camera',
  }
})
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
    // Start playing automatically when switching to playback
    await nextTick()
    recordingPlayerRef.value?.play()
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
      // Start playing the recording automatically
      await nextTick()
      recordingPlayerRef.value?.play()
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

// Initialize progress when switching views
watch(showRecording, newValue => {
  if (!newValue) {
    // When switching to live, set progress to total duration
    currentProgress.value = totalDuration.value
  }
})

const seekTo = (time: number) => {
  recordingPlayerRef.value?.seekTo(time)
}

const seekToTimestamp = async (timestamp: number) => {
  // If we're in live mode, we need to switch to playback first
  const wasInLiveMode = !showRecording.value

  if (wasInLiveMode && recorder.getChunks().length > 0) {
    // Switch to playback mode first
    showRecording.value = true
    // Wait for the component to be ready
    await nextTick()
    // Give the video player a moment to initialize
    await new Promise(resolve => setTimeout(resolve, 100))
  }

  // Now seek to the timestamp and start playing
  recordingPlayerRef.value?.seekTo(timestamp)
  currentProgress.value = timestamp

  // Start playing
  if (wasInLiveMode) {
    await nextTick()
    recordingPlayerRef.value?.play()
  } else {
    recordingPlayerRef.value?.play()
  }
}

const switchToLive = () => {
  showRecording.value = false
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

const onRecordingTimeUpdate = (time: number) => {
  currentProgress.value = time
}

const onProgressChange = (value: number[] | undefined) => {
  if (!value || value.length === 0) return

  const newTime = value[0]
  if (typeof newTime !== 'number') return

  currentProgress.value = newTime

  // If at 100% (at the end), switch to live
  if (newTime >= totalDuration.value && totalDuration.value > 0) {
    showRecording.value = false
    currentProgress.value = totalDuration.value
  } else {
    // Switch to playback mode and seek
    const wasInLiveMode = !showRecording.value
    if (wasInLiveMode && recorder.getChunks().length > 0) {
      showRecording.value = true
    }

    // Seek to the specific time
    recordingPlayerRef.value?.seekTo(newTime)

    // Start playing automatically (with nextTick if we just switched modes)
    if (wasInLiveMode) {
      nextTick(() => {
        recordingPlayerRef.value?.play()
      })
    } else {
      // Already in playback mode, play immediately after seek
      recordingPlayerRef.value?.play()
    }
  }
}

// Update progress when in live mode
const updateLiveProgress = () => {
  if (!showRecording.value && totalDuration.value > 0) {
    currentProgress.value = totalDuration.value
  }
}

// Watch for changes in total duration to update live progress
watch(totalDuration, () => {
  updateLiveProgress()
})

// Watch for changes in showRecording state to update progress
watch(showRecording, () => {
  updateLiveProgress()
})

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
  seekToTimestamp,
  cameraSettings,
})
</script>
