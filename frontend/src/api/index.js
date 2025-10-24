import axios from 'axios'
import { useLoadingStore } from '@/stores/loadingStore'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - show loading
apiClient.interceptors.request.use(
  (config) => {
    const loadingStore = useLoadingStore()
    loadingStore.startLoading()
    return config
  },
  (error) => {
    const loadingStore = useLoadingStore()
    loadingStore.stopLoading()
    return Promise.reject(error)
  }
)

// Response interceptor - hide loading
apiClient.interceptors.response.use(
  (response) => {
    const loadingStore = useLoadingStore()
    loadingStore.stopLoading()
    return response
  },
  (error) => {
    const loadingStore = useLoadingStore()
    loadingStore.stopLoading()
    return Promise.reject(error)
  }
)

// Connectors API
export const connectorsAPI = {
  list(connectorType = null) {
    return apiClient.get('/connectors/', { params: { connector_type: connectorType } })
  },
  get(id) {
    return apiClient.get(`/connectors/${id}`)
  },
  create(data) {
    return apiClient.post('/connectors/', data)
  },
  update(id, data) {
    return apiClient.put(`/connectors/${id}`, data)
  },
  delete(id) {
    return apiClient.delete(`/connectors/${id}`)
  },
  test(id) {
    return apiClient.post(`/connectors/${id}/test`)
  },
  testConfig(data) {
    return apiClient.post('/connectors/test-config', data)
  },
  listTables(id) {
    return apiClient.get(`/connectors/${id}/tables`)
  }
}

// Tasks API
export const tasksAPI = {
  list() {
    return apiClient.get('/tasks/')
  },
  get(id) {
    return apiClient.get(`/tasks/${id}`)
  },
  create(data) {
    return apiClient.post('/tasks/', data)
  },
  update(id, data) {
    return apiClient.put(`/tasks/${id}`, data)
  },
  delete(id) {
    return apiClient.delete(`/tasks/${id}`)
  },
  control(id, action) {
    return apiClient.post(`/tasks/${id}/control`, { action })
  },
  getExecutions(id) {
    return apiClient.get(`/tasks/${id}/executions`)
  }
}

// Dashboard API
export const dashboardAPI = {
  getMetrics() {
    return apiClient.get('/dashboard/metrics')
  }
}

export default apiClient

