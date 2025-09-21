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
          >Processing video for analysis...</CardDescription
        >
      </div>
    </CardHeader>

    <!-- Chat Messages Area -->
    <CardContent class="flex-1 flex flex-col min-h-0 p-0">
      <!-- Processing State -->
      <div class="flex-1 p-4 h-[340px]">
        <div
          class="flex-1 flex flex-col items-center justify-center text-center p-6"
        >
          <div class="mb-6">
            <div
              class="w-16 h-16 mx-auto mb-4 rounded-full bg-muted/30 flex items-center justify-center"
            >
              <div
                class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"
              ></div>
            </div>
            <h4 class="font-medium text-sm mb-2">Processing Video</h4>
            <p class="text-xs text-muted-foreground mb-4">
              {{ processingMessage }}
            </p>
          </div>

          <!-- Simple analysis message -->
          <div class="w-full max-w-md">
            <p class="text-xs text-muted-foreground text-center">
              Your video is being analyzed to enable AI-powered questions. This
              usually takes a few minutes.
            </p>
          </div>
        </div>
      </div>
    </CardContent>

    <!-- Chat Input Area (Disabled) -->
    <CardFooter class="p-4">
      <div class="relative w-full">
        <Textarea
          placeholder="Video is being processed..."
          class="w-full min-h-[60px] max-h-[120px] resize-none pr-12 border-muted-foreground/20 bg-muted/30"
          disabled
          rows="2"
        />
        <Button
          disabled
          size="sm"
          class="absolute right-4 top-1/2 -translate-y-1/2 h-8 w-8 p-0 rounded-full bg-muted"
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
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
        </Button>
      </div>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Button } from '~/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '~/components/ui/card'
import { Textarea } from '~/components/ui/textarea'

// Processing messages that cycle through
const processingMessages = [
  'Analyzing video content...',
  'Extracting key segments...',
  'Preparing AI analysis...',
  'Almost ready for questions...',
]

const processingMessage = ref(processingMessages[0])
let messageInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  // Cycle through processing messages
  let messageIndex = 0
  messageInterval = setInterval(() => {
    messageIndex = (messageIndex + 1) % processingMessages.length
    processingMessage.value = processingMessages[messageIndex]
  }, 3000)
})

onBeforeUnmount(() => {
  if (messageInterval) {
    clearInterval(messageInterval)
  }
})
</script>
