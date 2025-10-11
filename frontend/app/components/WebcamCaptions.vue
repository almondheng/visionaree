<template>
  <Card class="h-full flex flex-col pb-0 gap-0">
    <!-- Chat Header -->
    <ChatHeader title="Live Captions" description="Real-time video analysis">
      <template #icon>
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
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      </template>
    </ChatHeader>

    <!-- Captions Area -->
    <CardContent class="flex-1 flex flex-col min-h-0 p-0 pb-4">
      <ScrollArea class="flex-1 p-4 min-h-0">
        <!-- Empty State -->
        <div
          v-if="sortedCaptions.length === 0"
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
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </div>
            <h4 class="font-medium text-sm mb-2">No notable captions yet</h4>
            <p class="text-xs text-muted-foreground">
              Only medium and high-threat content will appear here
            </p>
          </div>
        </div>

        <!-- Captions List -->
        <div v-else class="space-y-2">
          <div
            v-for="(caption, index) in sortedCaptions"
            :key="caption.timestamp"
            class="bg-background border rounded-lg p-3 hover:bg-muted/50 transition-colors cursor-pointer group"
            @click="$emit('seek-to-timestamp', caption.startTime)"
          >
            <div class="flex items-start gap-3">
              <div class="flex flex-col items-start gap-1">
                <Badge
                  :variant="
                    caption.threat_level === 'high' ? 'destructive' : 'default'
                  "
                  class="text-xs"
                  :class="
                    caption.threat_level === 'high'
                      ? ''
                      : caption.threat_level === 'medium'
                      ? 'bg-amber-500'
                      : 'bg-yellow-500'
                  "
                >
                  {{ formatAbsoluteTimestamp(caption.timestamp) }}
                </Badge>
              </div>
              <div class="flex-1 min-w-0">
                <p v-if="caption.caption" class="text-sm leading-relaxed">
                  {{ caption.caption }}
                </p>
                <p
                  v-else-if="caption.captionError"
                  class="text-sm text-red-500"
                >
                  Error: {{ caption.captionError }}
                </p>
                <p v-else class="text-sm text-muted-foreground">
                  No caption available
                </p>
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { toast } from 'vue-sonner'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChatHeader } from '@/components/ui/chat'
import { Card, CardContent } from '@/components/ui/card'
import { formatTimestamp, formatAbsoluteTimestamp } from '@/lib/utils'

interface CaptionItem {
  timestamp: number
  startTime: number
  caption?: string
  captionError?: string
  captionProcessing?: boolean
  threat_level?: 'low' | 'medium' | 'high'
}

interface Props {
  captions: CaptionItem[]
  processingStatus: {
    total: number
    processing: number
    completed: number
    failed: number
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'seek-to-timestamp': [timestamp: number]
}>()

const sortedCaptions = computed(() => {
  return [...props.captions]
    .filter(caption => caption.caption || caption.captionError)
    .filter(
      caption =>
        caption.threat_level === 'medium' || caption.threat_level === 'high'
    )
    .reverse()
})

// Watch for new high threat level captions and show toast
let previousHighThreatCount = 0
watch(
  () => props.captions,
  newCaptions => {
    const highThreatCaptions = newCaptions.filter(
      caption => caption.threat_level === 'high' && caption.caption
    )

    // Only show toast if we have new high threat captions
    if (highThreatCaptions.length > previousHighThreatCount) {
      const newHighThreatCount =
        highThreatCaptions.length - previousHighThreatCount
      toast.warning('High Risk Alert', {
        description:
          'Review the flagged timestamps for potential security concerns.',
        duration: 6000,
      })
    }

    previousHighThreatCount = highThreatCaptions.length
  },
  { deep: true }
)
</script>
