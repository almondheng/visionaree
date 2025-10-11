<template>
  <div class="container mx-auto">
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

    <div class="flex flex-col gap-8">
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div class="xl:col-span-2 h-[500px]">
          <ClientOnly>
            <WebcamPlayer ref="webcamPlayerRef" />
          </ClientOnly>
        </div>

        <div class="xl:col-span-1 h-[500px]">
          <ClientOnly>
            <WebcamCaptions
              :captions="webcamCaptions"
              :processing-status="webcamProcessingStatus"
              @seek-to-timestamp="seekToTimestamp"
              @user-prompt-change="handleUserPromptChange"
            />
          </ClientOnly>
        </div>
      </div>

      <div>
        <Card>
          <CardHeader>
            <CardTitle class="text-2xl">Live Camera Feed</CardTitle>
            <CardDescription class="text-base"
              >Real-time webcam monitoring</CardDescription
            >
          </CardHeader>
          <CardContent class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >Status</label
                >
                <ClientOnly>
                  <p class="text-sm">{{ cameraStatus }}</p>
                </ClientOnly>
              </div>
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >Resolution</label
                >
                <ClientOnly>
                  <p class="text-sm">{{ cameraSettings.resolution }}</p>
                </ClientOnly>
              </div>
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >Frame Rate</label
                >
                <ClientOnly>
                  <p class="text-sm">{{ cameraSettings.frameRate }}</p>
                </ClientOnly>
              </div>
              <div>
                <label
                  class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >Source</label
                >
                <ClientOnly>
                  <p class="text-sm">{{ cameraSettings.source }}</p>
                </ClientOnly>
              </div>
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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '~/components/ui/card'
import WebcamPlayer from '~/components/WebcamPlayer.vue'
import WebcamCaptions from '~/components/WebcamCaptions.vue'

const webcamPlayerRef = ref<InstanceType<typeof WebcamPlayer> | null>(null)

const isCameraActive = computed(
  () => webcamPlayerRef.value?.isStreaming || false
)
const isShowingRecording = computed(
  () => webcamPlayerRef.value?.showRecording || false
)
const webcamCaptions = computed(() => webcamPlayerRef.value?.captions || [])
const webcamProcessingStatus = computed(
  () =>
    webcamPlayerRef.value?.captionProcessingStatus || {
      total: 0,
      processing: 0,
      completed: 0,
      failed: 0,
    }
)
const cameraStatus = computed(() => {
  if (isShowingRecording.value) return 'Recording Available'
  return isCameraActive.value ? 'Active' : 'Inactive'
})

const cameraSettings = computed(() => {
  return (
    webcamPlayerRef.value?.cameraSettings || {
      resolution: 'Loading...',
      frameRate: 'Loading...',
      source: 'Loading...',
    }
  )
})

const stopCamera = () => {
  webcamPlayerRef.value?.stopCamera()
}

const seekToTimestamp = async (timestamp: number) => {
  await webcamPlayerRef.value?.seekToTimestamp(timestamp)
}

const handleUserPromptChange = (prompt: string) => {
  webcamPlayerRef.value?.setUserPrompt(prompt)
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
