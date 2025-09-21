<template>
  <Card class="h-full max-h-[500px]">
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
        Ask about this video
      </CardTitle>
    </CardHeader>

    <CardContent class="flex-1 flex flex-col gap-4 min-h-0">
      <!-- Prompt input -->
      <div class="space-y-2">
        <div class="relative">
          <Textarea
            v-model="promptText"
            placeholder="What happened in this video? Describe specific scenes or events..."
            class="min-h-[100px] resize-none pr-16"
            :disabled="isLoading"
            @keydown.enter.ctrl.prevent="submitPrompt"
            @keydown.enter.meta.prevent="submitPrompt"
          />
          <Button
            @click="submitPrompt"
            :disabled="isLoading || !promptText.trim()"
            size="sm"
            class="absolute bottom-2 right-2"
          >
            <svg
              v-if="isLoading"
              class="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <svg
              v-else
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
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
            <span class="sr-only">{{
              isLoading ? 'Analyzing...' : 'Ask'
            }}</span>
          </Button>
        </div>
        <p class="text-xs text-muted-foreground">
          Press Ctrl+Enter (⌘+Enter) to submit
        </p>
      </div>

      <Separator />

      <!-- Responses -->
      <div class="flex-1 flex flex-col min-h-0">
        <h3
          class="font-semibold mb-3 text-sm text-muted-foreground uppercase tracking-wide"
        >
          Responses
        </h3>

        <ScrollArea class="h-[200px]">
          <div class="pr-4">
            <div
              v-if="responses.length === 0 && !isLoading"
              class="text-center py-8"
            >
              <div class="text-muted-foreground mb-2">
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
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <p class="text-muted-foreground text-sm">
                No questions asked yet. Start by asking what happens in the
                video!
              </p>
            </div>

            <div v-else class="space-y-4">
              <!-- Question and answer pairs -->
              <div
                v-for="(response, index) in responses"
                :key="index"
                class="space-y-3"
              >
                <!-- Question -->
                <div class="bg-muted/50 rounded-lg p-3">
                  <div class="flex items-start gap-2">
                    <div class="mt-1">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4 text-primary"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                    <p class="text-sm font-medium">{{ response.question }}</p>
                  </div>
                </div>

                <!-- Answer with timestamps -->
                <div class="pl-6 space-y-2">
                  <div
                    v-for="(event, eventIndex) in response.events"
                    :key="eventIndex"
                    class="flex items-start gap-3 p-3 bg-background border rounded-lg hover:bg-muted/30 transition-colors cursor-pointer"
                    @click="$emit('seek-to-timestamp', event.timestamp)"
                  >
                    <Badge
                      variant="secondary"
                      class="mt-0.5 shrink-0 font-mono text-xs"
                    >
                      {{ formatTimestamp(event.timestamp) }}
                    </Badge>
                    <p class="text-sm flex-1">{{ event.description }}</p>
                    <div class="mt-0.5 shrink-0 text-muted-foreground">
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
                          d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h8m2-10v18a2 2 0 01-2 2H6a2 2 0 01-2-2V4a2 2 0 012-2h12a2 2 0 012 2z"
                        />
                      </svg>
                    </div>
                  </div>
                </div>

                <!-- Separator between responses -->
                <Separator v-if="index < responses.length - 1" class="my-4" />
              </div>

              <!-- Loading indicator -->
              <div
                v-if="isLoading"
                class="flex items-center justify-center py-4"
              >
                <div class="flex items-center gap-2 text-muted-foreground">
                  <div
                    class="animate-spin rounded-full h-4 w-4 border-b-2 border-current"
                  ></div>
                  <span class="text-sm">Analyzing video content...</span>
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { formatTimestamp } from '@/lib/utils'

// Props
interface Props {
  videoId: string
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'seek-to-timestamp': [timestamp: number]
}>()

// Types
interface VideoEvent {
  timestamp: number
  description: string
}

interface VideoResponse {
  question: string
  events: VideoEvent[]
}

// Reactive state
const promptText = ref('')
const isLoading = ref(false)
const responses = ref<VideoResponse[]>([])

// Methods
async function submitPrompt() {
  if (!promptText.value.trim() || isLoading.value) return

  const question = promptText.value.trim()
  isLoading.value = true

  try {
    // TODO: Replace with actual API call
    // For now, simulate API response
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock response - replace with actual API call
    const mockEvents: VideoEvent[] = [
      {
        timestamp: 15.5,
        description: 'Person enters the frame and starts speaking',
      },
      {
        timestamp: 45.2,
        description: 'Camera pans to show the surrounding environment',
      },
      {
        timestamp: 78.9,
        description: 'Action sequence begins with movement',
      },
    ]

    // Add the response
    responses.value.push({
      question,
      events: mockEvents,
    })

    // Clear the input
    promptText.value = ''
  } catch (error) {
    console.error('Error submitting prompt:', error)
    // You might want to show an error message to the user
  } finally {
    isLoading.value = false
  }
}
</script>
