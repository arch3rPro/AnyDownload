<template>
  <NConfigProvider :theme="darkTheme">
    <NMessageProvider>
      <DouyinDownloader />
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { darkTheme, NConfigProvider, NMessageProvider } from 'naive-ui'
import DouyinDownloader from './components/DouyinDownloader.vue'
</script>