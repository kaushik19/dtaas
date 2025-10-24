<template>
  <el-drawer
    v-model="visible"
    title="Notifications"
    :size="400"
    direction="rtl"
    @close="handleClose"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-title">
          <el-icon><Bell /></el-icon>
          Notifications
        </span>
        <div class="header-actions">
          <el-button 
            text 
            size="small" 
            @click="markAllAsRead"
            v-if="notificationStore.unreadCount > 0"
          >
            Mark all read
          </el-button>
          <el-button 
            text 
            size="small" 
            type="danger"
            @click="clearAll"
            v-if="notificationStore.notifications.length > 0"
          >
            Clear all
          </el-button>
        </div>
      </div>
    </template>

    <div v-if="notificationStore.notifications.length === 0" class="empty-state">
      <el-empty description="No notifications">
        <template #image>
          <el-icon :size="80" color="#909399"><Bell /></el-icon>
        </template>
      </el-empty>
    </div>

    <div v-else class="notifications-list">
      <div
        v-for="notification in notificationStore.notifications"
        :key="notification.id"
        :class="['notification-item', { 'unread': !notification.read }]"
        @click="handleNotificationClick(notification)"
      >
        <div class="notification-icon">
          <el-icon
            :size="24"
            :color="getIconColor(notification.type)"
          >
            <component :is="getIcon(notification.type)" />
          </el-icon>
        </div>
        
        <div class="notification-content">
          <div class="notification-header">
            <span class="notification-title">{{ notification.title }}</span>
            <span
              v-if="!notification.read"
              class="unread-dot"
            ></span>
          </div>
          
          <div class="notification-message">{{ notification.message }}</div>
          
          <div class="notification-footer">
            <span class="notification-time">{{ formatTime(notification.timestamp) }}</span>
            <el-button
              text
              size="small"
              type="danger"
              @click.stop="removeNotification(notification.id)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notificationStore'
import { ElMessage } from 'element-plus'
import {
  Bell,
  SuccessFilled,
  WarningFilled,
  InfoFilled,
  Close,
  VideoPlay,
  VideoPause,
  CircleCheck
} from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const router = useRouter()
const notificationStore = useNotificationStore()
const visible = ref(props.modelValue)

watch(() => props.modelValue, (newVal) => {
  visible.value = newVal
})

watch(visible, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleClose = () => {
  visible.value = false
}

const getIcon = (type) => {
  const icons = {
    success: SuccessFilled,
    error: WarningFilled,
    warning: WarningFilled,
    info: InfoFilled,
    task_completed: CircleCheck,
    task_started: VideoPlay,
    task_stopped: VideoPause
  }
  return icons[type] || InfoFilled
}

const getIconColor = (type) => {
  const colors = {
    success: '#67c23a',
    error: '#f56c6c',
    warning: '#e6a23c',
    info: '#909399',
    task_completed: '#67c23a',
    task_started: '#409eff',
    task_stopped: '#e6a23c'
  }
  return colors[type] || '#909399'
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}

const handleNotificationClick = (notification) => {
  notificationStore.markAsRead(notification.id)
  
  // Navigate to related page if taskId is provided
  if (notification.taskId) {
    router.push(`/tasks/${notification.taskId}/detail`)
    visible.value = false
  }
}

const markAllAsRead = () => {
  notificationStore.markAllAsRead()
  ElMessage.success('All notifications marked as read')
}

const clearAll = () => {
  notificationStore.clearAll()
  ElMessage.success('All notifications cleared')
}

const removeNotification = (id) => {
  notificationStore.removeNotification(id)
}
</script>

<style scoped>
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.3s;
}

.notification-item:hover {
  background: #f5f7fa;
}

.notification-item.unread {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.notification-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  border-radius: 50%;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.unread-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
  display: inline-block;
}

.notification-message {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  line-height: 1.5;
  word-wrap: break-word;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-time {
  font-size: 12px;
  color: #909399;
}
</style>

