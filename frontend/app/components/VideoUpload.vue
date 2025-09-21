<template>
  <div class="space-y-4">
    <div
      class="border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer"
      :class="{
        'border-gray-300 hover:border-gray-400': !isDragOver && !isUploading,
        'border-blue-400 bg-blue-50 dark:bg-blue-900/20': isDragOver,
        'border-gray-200 cursor-not-allowed': isUploading,
      }"
      @click="triggerFileSelect"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @dragenter="handleDragEnter"
      @dragleave="handleDragLeave"
    >
      <div class="mx-auto w-12 h-12 text-gray-400 mb-4">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
      </div>

      <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
        <span v-if="isDragOver">Drop your video here</span>
        <span v-else>Upload your video</span>
      </h3>

      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        <span v-if="isDragOver">Release to upload</span>
        <span v-else
          >Drag & drop or click to select a video file (max 1GB)</span
        >
      </p>

      <input
        ref="fileInput"
        type="file"
        accept="video/*"
        @change="handleFileSelect"
        class="hidden"
        :disabled="isUploading"
      />

      <Button
        @click.stop="triggerFileSelect"
        :disabled="isUploading"
        class="mb-4"
      >
        <span v-if="!isUploading">Choose Video File</span>
        <span v-else>Processing...</span>
      </Button>

      <div v-if="isUploading" class="w-full bg-gray-200 rounded-full h-2">
        <div
          class="bg-blue-600 h-2 rounded-full transition-all duration-300"
          :style="{ width: `${uploadProgress}%` }"
        ></div>
      </div>

      <p class="text-xs text-gray-400 mt-2">
        Supported formats: MP4, WebM, AVI, MOV, MKV
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { Button } from '~/components/ui/button'

interface Props {
  onUploadSuccess?: (file: File) => void
  onUploadError?: (error: string) => void
}

const props = defineProps<Props>()

const fileInput = ref<HTMLInputElement>()
const isUploading = ref(false)
const uploadProgress = ref(0)
const isDragOver = ref(false)

const MAX_FILE_SIZE = 1024 * 1024 * 1024 // 1GB in bytes

const triggerFileSelect = () => {
  fileInput.value?.click()
}

const validateFile = (file: File): string | null => {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return `File size exceeds 1GB limit. Current size: ${formatFileSize(
      file.size
    )}`
  }

  // Check file type
  if (!file.type.startsWith('video/')) {
    return 'Please select a valid video file'
  }

  return null
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  // Validate file
  const validationError = validateFile(file)
  if (validationError) {
    toast(validationError)
    target.value = '' // Clear the input
    return
  }

  try {
    isUploading.value = true
    uploadProgress.value = 0

    // Simulate progress for UI feedback while processing happens in background
    const progressInterval = setInterval(() => {
      uploadProgress.value += Math.random() * 20
      if (uploadProgress.value >= 90) {
        clearInterval(progressInterval)
      }
    }, 200)

    // Call success callback - this will trigger the VideoProcessingService
    props.onUploadSuccess?.(file)

    // Complete the progress bar
    clearInterval(progressInterval)
    uploadProgress.value = 100

    // Reset form
    target.value = ''
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Upload failed'
    toast(`Upload failed: ${errorMessage}`)
    props.onUploadError?.(errorMessage)
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
  }
}

const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  event.stopPropagation()
}

const handleDragEnter = (event: DragEvent) => {
  event.preventDefault()
  event.stopPropagation()
  isDragOver.value = true
}

const handleDragLeave = (event: DragEvent) => {
  event.preventDefault()
  event.stopPropagation()
  // Only set isDragOver to false if we're leaving the drop zone entirely
  const currentTarget = event.currentTarget as HTMLElement
  const relatedTarget = event.relatedTarget as HTMLElement
  if (!currentTarget?.contains(relatedTarget)) {
    isDragOver.value = false
  }
}

const handleDrop = async (event: DragEvent) => {
  event.preventDefault()
  event.stopPropagation()
  isDragOver.value = false

  if (isUploading.value) return

  const files = event.dataTransfer?.files
  const file = files?.[0]

  if (!file) return

  // Validate file
  const validationError = validateFile(file)
  if (validationError) {
    toast(validationError)
    return
  }

  try {
    isUploading.value = true
    uploadProgress.value = 0

    // Simulate progress for UI feedback while processing happens in background
    const progressInterval = setInterval(() => {
      uploadProgress.value += Math.random() * 20
      if (uploadProgress.value >= 90) {
        clearInterval(progressInterval)
      }
    }, 200)

    // Call success callback - this will trigger the VideoProcessingService
    props.onUploadSuccess?.(file)

    // Complete the progress bar
    clearInterval(progressInterval)
    uploadProgress.value = 100

    toast(`Upload successful! Video is being processed...`)
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Upload failed'
    toast(`Upload failed: ${errorMessage}`)
    props.onUploadError?.(errorMessage)
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
  }
}
</script>
