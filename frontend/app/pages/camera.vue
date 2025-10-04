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
          <VideoPromptSkeleton v-if="!isBackendReady" />
          <VideoPrompt v-else-if="isBackendReady" ref="videoPromptRef" video-id="camera-live" @seek-to-timestamp="() => {}" />
          <div v-else class="h-full flex items-center justify-center">
            <p class="text-muted-foreground">Loading...</p>
          </div>
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
                <Button v-if="!isCameraActive && !isShowingRecording" @click="startCamera">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Start Camera
              </Button>
              <Button v-else-if="isCameraActive" variant="destructive" @click="stopCamera">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
                Stop Recording
              </Button>
              <Button v-if="isShowingRecording" @click="startCamera">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                New Recording
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
import VideoPrompt from '~/components/VideoPrompt.vue'
import VideoPromptSkeleton from '~/components/VideoPromptSkeleton.vue'
import WebcamPlayer from '~/components/WebcamPlayer.vue'

const webcamPlayerRef = ref<InstanceType<typeof WebcamPlayer> | null>(null)
const videoPromptRef = ref<InstanceType<typeof VideoPrompt> | null>(null)
const isBackendReady = ref(false)

const isCameraActive = computed(() => webcamPlayerRef.value?.isStreaming || false)
const isShowingRecording = computed(() => webcamPlayerRef.value?.showRecording || false)
const cameraStatus = computed(() => {
  if (isShowingRecording.value) return 'Recording Available'
  return isCameraActive.value ? 'Active' : 'Inactive'
})

const startCamera = async () => {
  await webcamPlayerRef.value?.startCamera()
}

const stopCamera = () => {
  webcamPlayerRef.value?.stopCamera()
}

const clearRecording = () => {
  webcamPlayerRef.value?.clearRecording()
}

onMounted(() => {
  startCamera()
})

useHead({
  title: 'Live Camera - Lookowl',
  meta: [{ name: 'description', content: 'Live camera monitoring' }],
})

definePageMeta({
  ssr: false,
})
</script>
