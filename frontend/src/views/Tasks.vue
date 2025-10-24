<template>
  <div class="tasks">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Tasks</span>
          <div class="header-actions">
            <el-tooltip content="Refresh tasks" placement="bottom">
              <el-button 
                @click="refreshTasks" 
                :icon="Refresh" 
                circle
                :loading="taskStore.loading"
              />
            </el-tooltip>
            <el-button type="primary" @click="$router.push('/task-builder')">
              <el-icon><Plus /></el-icon>
              Create Task
            </el-button>
          </div>
        </div>
      </template>

      <!-- Bulk Actions Bar -->
      <div v-if="selectedTasks.length > 0" class="bulk-actions-bar">
        <div class="selected-info">
          <el-checkbox 
            v-model="selectAll" 
            @change="handleSelectAll"
            :indeterminate="selectedTasks.length > 0 && selectedTasks.length < taskStore.tasks.length"
          />
          <span class="selected-count">{{ selectedTasks.length }} selected</span>
        </div>
        <div class="bulk-buttons">
          <el-button 
            size="small" 
            type="success"
            @click="bulkStart"
            :disabled="!canBulkStart"
          >
            <el-icon><VideoPlay /></el-icon>
            Start Selected
          </el-button>
          <el-button 
            size="small" 
            type="warning"
            @click="bulkPause"
            :disabled="!canBulkPause"
          >
            <el-icon><VideoPause /></el-icon>
            Pause Selected
          </el-button>
          <el-button 
            size="small" 
            type="danger"
            @click="bulkStop"
            :disabled="!canBulkStop"
          >
            <el-icon><CloseBold /></el-icon>
            Stop Selected
          </el-button>
          <el-divider direction="vertical" />
          <el-button 
            size="small" 
            type="danger"
            @click="bulkDelete"
          >
            <el-icon><Delete /></el-icon>
            Delete Selected
          </el-button>
          <el-button 
            size="small" 
            text
            @click="clearSelection"
          >
            Clear Selection
          </el-button>
        </div>
      </div>

      <el-table 
        :data="taskStore.tasks" 
        v-loading="taskStore.loading"
        @selection-change="handleSelectionChange"
        @row-click="handleRowClick"
        style="cursor: pointer;"
      >
        <el-table-column type="selection" width="55" :selectable="isSelectable" />
        <el-table-column prop="name" label="Name" width="200" />
        <el-table-column prop="mode" label="Mode" width="150">
          <template #default="{ row }">
            <el-tag :type="getModeType(row.mode)" size="small">
              {{ row.mode }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="schedule_type" label="Schedule" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.schedule_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Source Tables" width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.source_tables.join(', ')">
              <span>{{ row.source_tables.length }} table(s)</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="Status" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Progress" width="200">
          <template #default="{ row }">
            <div v-if="row.status === 'failed'" style="color: #f56c6c;">
              <el-icon><WarningFilled /></el-icon>
              <span style="margin-left: 5px;">Failed</span>
              <el-button 
                text 
                type="danger" 
                size="small" 
                @click="viewExecutions(row)"
                style="margin-left: 10px;"
              >
                View Error
              </el-button>
            </div>
            <el-progress 
              v-else
              :percentage="row.current_progress_percent" 
              :status="row.status === 'completed' ? 'success' : null"
            />
          </template>
        </el-table-column>
        <el-table-column label="Last Run" width="180">
          <template #default="{ row }">
            {{ row.last_run_at ? formatDate(row.last_run_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status !== 'running'"
                size="small" 
                type="success"
                @click.stop="controlTask(row.id, 'start')"
              >
                <el-icon><VideoPlay /></el-icon>
                Start
              </el-button>
              <el-button 
                v-if="row.status === 'running'"
                size="small" 
                type="danger"
                @click.stop="controlTask(row.id, 'stop')"
              >
                <el-icon><CloseBold /></el-icon>
                Stop
              </el-button>
              <el-button 
                size="small" 
                @click.stop="editTask(row)"
                :disabled="row.status === 'running'"
              >
                <el-icon><Edit /></el-icon>
                Edit
              </el-button>
            </el-button-group>
            <el-dropdown 
              trigger="click" 
              @command="(cmd) => handleDropdownCommand(cmd, row)"
              style="margin-left: 8px;"
            >
              <el-button size="small" circle>
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="detail">
                    <el-icon><DataAnalysis /></el-icon>
                    View Detail
                  </el-dropdown-item>
                  <el-dropdown-item command="history">
                    <el-icon><View /></el-icon>
                    View History
                  </el-dropdown-item>
                  <el-dropdown-item 
                    v-if="row.status === 'running'"
                    command="pause"
                  >
                    <el-icon><VideoPause /></el-icon>
                    Pause Task
                  </el-dropdown-item>
                  <el-dropdown-item divided command="delete">
                    <el-icon><Delete /></el-icon>
                    <span style="color: #f56c6c;">Delete Task</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Execution History Dialog -->
    <el-dialog 
      v-model="executionDialogVisible" 
      title="Execution History" 
      width="90%"
    >
      <el-table :data="executions" v-loading="loadingExecutions">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="execution_type" label="Type" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.execution_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="processed_rows" label="Rows" width="120" />
        <el-table-column prop="data_size_mb" label="Size (MB)" width="120">
          <template #default="{ row }">
            {{ row.data_size_mb.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="Progress" width="150">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.progress_percent" 
              :status="row.status === 'success' ? 'success' : null"
            />
          </template>
        </el-table-column>
        <el-table-column prop="rows_per_second" label="Rows/sec" width="120">
          <template #default="{ row }">
            {{ row.rows_per_second ? row.rows_per_second.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_seconds" label="Duration" width="120">
          <template #default="{ row }">
            {{ row.duration_seconds ? `${row.duration_seconds.toFixed(1)}s` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="Started" width="180">
          <template #default="{ row }">
            {{ row.started_at ? formatDate(row.started_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="Error" min-width="200">
          <template #default="{ row }">
            <div v-if="row.error_message" class="error-cell">
              <el-alert 
                :title="truncate(row.error_message, 80)" 
                type="error" 
                :closable="false"
                style="padding: 8px;"
              >
                <template #default>
                  <div style="font-size: 12px; margin-top: 5px;">
                    {{ row.error_message }}
                  </div>
                </template>
              </el-alert>
            </div>
            <span v-else style="color: #67c23a;">
              <el-icon><SuccessFilled /></el-icon> Success
            </span>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="150" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small"
              @click="viewDetailFromExecution(row.task_id)"
            >
              <el-icon><DataAnalysis /></el-icon>
              View Detail
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/taskStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, VideoPause, View, Edit, CloseBold, WarningFilled, SuccessFilled, DataAnalysis, Refresh, Delete, MoreFilled } from '@element-plus/icons-vue'

const router = useRouter()
const taskStore = useTaskStore()
const executionDialogVisible = ref(false)
const executions = ref([])
const loadingExecutions = ref(false)
const selectedTasks = ref([])
const selectAll = ref(false)

// Computed properties for bulk actions
const canBulkStart = computed(() => {
  return selectedTasks.value.some(task => task.status !== 'running')
})

const canBulkPause = computed(() => {
  return selectedTasks.value.some(task => task.status === 'running')
})

const canBulkStop = computed(() => {
  return selectedTasks.value.some(task => task.status === 'running')
})

const getModeType = (mode) => {
  const types = {
    'full_load': 'primary',
    'cdc': 'success',
    'full_load_then_cdc': 'warning'
  }
  return types[mode] || 'info'
}

const getStatusType = (status) => {
  const types = {
    'created': 'info',
    'running': 'primary',
    'paused': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'stopped': 'info',
    'success': 'success',
    'pending': 'info'
  }
  return types[status] || 'info'
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const truncate = (str, length) => {
  return str.length > length ? str.substring(0, length) + '...' : str
}

const controlTask = async (id, action) => {
  try {
    await taskStore.controlTask(id, action)
    ElMessage.success(`Task ${action}ed successfully`)
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || `Failed to ${action} task`
    ElMessage.error({
      message: errorMsg,
      duration: 8000,
      showClose: true
    })
  }
}

const viewDetail = (task) => {
  router.push(`/tasks/${task.id}/detail`)
}

const viewDetailFromExecution = (taskId) => {
  executionDialogVisible.value = false
  router.push(`/tasks/${taskId}/detail`)
}

const viewExecutions = async (task) => {
  loadingExecutions.value = true
  executionDialogVisible.value = true
  try {
    executions.value = await taskStore.getTaskExecutions(task.id)
  } catch (error) {
    ElMessage.error('Failed to load execution history')
  } finally {
    loadingExecutions.value = false
  }
}

const editTask = (task) => {
  router.push(`/task-builder/${task.id}`)
}

const deleteTask = async (id) => {
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this task?', 'Warning', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    await taskStore.deleteTask(id)
    ElMessage.success('Task deleted successfully')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete task')
    }
  }
}

const refreshTasks = async () => {
  try {
    await taskStore.fetchTasks()
    ElMessage.success('Tasks refreshed')
  } catch (error) {
    ElMessage.error('Failed to refresh tasks')
  }
}

// Selection handlers
const handleSelectionChange = (selection) => {
  selectedTasks.value = selection
  selectAll.value = selection.length === taskStore.tasks.length && selection.length > 0
}

const handleSelectAll = (value) => {
  // This is handled by el-table automatically
}

const clearSelection = () => {
  selectedTasks.value = []
  selectAll.value = false
}

const isSelectable = (row) => {
  return true // All rows are selectable
}

const handleRowClick = (row, column, event) => {
  // Only navigate if not clicking on action buttons
  if (!event.target.closest('.el-button') && !event.target.closest('.el-checkbox')) {
    viewDetail(row)
  }
}

// Dropdown command handler
const handleDropdownCommand = (command, row) => {
  switch (command) {
    case 'detail':
      viewDetail(row)
      break
    case 'history':
      viewExecutions(row)
      break
    case 'pause':
      controlTask(row.id, 'pause')
      break
    case 'delete':
      deleteTask(row.id)
      break
  }
}

// Bulk actions
const bulkStart = async () => {
  const tasksToStart = selectedTasks.value.filter(task => task.status !== 'running')
  if (tasksToStart.length === 0) return

  try {
    await Promise.all(tasksToStart.map(task => taskStore.controlTask(task.id, 'start')))
    ElMessage.success(`Started ${tasksToStart.length} task(s)`)
    clearSelection()
  } catch (error) {
    ElMessage.error('Failed to start some tasks')
  }
}

const bulkPause = async () => {
  const tasksToPause = selectedTasks.value.filter(task => task.status === 'running')
  if (tasksToPause.length === 0) return

  try {
    await Promise.all(tasksToPause.map(task => taskStore.controlTask(task.id, 'pause')))
    ElMessage.success(`Paused ${tasksToPause.length} task(s)`)
    clearSelection()
  } catch (error) {
    ElMessage.error('Failed to pause some tasks')
  }
}

const bulkStop = async () => {
  const tasksToStop = selectedTasks.value.filter(task => task.status === 'running')
  if (tasksToStop.length === 0) return

  try {
    await Promise.all(tasksToStop.map(task => taskStore.controlTask(task.id, 'stop')))
    ElMessage.success(`Stopped ${tasksToStop.length} task(s)`)
    clearSelection()
  } catch (error) {
    ElMessage.error('Failed to stop some tasks')
  }
}

const bulkDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete ${selectedTasks.value.length} task(s)?`,
      'Warning',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    await Promise.all(selectedTasks.value.map(task => taskStore.deleteTask(task.id)))
    ElMessage.success(`Deleted ${selectedTasks.value.length} task(s)`)
    clearSelection()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete some tasks')
    }
  }
}

onMounted(() => {
  taskStore.fetchTasks()
})
</script>

<style scoped>
.tasks {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.error-text {
  color: #f56c6c;
  cursor: pointer;
}

.bulk-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px 0 rgba(102, 126, 234, 0.3);
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
  font-weight: 500;
}

.selected-count {
  font-size: 14px;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 12px;
  border-radius: 12px;
}

.bulk-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.bulk-actions-bar :deep(.el-button) {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>

