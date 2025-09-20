<script lang="ts" setup>
defineProps<{
  dimensions: { width: number; height: number };
}>();

const canvas = useTemplateRef<HTMLCanvasElement>("testCanvas");

onMounted(() => {
  if (!canvas.value) return;
  const ctx = canvas.value.getContext("2d");
  if (!ctx) return;

  // Draw a simple grid for demonstration
  const step = 20;
  ctx.strokeStyle = "rgba(200, 200, 200, 0.5)";
  for (let x = 0; x < canvas.value.width; x += step) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.value.height);
    ctx.stroke();
  }
  for (let y = 0; y < canvas.value.height; y += step) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.value.width, y);
    ctx.stroke();
  }
});
</script>

<template>
  <div
    :class="`aspect-[${dimensions.width}/${dimensions.height}] relative rounded-lg overflow-hidden`"
  >
    <canvas
      ref="testCanvas"
      :width="dimensions.width"
      :height="dimensions.height"
      class="w-full absolute inset-0"
    />
    <slot />
  </div>
</template>
