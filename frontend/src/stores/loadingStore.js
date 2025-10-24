import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  const isLoading = ref(false)
  const message = ref('Loading...')
  const requestCount = ref(0)

  const startLoading = (msg = 'Loading...') => {
    requestCount.value++
    message.value = msg
    isLoading.value = true
  }

  const stopLoading = () => {
    requestCount.value = Math.max(0, requestCount.value - 1)
    if (requestCount.value === 0) {
      isLoading.value = false
    }
  }

  const forceStop = () => {
    requestCount.value = 0
    isLoading.value = false
  }

  return {
    isLoading,
    message,
    startLoading,
    stopLoading,
    forceStop
  }
})

