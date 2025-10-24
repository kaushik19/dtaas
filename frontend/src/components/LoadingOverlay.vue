<template>
  <transition name="fade">
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-container">
        <div class="loader">
          <div class="circle"></div>
          <div class="circle"></div>
          <div class="circle"></div>
          <div class="circle"></div>
        </div>
        <div class="loading-text">{{ loadingText }}</div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useLoadingStore } from '@/stores/loadingStore'

const loadingStore = useLoadingStore()
const isLoading = ref(false)
const loadingText = ref('Loading...')
let safetyTimeout = null
let showDelayTimeout = null

watch(
  () => loadingStore.isLoading,
  (newVal) => {
    if (newVal) {
      // Only show overlay after 300ms (avoid flicker for fast requests)
      clearTimeout(showDelayTimeout)
      showDelayTimeout = setTimeout(() => {
        isLoading.value = true
      }, 300)
      
      // Safety mechanism: auto-hide after 30 seconds
      clearTimeout(safetyTimeout)
      safetyTimeout = setTimeout(() => {
        console.warn('Loading overlay stuck - forcing stop')
        loadingStore.forceStop()
      }, 30000)
    } else {
      // Immediately hide
      clearTimeout(showDelayTimeout)
      clearTimeout(safetyTimeout)
      isLoading.value = false
    }
  }
)

watch(
  () => loadingStore.message,
  (newVal) => {
    loadingText.value = newVal || 'Loading...'
  }
)

onMounted(() => {
  // Clear any stuck loading state on mount
  if (loadingStore.requestCount > 0) {
    console.warn('Clearing stuck loading state on mount')
    loadingStore.forceStop()
  }
})
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  pointer-events: none; /* Allow clicks to pass through except on the loader */
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  pointer-events: auto; /* Re-enable pointer events for the loader itself */
  background: rgba(255, 255, 255, 0.95);
  padding: 32px 48px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.loader {
  display: flex;
  gap: 12px;
}

.circle {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  animation: bounce 1.4s infinite ease-in-out both;
}

.circle:nth-child(1) {
  animation-delay: -0.32s;
}

.circle:nth-child(2) {
  animation-delay: -0.16s;
}

.circle:nth-child(3) {
  animation-delay: 0s;
}

.circle:nth-child(4) {
  animation-delay: 0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.loading-text {
  color: #303133;
  font-size: 16px;
  font-weight: 500;
  text-align: center;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

