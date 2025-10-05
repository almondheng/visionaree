<template>
  <div class="flex flex-row items-center gap-3 space-y-0 border-b px-4 py-3">
    <div class="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10">
      <slot name="icon">
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
      </slot>
    </div>
    <div>
      <h3 class="text-sm font-semibold">{{ title }}</h3>
      <p class="text-xs text-muted-foreground">{{ description }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>