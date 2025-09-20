<template>
  <div class="container mx-auto">
    <!-- Upload section - shown when no videos or user wants to add more -->
    <div v-if="videos.length === 0" class="mb-8">
      <VideoUpload
        :on-upload-success="handleUploadSuccess"
        :on-upload-error="handleUploadError"
      />
    </div>

    <!-- Videos grid -->
    <div v-if="videos.length > 0">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Your Videos ({{ videos.length }})
        </h2>
        <Button
          @click="showUploadDialog = true"
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          Add Video
        </Button>
      </div>

      <VideoGrid
        :videos="videos"
        :on-video-click="handleVideoClick"
        :on-play-video="handlePlayVideo"
        :on-delete-video="handleDeleteVideo"
      />
    </div>

    <!-- Upload dialog overlay -->
    <div
      v-if="showUploadDialog"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click="showUploadDialog = false"
    >
      <div
        class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4"
        @click.stop
      >
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Upload New Video</h3>
          <Button variant="ghost" size="sm" @click="showUploadDialog = false">
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </Button>
        </div>

        <VideoUpload
          :on-upload-success="handleDialogUploadSuccess"
          :on-upload-error="handleUploadError"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="text-center py-8">
      <div
        class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"
      ></div>
      <p class="text-gray-600 dark:text-gray-400">Loading videos...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from "vue";
import { toast } from "vue-sonner";
import { Button } from "~/components/ui/button";
import VideoUpload from "~/components/VideoUpload.vue";
import VideoGrid from "~/components/VideoGrid.vue";
import { videoProcessingService } from "~/lib/video-service";
import type { VideoRecord } from "~/lib/db";

// Reactive state
const videos = ref<VideoRecord[]>([]);
const isLoading = ref(true);
const showUploadDialog = ref(false);

// Auto-refresh interval for processing status
let refreshInterval: ReturnType<typeof setInterval> | null = null;

// Lifecycle
onMounted(async () => {
  await loadVideos();
  startAutoRefresh();
});

onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});

// Methods
const loadVideos = async () => {
  try {
    isLoading.value = true;
    videos.value = await videoProcessingService.getAllVideos();
  } catch (err) {
    toast("Failed to load videos");
    console.error("Error loading videos:", err);
  } finally {
    isLoading.value = false;
  }
};

const handleUploadSuccess = async (file: File) => {
  try {
    const videoId = await videoProcessingService.processVideo(file);
    toast(`Video "${file.name}" uploaded successfully and is being processed`);

    // Refresh videos list
    await loadVideos();
  } catch (err) {
    toast("Failed to process video");
    console.error("Upload error:", err);
  }
};

const handleDialogUploadSuccess = async (file: File) => {
  await handleUploadSuccess(file);
  showUploadDialog.value = false;
};

const handleUploadError = (errorMessage: string) => {
  toast(errorMessage);
};

const handleVideoClick = (video: VideoRecord) => {
  if (video.id) {
    navigateTo(`/video/${video.id}`);
  }
};

const handlePlayVideo = (video: VideoRecord) => {
  if (video.id) {
    navigateTo(`/video/${video.id}`);
  }
};

const handleDeleteVideo = async (video: VideoRecord) => {
  if (!video.id) return;

  const confirmed = confirm(
    `Are you sure you want to delete "${video.title}"?`
  );
  if (!confirmed) return;

  try {
    await videoProcessingService.deleteVideo(video.id);
    toast(`Video "${video.title}" deleted successfully`);

    // Refresh videos list
    await loadVideos();
  } catch (err) {
    toast("Failed to delete video");
    console.error("Delete error:", err);
  }
};

const startAutoRefresh = () => {
  // Refresh videos every 5 seconds to update processing status
  refreshInterval = setInterval(async () => {
    const hasProcessingVideos = videos.value.some(
      (video) =>
        video.processingStatus === "processing" ||
        video.processingStatus === "pending"
    );

    if (hasProcessingVideos) {
      await loadVideos();
    }
  }, 5000);
};

// Page metadata
useHead({
  title: "Visionaree",
  meta: [
    { name: "description", content: "Upload and manage videos for annotation" },
  ],
});
</script>
