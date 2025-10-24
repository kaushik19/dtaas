import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const unreadCount = ref(0)
  
  const addNotification = (notification) => {
    const newNotification = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      read: false,
      ...notification
    }
    
    notifications.value.unshift(newNotification)
    unreadCount.value++
    
    // Keep only last 50 notifications
    if (notifications.value.length > 50) {
      notifications.value = notifications.value.slice(0, 50)
    }
  }
  
  const markAsRead = (id) => {
    const notification = notifications.value.find(n => n.id === id)
    if (notification && !notification.read) {
      notification.read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }
  
  const markAllAsRead = () => {
    notifications.value.forEach(n => n.read = true)
    unreadCount.value = 0
  }
  
  const clearAll = () => {
    notifications.value = []
    unreadCount.value = 0
  }
  
  const removeNotification = (id) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      const notification = notifications.value[index]
      if (!notification.read) {
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
      notifications.value.splice(index, 1)
    }
  }
  
  // Computed properties
  const unreadNotifications = computed(() => 
    notifications.value.filter(n => !n.read)
  )
  
  const recentNotifications = computed(() => 
    notifications.value.slice(0, 10)
  )
  
  return {
    notifications,
    unreadCount,
    unreadNotifications,
    recentNotifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    clearAll,
    removeNotification
  }
})

