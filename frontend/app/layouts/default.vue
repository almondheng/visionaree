<template>
  <div class="min-h-screen max-w-7xl px-4 py-8 mx-auto flex flex-col gap-8">
    <header class="flex items-center justify-between">
      <NuxtLink to="/" class="flex items-center gap-2">
        <img src="/lookowl.svg" alt="Lookowl" class="size-8 dark:invert" />
        <h1 class="text-2xl font-bold">Lookowl</h1>
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
import 'vue-sonner/style.css'
</script>
