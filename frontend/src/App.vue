<template>
  <LoadingOverlay />
  <el-container class="app-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>DTaaS</h2>
        <p>Data Transfer Service</p>
      </div>
      <el-menu
        :default-active="currentRoute"
        router
        class="sidebar-menu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1890ff"
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="/connectors">
          <el-icon><Connection /></el-icon>
          <span>Connectors</span>
        </el-menu-item>
        <el-menu-item index="/variables">
          <el-icon><SetUp /></el-icon>
          <span>Global Variables</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>Tasks</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h3>{{ pageTitle }}</h3>
          <div class="header-right">
            <el-tooltip content="Notifications" placement="bottom">
              <el-badge 
                :value="notificationStore.unreadCount" 
                :hidden="notificationStore.unreadCount === 0"
                :max="99"
              >
                <el-button 
                  circle
                  @click="showNotifications = true"
                  :type="notificationStore.unreadCount > 0 ? 'primary' : ''"
                >
                  <el-icon><Bell /></el-icon>
                </el-button>
              </el-badge>
            </el-tooltip>
            
            <el-tooltip content="Running Tasks" placement="bottom">
              <el-badge 
                :value="runningTasks" 
                :hidden="runningTasks === 0"
                type="success"
              >
                <el-button circle @click="goToTasks">
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-badge>
            </el-tooltip>
          </div>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
    
    <!-- Notification Panel -->
    <NotificationPanel v-model="showNotifications" />
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from './stores/taskStore'
import { useWebSocketStore } from './stores/websocketStore'
import { useNotificationStore } from './stores/notificationStore'
import { DataAnalysis, Connection, List, Bell, SetUp, VideoPlay } from '@element-plus/icons-vue'
import LoadingOverlay from './components/LoadingOverlay.vue'
import NotificationPanel from './components/NotificationPanel.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const wsStore = useWebSocketStore()
const notificationStore = useNotificationStore()

const showNotifications = ref(false)
const currentRoute = computed(() => route.path)
const runningTasks = computed(() => taskStore.runningTasksCount)

const pageTitle = computed(() => {
  const titles = {
    '/': 'Dashboard',
    '/connectors': 'Connectors',
    '/variables': 'Global Variables',
    '/tasks': 'Tasks'
  }
  
  if (route.path.startsWith('/tasks/') && route.path.includes('/detail')) {
    return 'Task Detail'
  }
  if (route.path.startsWith('/task-builder')) {
    return route.params.id ? 'Edit Task' : 'Create Task'
  }
  
  return titles[route.path] || 'DTaaS'
})

const goToTasks = () => {
  router.push('/tasks')
}

// Listen for WebSocket messages and create notifications
if (typeof window !== 'undefined') {
  window.addEventListener('ws-message', (event) => {
    const data = event.detail
    
    if (data.type === 'task_update') {
      data.tasks.forEach(task => {
        // Notify on task completion
        if (task.status === 'completed') {
          notificationStore.addNotification({
            type: 'task_completed',
            title: 'Task Completed',
            message: `Task "${task.name}" has completed successfully`,
            taskId: task.id
          })
        }
        
        // Notify on task failure
        if (task.status === 'failed') {
          notificationStore.addNotification({
            type: 'error',
            title: 'Task Failed',
            message: `Task "${task.name}" has failed`,
            taskId: task.id
          })
        }
      })
    }
  })
}

onMounted(() => {
  // Connect WebSocket after a delay to not block initial render
  setTimeout(() => {
    try {
      wsStore.connect()
    } catch (error) {
      console.error('WebSocket connection failed:', error)
    }
  }, 1000)
  
  // Fetch tasks
  taskStore.fetchTasks().catch(err => {
    console.error('Failed to fetch tasks:', err)
  })
  
  // Welcome notification
  notificationStore.addNotification({
    type: 'info',
    title: 'Welcome to DTaaS',
    message: 'Data Transfer as a Service is ready'
  })
})

onUnmounted(() => {
  try {
    wsStore.disconnect()
  } catch (error) {
    console.error('WebSocket disconnect failed:', error)
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background-color: #001529;
  overflow-y: auto;
}

.logo {
  padding: 20px;
  text-align: center;
  color: #fff;
  border-bottom: 1px solid #002140;
}

.logo h2 {
  margin: 0;
  font-size: 24px;
  color: #1890ff;
}

.logo p {
  margin: 5px 0 0;
  font-size: 12px;
  color: #8c8c8c;
}

.sidebar-menu {
  border: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 24px;
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.main-content {
  background-color: #f0f2f5;
  overflow-y: auto;
  padding: 24px;
}
</style>

