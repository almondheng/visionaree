<template>
  <video
    class="w-full h-full backdrop-blur-2xl backdrop-brightness-75 rounded-md"
    ref="videoPlayer"
    controls
    @timeupdate="handleTimeUpdate"
  ></video>
</template>

<script setup lang="ts">
import Hls, { ErrorDetails, ErrorTypes } from "hls.js";

const videoPlayer: Ref<HTMLMediaElement | undefined> = ref();
const props = defineProps<{
  src: string;
}>();
const emit = defineEmits<{
  error: [boolean];
  progress: [number];
}>();

const handleTimeUpdate = () => {
  if (videoPlayer.value && videoPlayer.value.duration) {
    const progress =
      (videoPlayer.value.currentTime / videoPlayer.value.duration) * 100;
    emit("progress", progress);
  }
};

onMounted(() => {
  if (!videoPlayer.value) return;

  if (Hls.isSupported()) {
    const hls = new Hls({
      enableWorker: true,
      lowLatencyMode: true,
      backBufferLength: 90,
    });
    hls.loadSource(props.src);
    hls.attachMedia(videoPlayer.value);

    hls.on(Hls.Events.ERROR, (_, data) => {
      const { type, details, fatal } = data;
      if (!fatal) {
        console.warn(`[HLS] Non-fatal error occurred: ${details}`);
        return;
      }
      if (type === ErrorTypes.NETWORK_ERROR) {
        if (details === ErrorDetails.MANIFEST_LOAD_ERROR) {
          console.error("[HLS] Load error.");
          emit("error", true);
          return;
        }
      }
      if (type === ErrorTypes.MEDIA_ERROR) {
        console.warn("[HLS] Attempting to recover from media error...");
        hls.recoverMediaError();
        return;
      }
      console.error(`[HLS] Unhandled error: ${type}`);
      emit("error", true);
    });
    return;
  } else if (videoPlayer.value.canPlayType("application/vnd.apple.mpegurl")) {
    videoPlayer.value.src = props.src;
  } else {
    alert("Your browser does not support HLS playback.");
  }
});
</script>
