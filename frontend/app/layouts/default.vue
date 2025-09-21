<template>
  <div class="min-h-screen max-w-7xl px-4 py-8 mx-auto flex flex-col gap-8">
    <header class="flex items-center justify-between">
      <NuxtLink to="/" class="flex items-center gap-2">
        <Icon icon="ri:camera-lens-ai-fill" class="size-8" />
        <h1 class="text-2xl font-bold">Visionaree</h1>
      </NuxtLink>
      <div class="flex items-center gap-4">
        <ThemeToggle />
      </div>
    </header>
    <main>
      <NuxtPage />
    </main>
    <Toaster />
  </div>
</template>

<script lang="ts" setup>
import { Icon } from '@iconify/vue'
import 'vue-sonner/style.css'
</script>
