<template>
  <div class="tasks">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Tasks</span>
          <el-button type="primary" @click="$router.push('/task-builder')">
            <el-icon><Plus /></el-icon>
            Create Task
          </el-button>
        </div>
      </template>

      <el-table :data="taskStore.tasks" v-loading="taskStore.loading">
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
            <el-progress 
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
        <el-table-column label="Actions" width="300" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status !== 'running'"
              size="small" 
              type="primary"
              @click="controlTask(row.id, 'start')"
            >
              <el-icon><VideoPlay /></el-icon>
              Start
            </el-button>
            <el-button 
              v-if="row.status === 'running'"
              size="small" 
              type="warning"
              @click="controlTask(row.id, 'pause')"
            >
              <el-icon><VideoPause /></el-icon>
              Pause
            </el-button>
            <el-button 
              v-if="row.status === 'running'"
              size="small" 
              type="danger"
              @click="controlTask(row.id, 'stop')"
            >
              <el-icon><VideoStop /></el-icon>
              Stop
            </el-button>
            <el-button 
              size="small"
              @click="viewExecutions(row)"
            >
              <el-icon><View /></el-icon>
              History
            </el-button>
            <el-button 
              size="small" 
              type="danger"
              @click="deleteTask(row.id)"
            >
              Delete
            </el-button>
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
            <el-tooltip v-if="row.error_message" :content="row.error_message">
              <span class="error-text">{{ truncate(row.error_message, 50) }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { ElMessage, ElMessageBox } from 'element-plus'

const taskStore = useTaskStore()
const executionDialogVisible = ref(false)
const executions = ref([])
const loadingExecutions = ref(false)

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
    ElMessage.error(`Failed to ${action} task`)
  }
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

onMounted(() => {
  taskStore.fetchTasks()
  
  // Refresh tasks every 3 seconds
  setInterval(() => {
    taskStore.fetchTasks()
  }, 3000)
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

.error-text {
  color: #f56c6c;
  cursor: pointer;
}
</style>

