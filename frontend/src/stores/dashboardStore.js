import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardAPI } from '@/api'

export const useDashboardStore = defineStore('dashboard', () => {
  const metrics = ref({
    total_tasks: 0,
    active_tasks: 0,
    running_tasks: 0,
    total_rows_transferred: 0,
    total_data_transferred_mb: 0,
    successful_executions: 0,
    failed_executions: 0,
    avg_rows_per_second: 0,
    recent_executions: []
  })
  const loading = ref(false)
  const error = ref(null)

  const fetchMetrics = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await dashboardAPI.getMetrics()
      metrics.value = response.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    metrics,
    loading,
    error,
    fetchMetrics
  }
})

