<template>
  <div class="container mx-auto">
    <div class="mb-6">
      <Button variant="ghost" @click="$router.push('/')" class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Videos
      </Button>
    </div>

    <div class="flex flex-col gap-8">
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div class="xl:col-span-2 h-full max-h-[500px]">
          <ClientOnly>
            <WebcamPlayer ref="webcamPlayerRef" />
          </ClientOnly>
        </div>

        <div class="xl:col-span-1 h-full max-h-[500px]">
          <ClientOnly>
            <WebcamCaptions
              :captions="webcamCaptions"
              :processing-status="webcamProcessingStatus"
              @seek-to-timestamp="seekToTimestamp"
            />
          </ClientOnly>
        </div>
      </div>

      <div>
        <Card>
          <CardHeader>
            <CardTitle class="text-2xl">Live Camera Feed</CardTitle>
            <CardDescription class="text-base">Real-time webcam monitoring</CardDescription>
          </CardHeader>
          <CardContent class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Status</label>
                <ClientOnly>
                  <p class="text-sm">{{ cameraStatus }}</p>
                </ClientOnly>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Resolution</label>
                <p class="text-sm">Auto</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Frame Rate</label>
                <p class="text-sm">30 FPS</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Source</label>
                <p class="text-sm">Webcam</p>
              </div>
            </div>

            <div class="flex gap-3 pt-4 border-t">
              <ClientOnly>
                <Button v-if="isShowingRecording" @click="switchToLive">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Switch to Live
                </Button>
                <Button v-else @click="switchToPlayback">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  View Recording
                </Button>
                <Button v-if="isShowingRecording" variant="outline" @click="clearRecording">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Clear
                </Button>
              </ClientOnly>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import WebcamPlayer from '~/components/WebcamPlayer.vue'
import WebcamCaptions from '~/components/WebcamCaptions.vue'

const webcamPlayerRef = ref<InstanceType<typeof WebcamPlayer> | null>(null)

const isCameraActive = computed(() => webcamPlayerRef.value?.isStreaming || false)
const isShowingRecording = computed(() => webcamPlayerRef.value?.showRecording || false)
const webcamCaptions = computed(() => webcamPlayerRef.value?.captions || [])
const webcamProcessingStatus = computed(() => webcamPlayerRef.value?.captionProcessingStatus || { total: 0, processing: 0, completed: 0, failed: 0 })
const cameraStatus = computed(() => {
  if (isShowingRecording.value) return 'Recording Available'
  return isCameraActive.value ? 'Active' : 'Inactive'
})

const switchToLive = () => {
  webcamPlayerRef.value?.switchToLive()
}

const switchToPlayback = () => {
  webcamPlayerRef.value?.switchToPlayback()
}

const stopCamera = () => {
  webcamPlayerRef.value?.stopCamera()
}

const clearRecording = () => {
  webcamPlayerRef.value?.clearRecording()
}

const seekToTimestamp = async (timestamp: number) => {
  if (!isShowingRecording.value) {
    webcamPlayerRef.value?.switchToPlayback()
    // Wait for playback to be ready
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  webcamPlayerRef.value?.seekTo(timestamp)
}

onMounted(() => {
  webcamPlayerRef.value?.startCamera()
})

useHead({
  title: 'Live Camera - Lookowl',
  meta: [{ name: 'description', content: 'Live camera monitoring' }],
})

definePageMeta({
  ssr: false,
})
</script>
