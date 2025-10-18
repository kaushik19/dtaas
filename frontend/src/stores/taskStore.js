import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksAPI } from '@/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const loading = ref(false)
  const error = ref(null)

  const fetchTasks = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await tasksAPI.list()
      tasks.value = response.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const createTask = async (data) => {
    loading.value = true
    error.value = null
    try {
      const response = await tasksAPI.create(data)
      tasks.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const updateTask = async (id, data) => {
    loading.value = true
    error.value = null
    try {
      const response = await tasksAPI.update(id, data)
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const deleteTask = async (id) => {
    loading.value = true
    error.value = null
    try {
      await tasksAPI.delete(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const controlTask = async (id, action) => {
    try {
      const response = await tasksAPI.control(id, action)
      // Refresh task after control action
      await fetchTasks()
      return response.data
    } catch (e) {
      throw e
    }
  }

  const getTaskExecutions = async (id) => {
    try {
      const response = await tasksAPI.getExecutions(id)
      return response.data
    } catch (e) {
      throw e
    }
  }

  const runningTasksCount = computed(() => {
    return tasks.value.filter(t => t.status === 'running').length
  })

  // Listen for WebSocket updates
  if (typeof window !== 'undefined') {
    window.addEventListener('ws-message', (event) => {
      const data = event.detail
      if (data.type === 'task_update') {
        // Update task statuses from WebSocket
        data.tasks.forEach(updatedTask => {
          const index = tasks.value.findIndex(t => t.id === updatedTask.id)
          if (index !== -1) {
            tasks.value[index].status = updatedTask.status
            tasks.value[index].current_progress_percent = updatedTask.progress
          }
        })
      }
    })
  }

  return {
    tasks,
    loading,
    error,
    runningTasksCount,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    controlTask,
    getTaskExecutions
  }
})

