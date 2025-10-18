<template>
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
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>Tasks</span>
        </el-menu-item>
        <el-menu-item index="/task-builder">
          <el-icon><Edit /></el-icon>
          <span>Task Builder</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h3>{{ pageTitle }}</h3>
          <div class="header-right">
            <el-badge :value="runningTasks" :hidden="runningTasks === 0" class="item">
              <el-button circle>
                <el-icon><Bell /></el-icon>
              </el-button>
            </el-badge>
          </div>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskStore } from './stores/taskStore'
import { useWebSocketStore } from './stores/websocketStore'

const route = useRoute()
const taskStore = useTaskStore()
const wsStore = useWebSocketStore()

const currentRoute = computed(() => route.path)
const runningTasks = computed(() => taskStore.runningTasksCount)

const pageTitle = computed(() => {
  const titles = {
    '/': 'Dashboard',
    '/connectors': 'Connectors',
    '/tasks': 'Tasks',
    '/task-builder': 'Task Builder'
  }
  return titles[route.path] || 'DTaaS'
})

onMounted(() => {
  wsStore.connect()
  taskStore.fetchTasks()
})

onUnmounted(() => {
  wsStore.disconnect()
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

