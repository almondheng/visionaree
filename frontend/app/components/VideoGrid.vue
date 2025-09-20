<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
    <Card
      v-for="video in videos"
      :key="video.id"
      class="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer pt-0 pb-2 gap-1"
      @click="onVideoClick?.(video)"
    >
      <CardHeader class="p-0">
        <div
          class="aspect-video bg-gray-100 dark:bg-gray-800 relative overflow-hidden"
        >
          <img
            v-if="video.thumbnail"
            :src="video.thumbnail"
            :alt="video.title"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <div class="text-gray-400">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-12 w-12"
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
          </div>

          <!-- Processing status overlay -->
          <div
            v-if="video.processingStatus === 'processing'"
            class="absolute inset-0 bg-black/50 flex items-center justify-center"
          >
            <div class="text-white text-sm">
              <div
                class="animate-spin rounded-full h-6 w-6 border-b-2 border-white mb-2 mx-auto"
              ></div>
              Processing...
            </div>
          </div>

          <!-- Duration badge -->
          <div
            v-if="video.duration"
            class="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-2 py-1 rounded"
          >
            {{ formatDuration(video.duration) }}
          </div>

          <!-- Status indicator -->
          <div class="absolute top-2 right-2">
            <div
              v-if="video.processingStatus === 'completed'"
              class="w-3 h-3 bg-green-500 rounded-full"
              title="Processing completed"
            ></div>
            <div
              v-else-if="video.processingStatus === 'error'"
              class="w-3 h-3 bg-red-500 rounded-full"
              title="Processing failed"
            ></div>
            <div
              v-else-if="video.processingStatus === 'pending'"
              class="w-3 h-3 bg-yellow-500 rounded-full"
              title="Pending processing"
            ></div>
          </div>
        </div>
      </CardHeader>

      <CardContent class="">
        <CardTitle class="text-sm font-medium line-clamp-2">
          {{ video.title }}
        </CardTitle>
      </CardContent>

      <CardContent class="">
        <CardDescription class="text-xs space-y-1">
          <div class="flex justify-between">
            <span>{{ formatFileSize(video.size) }}</span>
            <span>{{ formatDate(video.uploadedAt) }}</span>
          </div>
          <!-- <div class="text-xs text-gray-500 capitalize">
            {{ video.processingStatus }}
          </div> -->
        </CardDescription>
        <!-- <Button
          variant="ghost"
          size="sm"
          @click.stop="onDeleteVideo?.(video)"
          class="text-red-600 hover:text-red-700"
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
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </Button> -->
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
  CardHeader,
  CardFooter,
} from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import type { VideoRecord } from "~/lib/db";

interface Props {
  videos: VideoRecord[];
  onVideoClick?: (video: VideoRecord) => void;
  onPlayVideo?: (video: VideoRecord) => void;
  onDeleteVideo?: (video: VideoRecord) => void;
}

defineProps<Props>();

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date));
};

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
};
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
