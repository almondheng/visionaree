<template>
  <Card class="h-full max-h-[600px] flex flex-col pb-0 gap-0">
    <!-- Chat Header -->
    <CardHeader class="flex flex-row items-center gap-3 space-y-0 border-b">
      <div
        class="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10"
      >
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
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </div>
      <div>
        <CardTitle class="text-sm">Video Assistant</CardTitle>
        <CardDescription class="text-xs"
          >Ask questions about your video</CardDescription
        >
      </div>
    </CardHeader>

    <!-- Chat Messages Area -->
    <CardContent class="flex-1 flex flex-col min-h-0 p-0">
      <!-- Chat Messages -->
      <ScrollArea class="flex-1 p-4 h-[340px]">
        <!-- Empty State with Suggested Prompts -->
        <div
          v-if="responses.length === 0 && !isLoading"
          class="flex-1 flex flex-col items-center justify-center text-center p-6"
        >
          <div class="mb-6">
            <div
              class="w-16 h-16 mx-auto mb-4 rounded-full bg-muted/30 flex items-center justify-center"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-8 w-8 text-muted-foreground"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2M7 4h10M7 4l-2 16h14l-2-16"
                />
              </svg>
            </div>
            <h4 class="font-medium text-sm mb-2">Start a conversation</h4>
            <p class="text-xs text-muted-foreground">
              Ask questions about what happens in your video
            </p>
          </div>

          <!-- Suggested Prompts -->
          <div class="w-full max-w-md space-y-2">
            <p class="text-xs font-medium text-muted-foreground mb-3">
              Try asking:
            </p>
            <div class="grid gap-2">
              <Button
                v-for="suggestion in suggestedPrompts"
                :key="suggestion"
                variant="outline"
                size="sm"
                class="text-left justify-start h-auto py-2 px-3 text-xs"
                @click="submitSuggestedPrompt(suggestion)"
              >
                {{ suggestion }}
              </Button>
            </div>
          </div>
        </div>
        <div v-else class="space-y-4">
          <div
            v-for="(response, index) in responses"
            :key="index"
            class="space-y-3"
          >
            <!-- User Question Bubble -->
            <div class="flex justify-end">
              <div
                class="max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-md px-4 py-2"
              >
                <p class="text-sm">{{ response.question }}</p>
              </div>
            </div>

            <!-- AI Response Bubble -->
            <div class="flex justify-start">
              <div class="max-w-[85%]">
                <div class="bg-muted rounded-2xl rounded-tl-md px-4 py-3 mb-2">
                  <!-- Insights -->
                  <div v-if="response.insights" class="mb-3">
                    <p class="text-sm">{{ response.insights }}</p>
                    <div v-if="response.totalRelevantSegments" class="mt-2">
                      <Badge variant="secondary" class="text-xs">
                        {{ response.totalRelevantSegments }} segments found
                      </Badge>
                    </div>
                  </div>
                </div>

                <!-- Segments -->
                <div v-if="response.segments.length > 0" class="space-y-2 mt-2">
                  <div
                    v-for="(segment, segmentIndex) in response.segments"
                    :key="segmentIndex"
                    class="bg-background border rounded-lg p-3 hover:bg-muted/50 transition-colors cursor-pointer group"
                    @click="
                      $emit('seek-to-timestamp', segment.segmentStartTime)
                    "
                  >
                    <div class="flex items-start gap-3">
                      <div class="flex flex-col items-start gap-1">
                        <Badge
                          :variant="
                            segment.threat_level === 'high'
                              ? 'destructive'
                              : 'default'
                          "
                          class="text-xs"
                          :class="
                            segment.threat_level === 'high'
                              ? ''
                              : segment.threat_level === 'medium'
                              ? 'bg-amber-500'
                              : 'bg-yellow-500'
                          "
                        >
                          {{ formatTimestamp(segment.segmentStartTime) }}
                        </Badge>
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="text-sm leading-relaxed">
                          {{ segment.caption }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Loading Indicator -->
          <div v-if="isLoading" class="flex justify-start">
            <div class="bg-muted rounded-2xl rounded-tl-md px-4 py-3">
              <div class="flex items-center gap-2 text-muted-foreground">
                <div class="flex space-x-1">
                  <div
                    class="w-2 h-2 bg-current rounded-full animate-bounce"
                    style="animation-delay: 0ms"
                  ></div>
                  <div
                    class="w-2 h-2 bg-current rounded-full animate-bounce"
                    style="animation-delay: 150ms"
                  ></div>
                  <div
                    class="w-2 h-2 bg-current rounded-full animate-bounce"
                    style="animation-delay: 300ms"
                  ></div>
                </div>
                <span class="text-sm">Analyzing...</span>
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </CardContent>

    <!-- Chat Input Area -->
    <CardFooter class="p-4">
      <div class="relative w-full">
        <Textarea
          v-model="promptText"
          placeholder="Ask about your video..."
          class="w-full min-h-[60px] max-h-[120px] resize-none pr-12 border-muted-foreground/20 focus:border-primary"
          :disabled="isLoading"
          @keydown.enter.prevent="handleEnterKey"
          rows="2"
        />
        <Button
          @click="submitPrompt"
          :disabled="isLoading || !promptText.trim()"
          size="sm"
          class="absolute right-4 top-1/2 -translate-y-1/2 h-8 w-8 p-0 rounded-full"
          :class="
            promptText.trim() ? 'bg-primary hover:bg-primary/90' : 'bg-muted'
          "
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
          <span class="sr-only">{{ isLoading ? 'Analyzing...' : 'Send' }}</span>
        </Button>
      </div>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { formatTimestamp } from '@/lib/utils'
import {
  queryVideo,
  type FilteredSegment,
  type VideoQueryResponse,
} from '@/lib/video-service'

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
interface VideoSegment {
  segmentStartTime: number
  caption: string
  threat_level: 'low' | 'medium' | 'high'
  relevance_reason: string
}

interface VideoResponse {
  question: string
  segments: VideoSegment[]
  insights?: string
  totalRelevantSegments?: number
}

// Reactive state
const promptText = ref('')
const isLoading = ref(false)
const responses = ref<VideoResponse[]>([])

// Suggested prompts for the empty state
const suggestedPrompts = ['Identify suspicious activities']

// Methods
function handleEnterKey(event: KeyboardEvent) {
  if (event.shiftKey) {
    // Allow new line with Shift+Enter
    return
  }
  // Submit with Enter
  event.preventDefault()
  submitPrompt()
}

async function submitSuggestedPrompt(suggestion: string) {
  if (isLoading.value) return

  promptText.value = suggestion
  await submitPrompt()
}
async function submitPrompt() {
  if (!promptText.value.trim() || isLoading.value) return

  const question = promptText.value.trim()
  isLoading.value = true

  try {
    // Generate job ID from video ID (assuming it follows the upload-{videoId} pattern)
    const jobId = `upload-${props.videoId}`

    // Call the real API
    const apiResponse: VideoQueryResponse = await queryVideo(jobId, question)

    // Transform the API response to our component format
    const segments: VideoSegment[] =
      apiResponse.ai_analysis.filtered_segments.map(
        (segment: FilteredSegment) => ({
          segmentStartTime: parseInt(segment.segmentStartTime),
          caption: segment.caption,
          threat_level: segment.threat_level,
          relevance_reason: segment.relevance_reason,
        })
      )

    // Add the response
    responses.value.push({
      question,
      segments,
      insights: apiResponse.ai_analysis.insights,
      totalRelevantSegments: apiResponse.ai_analysis.total_relevant_segments,
    })

    // Check for high risk segments and show red toast if found
    const highRiskSegments = segments.filter(
      segment => segment.threat_level === 'high'
    )
    if (highRiskSegments.length > 0) {
      toast.warning(
        `High Risk Alert: ${highRiskSegments.length} high-risk segment${
          highRiskSegments.length > 1 ? 's' : ''
        } detected!`,
        {
          description:
            'Review the flagged segments for potential security concerns.',
          duration: 6000,
        }
      )
    }

    // Clear the input
    promptText.value = ''
  } catch (error) {
    console.error('Error submitting prompt:', error)
    // You might want to show an error message to the user
    // For now, add an error response
    responses.value.push({
      question,
      segments: [],
      insights:
        'Sorry, there was an error processing your query. Please try again.',
    })
    promptText.value = ''
  } finally {
    isLoading.value = false
  }
}

// Expose methods for parent components
defineExpose({
  submitSuggestedPrompt,
})
</script>
