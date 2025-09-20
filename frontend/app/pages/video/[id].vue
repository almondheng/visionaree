<template>
  <div class="container mx-auto">
    <!-- Back button -->
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

    <!-- Loading state -->
    <div v-if="isLoading" class="text-center py-8">
      <div
        class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"
      ></div>
      <p class="text-gray-600 dark:text-gray-400">Loading video...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error || !video" class="text-center py-8">
      <div class="text-red-500 mb-4">
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
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
        Video not found
      </h2>
      <p class="text-gray-600 dark:text-gray-400 mb-4">
        The video you're looking for doesn't exist or has been deleted.
      </p>
      <Button @click="$router.push('/')">Go back to videos</Button>
    </div>

    <!-- Video detail view -->
    <div v-else>
      <!-- Video player section -->
      <Card class="mb-8 py-0">
        <CardContent class="p-0">
          <div
            class="bg-gray-100 dark:bg-gray-800 relative overflow-hidden rounded-lg"
          >
            <!-- Video player for completed videos -->
            <div
              v-if="video.processingStatus === 'completed' && video.videoBlob"
              class="w-full h-full"
            >
              <video
                ref="videoPlayer"
                class="w-full h-full object-contain"
                autoplay
                controls
                @loadedmetadata="onVideoLoaded"
                @timeupdate="onTimeUpdate"
                @error="onVideoError"
                @loadstart="onLoadStart"
                @canplay="onCanPlay"
              >
                Your browser does not support the video tag.
              </video>
            </div>

            <!-- Thumbnail for non-completed videos -->
            <div v-else class="w-full h-full flex items-center justify-center">
              <img
                v-if="video.thumbnail"
                :src="video.thumbnail"
                :alt="video.title"
                class="w-full h-full object-cover"
              />
              <div v-else class="text-gray-400">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-24 w-24"
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

            <!-- Processing overlay -->
            <div
              v-if="video.processingStatus === 'processing'"
              class="absolute inset-0 bg-black/50 flex items-center justify-center"
            >
              <div class="text-white text-center">
                <div
                  class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-4 mx-auto"
                ></div>
                <p class="text-lg">Processing video...</p>
                <p class="text-sm text-gray-300">This may take a few minutes</p>
              </div>
            </div>

            <!-- Error overlay -->
            <div
              v-if="video.processingStatus === 'error'"
              class="absolute inset-0 bg-red-500/20 flex items-center justify-center"
            >
              <div class="text-white text-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-8 w-8 mx-auto mb-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p class="text-lg">Processing failed</p>
                <Button
                  variant="outline"
                  size="sm"
                  class="mt-2 bg-white/10 border-white/20 text-white hover:bg-white/20"
                  @click="retryProcessing"
                >
                  Retry
                </Button>
              </div>
            </div>

            <!-- Status indicator -->
            <div class="absolute top-4 right-4">
              <div
                v-if="video.processingStatus === 'completed'"
                class="flex items-center gap-2 bg-green-500/80 text-white text-sm px-3 py-1 rounded-full"
              >
                <div class="w-2 h-2 bg-white rounded-full"></div>
                Ready
              </div>
              <div
                v-else-if="video.processingStatus === 'error'"
                class="flex items-center gap-2 bg-red-500/80 text-white text-sm px-3 py-1 rounded-full"
              >
                <div class="w-2 h-2 bg-white rounded-full"></div>
                Error
              </div>
              <div
                v-else-if="video.processingStatus === 'pending'"
                class="flex items-center gap-2 bg-yellow-500/80 text-white text-sm px-3 py-1 rounded-full"
              >
                <div class="w-2 h-2 bg-white rounded-full"></div>
                Pending
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Video information -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Main info -->
        <div class="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle class="text-2xl">{{ video.title }}</CardTitle>
              <CardDescription class="text-base">
                Video details and information
              </CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label
                    class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >
                    Filename
                  </label>
                  <p class="text-sm">{{ video.filename }}</p>
                </div>
                <div>
                  <label
                    class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >
                    File Size
                  </label>
                  <p class="text-sm">{{ formatFileSize(video.size) }}</p>
                </div>
                <div>
                  <label
                    class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >
                    Duration
                  </label>
                  <p class="text-sm">
                    {{
                      video.duration
                        ? formatDuration(video.duration)
                        : "Unknown"
                    }}
                  </p>
                </div>
                <div>
                  <label
                    class="text-sm font-medium text-gray-500 dark:text-gray-400"
                  >
                    Uploaded
                  </label>
                  <p class="text-sm">{{ formatDate(video.uploadedAt) }}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Actions sidebar -->
        <div>
          <Card>
            <CardHeader>
              <CardTitle class="text-lg">Actions</CardTitle>
            </CardHeader>
            <CardContent class="space-y-3">
              <Button
                v-if="video.processingStatus === 'completed'"
                class="w-full"
                @click="startAnnotation"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
                Start Annotation
              </Button>

              <Button
                variant="outline"
                class="w-full"
                @click="downloadVideo"
                :disabled="video.processingStatus !== 'completed'"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Download
              </Button>

              <Button variant="destructive" class="w-full" @click="deleteVideo">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 mr-2"
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
                Delete Video
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { videoProcessingService } from "~/lib/video-service";
import type { VideoRecord } from "~/lib/db";

// Router
const route = useRoute();
const router = useRouter();

// Reactive state
const video = ref<VideoRecord | null>(null);
const isLoading = ref(true);
const error = ref(false);
const videoPlayer = ref<HTMLVideoElement>();

// Auto-refresh for processing status
let refreshInterval: ReturnType<typeof setInterval> | null = null;

// Lifecycle
onMounted(async () => {
  await loadVideo();
  startAutoRefresh();
});

// Watch for video changes and setup player
watch(
  [video, videoPlayer],
  async () => {
    if (
      video.value?.processingStatus === "completed" &&
      video.value?.videoBlob &&
      videoPlayer.value
    ) {
      await nextTick();
      console.log("Watcher triggered - setting up video player");
      setupVideoPlayer();
    }
  },
  { immediate: false }
);

onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  // Clean up video blob URL if exists
  if (videoPlayer.value?.src) {
    URL.revokeObjectURL(videoPlayer.value.src);
  }
});

// Methods
const loadVideo = async () => {
  try {
    isLoading.value = true;
    error.value = false;

    const videoId = route.params.id as string;
    const videoData = await videoProcessingService.getVideo(videoId);

    if (!videoData) {
      error.value = true;
      return;
    }

    video.value = videoData;

    // Set up video player if video is ready
    if (videoData.processingStatus === "completed" && videoData.videoBlob) {
      await nextTick();
      console.log("Video is completed, setting up player...");
      setupVideoPlayer();
    } else {
      console.log("Video not ready for playback:", {
        status: videoData.processingStatus,
        hasBlob: !!videoData.videoBlob,
      });
    }
  } catch (err) {
    console.error("Error loading video:", err);
    error.value = true;
  } finally {
    isLoading.value = false;
  }
};

const setupVideoPlayer = () => {
  if (!video.value?.videoBlob || !videoPlayer.value) {
    console.log("Cannot setup video player:", {
      hasBlob: !!video.value?.videoBlob,
      hasPlayerRef: !!videoPlayer.value,
    });
    return;
  }

  // Clean up existing URL if any
  if (videoPlayer.value.src) {
    URL.revokeObjectURL(videoPlayer.value.src);
  }

  // Create object URL for the video blob
  const videoUrl = URL.createObjectURL(video.value.videoBlob);
  console.log("Setting video URL:", videoUrl);
  videoPlayer.value.src = videoUrl;

  // Force load the video
  videoPlayer.value.load();
};

const onVideoLoaded = () => {
  console.log("Video loaded successfully", {
    duration: videoPlayer.value?.duration,
    videoWidth: videoPlayer.value?.videoWidth,
    videoHeight: videoPlayer.value?.videoHeight,
    readyState: videoPlayer.value?.readyState,
  });
};

const onTimeUpdate = () => {
  if (videoPlayer.value && videoPlayer.value.duration) {
    const progress =
      (videoPlayer.value.currentTime / videoPlayer.value.duration) * 100;
    // Could emit progress for future annotation features
    console.log(`Video progress: ${progress.toFixed(1)}%`);
  }
};

const onVideoError = (event: Event) => {
  console.error("Video error:", event, {
    error: videoPlayer.value?.error,
    networkState: videoPlayer.value?.networkState,
    readyState: videoPlayer.value?.readyState,
  });
  toast("Error loading video");
};

const onLoadStart = () => {
  console.log("Video load started");
};

const onCanPlay = () => {
  console.log("Video can start playing");
};

const startAnnotation = () => {
  // TODO: Navigate to annotation interface
  toast("Annotation feature coming soon!");
};

const downloadVideo = () => {
  if (!video.value?.videoBlob) return;

  const url = URL.createObjectURL(video.value.videoBlob);
  const a = document.createElement("a");
  a.href = url;
  a.download = video.value.filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  toast("Download started");
};

const deleteVideo = async () => {
  if (!video.value?.id) return;

  const confirmed = confirm(
    `Are you sure you want to delete "${video.value.title}"?`
  );
  if (!confirmed) return;

  try {
    await videoProcessingService.deleteVideo(video.value.id);
    toast(`Video "${video.value.title}" deleted successfully`);
    router.push("/");
  } catch (err) {
    toast("Failed to delete video");
    console.error("Delete error:", err);
  }
};

const retryProcessing = async () => {
  if (!video.value?.id) return;

  try {
    await videoProcessingService.retryProcessing(video.value.id);
    toast("Retrying video processing...");
    await loadVideo();
  } catch (err) {
    toast("Failed to retry processing");
    console.error("Retry error:", err);
  }
};

const startAutoRefresh = () => {
  // Refresh video status every 5 seconds if processing
  refreshInterval = setInterval(async () => {
    if (
      video.value &&
      (video.value.processingStatus === "processing" ||
        video.value.processingStatus === "pending")
    ) {
      await loadVideo();
    }
  }, 5000);
};

// Utility functions
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
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

// Page metadata
useHead({
  title: computed(() =>
    video.value ? `${video.value.title} - Video Details` : "Video Details"
  ),
  meta: [{ name: "description", content: "View and manage video details" }],
});
</script>
