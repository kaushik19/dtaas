<template>
  <div class="task-detail">
    <el-page-header @back="$router.back()" :title="taskDetail?.task?.name || 'Task Detail'">
      <template #content>
        <div class="header-content">
          <span class="task-name">{{ taskDetail?.task?.name }}</span>
          <el-tag :type="getStatusType(taskDetail?.task?.status)" size="large">
            {{ taskDetail?.task?.status }}
          </el-tag>
        </div>
      </template>
      <template #extra>
        <div class="header-actions">
          <el-button 
            v-if="taskDetail?.task?.status !== 'running'"
            type="primary"
            @click="controlTask('start')"
          >
            <el-icon><VideoPlay /></el-icon>
            Start Task
          </el-button>
          <el-button 
            v-if="taskDetail?.task?.status === 'running'"
            type="danger"
            @click="controlTask('stop')"
          >
            <el-icon><CloseBold /></el-icon>
            Stop Task
          </el-button>
        </div>
      </template>
    </el-page-header>

    <div v-loading="loading" class="content">
      <!-- Task Overview Card -->
      <el-card class="overview-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>Task Overview</span>
            <el-tooltip content="Refresh data" placement="top">
              <el-button 
                @click="refreshData" 
                :icon="Refresh" 
                type="primary"
                size="small"
                circle 
                :loading="loading"
              />
            </el-tooltip>
          </div>
        </template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="Last Update">
            <el-tag type="success">{{ lastUpdate }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Mode">
            <el-tag :type="getModeType(taskDetail?.task?.mode)">
              {{ taskDetail?.task?.mode }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Schedule">
            <el-tag>{{ taskDetail?.task?.schedule_type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Tables">
            {{ taskDetail?.task?.source_tables?.length || 0 }} table(s)
          </el-descriptions-item>
          <el-descriptions-item label="Overall Progress">
            <el-progress 
              :percentage="taskDetail?.task?.current_progress_percent || 0" 
              :status="taskDetail?.task?.status === 'completed' ? 'success' : null"
            />
          </el-descriptions-item>
          <el-descriptions-item label="Last Run">
            {{ taskDetail?.task?.last_run_at ? formatDate(taskDetail.task.last_run_at) : 'Never' }}
          </el-descriptions-item>
          <el-descriptions-item label="Created">
            {{ taskDetail?.task?.created_at ? formatDate(taskDetail.task.created_at) : '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Table-wise Progress Tabs -->
      <el-card class="progress-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>Table-wise Progress</span>
            <el-tooltip content="Refresh data" placement="top">
              <el-button 
                @click="refreshData" 
                :icon="Refresh" 
                type="primary"
                circle 
                :loading="loading"
              />
            </el-tooltip>
          </div>
        </template>

        <el-tabs v-model="activeTab" type="card">
          <!-- Full Load Tab -->
          <el-tab-pane label="Full Load" name="full_load">
            <el-empty 
              v-if="!taskDetail?.full_load_progress?.length" 
              description="No full load data available"
            />
            <el-table 
              v-else
              :key="updateCounter"
              :data="taskDetail.full_load_progress" 
              stripe
              style="width: 100%"
            >
              <el-table-column prop="table_name" label="Table Name" width="250" fixed />
              <el-table-column label="Status" width="120">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" size="small">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="Progress" width="300">
                <template #default="{ row }">
                  <div v-if="row.status === 'failed'">
                    <el-tag type="danger" size="small">Failed</el-tag>
                  </div>
                  <div v-else>
                    <el-progress 
                      :percentage="calculateProgress(row.processed_rows, row.total_rows)" 
                      :status="row.status === 'success' || row.status === 'completed' ? 'success' : null"
                    />
                    <span class="progress-text">
                      {{ formatNumber(row.processed_rows) }} / {{ formatNumber(row.total_rows) }} rows
                    </span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="total_rows" label="Total Rows" width="120">
                <template #default="{ row }">
                  {{ formatNumber(row.total_rows) }}
                </template>
              </el-table-column>
              <el-table-column prop="processed_rows" label="Processed" width="120">
                <template #default="{ row }">
                  {{ formatNumber(row.processed_rows) }}
                </template>
              </el-table-column>
              <el-table-column prop="failed_rows" label="Failed" width="100">
                <template #default="{ row }">
                  <span :class="{ 'error-text': row.failed_rows > 0 }">
                    {{ formatNumber(row.failed_rows) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="Started" width="180">
                <template #default="{ row }">
                  {{ row.started_at ? formatDate(row.started_at) : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="Completed" width="180">
                <template #default="{ row }">
                  {{ row.completed_at ? formatDate(row.completed_at) : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="Error" min-width="200">
                <template #default="{ row }">
                  <div v-if="row.error_message" class="error-cell">
                    <el-tooltip :content="row.error_message" placement="top">
                      <el-tag type="danger" size="small">
                        {{ truncate(row.error_message, 50) }}
                      </el-tag>
                    </el-tooltip>
                  </div>
                  <span v-else style="color: #67c23a;">
                    <el-icon><SuccessFilled /></el-icon>
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="Actions" width="180" v-if="taskDetail?.task?.mode === 'full_load_then_cdc'">
                <template #default="{ row }">
                  <el-tooltip content="Re-run full load for this table" placement="top">
                    <el-button 
                      size="small" 
                      type="warning"
                      @click="forceFullLoad(row.table_name)"
                      :disabled="row.status === 'running'"
                    >
                      <el-icon><Refresh /></el-icon>
                      Force Full Load
                    </el-button>
                  </el-tooltip>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- CDC Tab -->
          <el-tab-pane label="CDC (Change Data Capture)" name="cdc">
            <el-empty 
              v-if="!taskDetail?.cdc_progress?.length" 
              description="No CDC data available. CDC will track changes after full load completes."
            />
            <el-table 
              v-else
              :data="taskDetail.cdc_progress" 
              stripe
              style="width: 100%"
            >
              <el-table-column prop="table_name" label="Table Name" width="250" fixed />
              <el-table-column label="Status" width="120">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" size="small">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="Changes Captured" width="200">
                <template #default="{ row }">
                  <div class="changes-info">
                    <el-icon><Edit /></el-icon>
                    <span>{{ formatNumber(row.processed_rows) }} changes</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="total_rows" label="Total Changes" width="150">
                <template #default="{ row }">
                  {{ formatNumber(row.total_rows) }}
                </template>
              </el-table-column>
              <el-table-column prop="processed_rows" label="Synced" width="120">
                <template #default="{ row }">
                  {{ formatNumber(row.processed_rows) }}
                </template>
              </el-table-column>
              <el-table-column prop="failed_rows" label="Failed" width="100">
                <template #default="{ row }">
                  <span :class="{ 'error-text': row.failed_rows > 0 }">
                    {{ formatNumber(row.failed_rows) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="Last Sync" width="180">
                <template #default="{ row }">
                  {{ row.completed_at ? formatDate(row.completed_at) : 'In Progress' }}
                </template>
              </el-table-column>
              <el-table-column label="Error" min-width="200">
                <template #default="{ row }">
                  <div v-if="row.error_message" class="error-cell">
                    <el-tooltip :content="row.error_message" placement="top">
                      <el-tag type="danger" size="small">
                        {{ truncate(row.error_message, 50) }}
                      </el-tag>
                    </el-tooltip>
                  </div>
                  <span v-else style="color: #67c23a;">
                    <el-icon><SuccessFilled /></el-icon>
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- Latest Execution Info -->
          <el-tab-pane label="Latest Execution" name="execution">
            <el-empty 
              v-if="!taskDetail?.latest_execution" 
              description="No execution data available"
            />
            <el-descriptions v-else :column="2" border>
              <el-descriptions-item label="Execution ID">
                {{ taskDetail.latest_execution.id }}
              </el-descriptions-item>
              <el-descriptions-item label="Type">
                <el-tag>{{ taskDetail.latest_execution.execution_type }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Status">
                <el-tag :type="getStatusType(taskDetail.latest_execution.status)">
                  {{ taskDetail.latest_execution.status }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Progress">
                <el-progress 
                  :percentage="taskDetail.latest_execution.progress_percent" 
                  :status="taskDetail.latest_execution.status === 'success' ? 'success' : null"
                />
              </el-descriptions-item>
              <el-descriptions-item label="Total Rows">
                {{ formatNumber(taskDetail.latest_execution.total_rows) }}
              </el-descriptions-item>
              <el-descriptions-item label="Processed Rows">
                {{ formatNumber(taskDetail.latest_execution.processed_rows) }}
              </el-descriptions-item>
              <el-descriptions-item label="Failed Rows">
                <span :class="{ 'error-text': taskDetail.latest_execution.failed_rows > 0 }">
                  {{ formatNumber(taskDetail.latest_execution.failed_rows) }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="Data Size">
                {{ taskDetail.latest_execution.data_size_mb.toFixed(2) }} MB
              </el-descriptions-item>
              <el-descriptions-item label="Throughput">
                {{ taskDetail.latest_execution.rows_per_second 
                  ? taskDetail.latest_execution.rows_per_second.toFixed(2) + ' rows/sec' 
                  : '-' 
                }}
              </el-descriptions-item>
              <el-descriptions-item label="Duration">
                {{ taskDetail.latest_execution.duration_seconds 
                  ? taskDetail.latest_execution.duration_seconds.toFixed(1) + 's' 
                  : '-' 
                }}
              </el-descriptions-item>
              <el-descriptions-item label="Started At">
                {{ taskDetail.latest_execution.started_at ? formatDate(taskDetail.latest_execution.started_at) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="Completed At">
                {{ taskDetail.latest_execution.completed_at ? formatDate(taskDetail.latest_execution.completed_at) : 'Running' }}
              </el-descriptions-item>
              <el-descriptions-item label="Error Message" :span="2" v-if="taskDetail.latest_execution.error_message">
                <el-alert 
                  :title="taskDetail.latest_execution.error_message" 
                  type="error" 
                  :closable="false"
                />
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, CloseBold, Refresh, Edit, SuccessFilled } from '@element-plus/icons-vue'
import { useWebSocketStore } from '@/stores/websocketStore'
import axios from 'axios'

const route = useRoute()
const taskId = ref(parseInt(route.params.id))
const taskDetail = ref(null)
const loading = ref(false)
const activeTab = ref('full_load')
const wsStore = useWebSocketStore()
const lastUpdate = ref('Never')  // Test reactivity
const updateCounter = ref(0)  // Force re-render counter

const fetchTaskDetail = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/tasks/${taskId.value}/detail`)
    taskDetail.value = response.data
  } catch (error) {
    ElMessage.error('Failed to load task details')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchTaskDetail()
  ElMessage.success('Data refreshed')
}

const controlTask = async (action) => {
  try {
    await axios.post(`/api/tasks/${taskId.value}/control`, { action })
    ElMessage.success(`Task ${action}ed successfully`)
    setTimeout(fetchTaskDetail, 1000)
  } catch (error) {
    ElMessage.error(`Failed to ${action} task`)
  }
}

const forceFullLoad = async (tableName) => {
  try {
    await ElMessageBox.confirm(
      `This will mark "${tableName}" for full load re-sync. The table will be reloaded in the next task execution. Continue?`,
      'Force Full Load',
      {
        confirmButtonText: 'Yes, Force Full Load',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    
    await axios.post(`/api/tasks/${taskId.value}/force-full-load`, [tableName])
    
    ElMessage({
      type: 'success',
      message: `Table "${tableName}" marked for full load. It will be reloaded when you start the task.`,
      duration: 5000
    })
    
    // Refresh task detail to show updated status
    setTimeout(fetchTaskDetail, 1000)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Failed to force full load')
    }
  }
}

const calculateProgress = (processed, total) => {
  if (!total || total === 0) return 0
  return Math.round((processed / total) * 100)
}

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const truncate = (str, length) => {
  if (!str) return ''
  return str.length > length ? str.substring(0, length) + '...' : str
}

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
    'success': 'success',
    'failed': 'danger',
    'stopped': 'info',
    'pending': 'info'
  }
  return types[status] || 'info'
}

// Handle real-time websocket updates
const handleWebSocketMessage = (event) => {
  const data = event.detail
  
  if (data.type === 'task_update' && taskDetail.value) {
    // Find update for current task
    const taskUpdate = data.tasks?.find(t => t.id === taskId.value)
    
    if (taskUpdate) {
      // Clone the entire taskDetail object to trigger reactivity
      const newTaskDetail = { ...taskDetail.value }
      
      // Update task status and progress
      if (newTaskDetail.task) {
        newTaskDetail.task = {
          ...newTaskDetail.task,
          status: taskUpdate.status,
          current_progress_percent: taskUpdate.progress
        }
      }
      
      // Update table-level progress if available
      if (taskUpdate.table_progress) {
        // Initialize full_load_progress if it doesn't exist
        if (!newTaskDetail.full_load_progress) {
          newTaskDetail.full_load_progress = []
        }
        
        if (newTaskDetail.full_load_progress) {
        // Create a map for quick lookup
        const progressMap = new Map(
          taskUpdate.table_progress.map(tp => [tp.table_name, tp])
        )
        
        // Track existing table names
        const existingTableNames = new Set(
          newTaskDetail.full_load_progress.map(t => t.table_name)
        )
        
        // Update existing table progress - create completely new array
        newTaskDetail.full_load_progress = newTaskDetail.full_load_progress.map(table => {
          const update = progressMap.get(table.table_name)
          if (update) {
            return {
              ...table,
              status: update.status,
              total_rows: update.total_rows,
              processed_rows: update.processed_rows,
              failed_rows: update.failed_rows,
              progress_percent: update.progress_percent,
              started_at: update.started_at,
              completed_at: update.completed_at
            }
          }
          return { ...table }
        })
        
        // Add any NEW tables that aren't in the existing list
        taskUpdate.table_progress.forEach(newTable => {
          if (!existingTableNames.has(newTable.table_name)) {
            newTaskDetail.full_load_progress.push({
              table_name: newTable.table_name,
              status: newTable.status,
              total_rows: newTable.total_rows,
              processed_rows: newTable.processed_rows,
              failed_rows: newTable.failed_rows,
              progress_percent: newTable.progress_percent,
              started_at: newTable.started_at,
              completed_at: newTable.completed_at
            })
          }
        })
        
        // Also update CDC progress if available
        if (newTaskDetail.cdc_progress) {
          const existingCdcTableNames = new Set(
            newTaskDetail.cdc_progress.map(t => t.table_name)
          )
          
          newTaskDetail.cdc_progress = newTaskDetail.cdc_progress.map(table => {
            const update = progressMap.get(table.table_name)
            if (update) {
              return {
                ...table,
                status: update.status,
                total_rows: update.total_rows,
                processed_rows: update.processed_rows,
                failed_rows: update.failed_rows,
                progress_percent: update.progress_percent,
                started_at: update.started_at,
                completed_at: update.completed_at
              }
            }
            return { ...table }
          })
          
          // Add any NEW CDC tables that aren't in the existing list
          taskUpdate.table_progress.forEach(newTable => {
            if (!existingCdcTableNames.has(newTable.table_name)) {
              newTaskDetail.cdc_progress.push({
                table_name: newTable.table_name,
                status: newTable.status,
                total_rows: newTable.total_rows,
                processed_rows: newTable.processed_rows,
                failed_rows: newTable.failed_rows,
                progress_percent: newTable.progress_percent,
                started_at: newTable.started_at,
                completed_at: newTable.completed_at
              })
            }
          })
        }
        }
      }
      
      // Reassign the entire object to trigger Vue reactivity
      taskDetail.value = newTaskDetail
      
      // Update timestamp
      lastUpdate.value = new Date().toLocaleTimeString()
      
      // Increment counter to force table re-render
      updateCounter.value++
    }
  }
}

onMounted(() => {
  fetchTaskDetail()
  
  // Connect to websocket if not connected
  if (!wsStore.connected) {
    wsStore.connect()
  }
  
  // Listen for websocket messages
  window.addEventListener('ws-message', handleWebSocketMessage)
})

onUnmounted(() => {
  // Clean up websocket listener
  window.removeEventListener('ws-message', handleWebSocketMessage)
})
</script>

<style scoped>
.task-detail {
  padding: 20px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.task-name {
  font-size: 20px;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.content {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-card,
.progress-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.progress-text {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

.error-text {
  color: #f56c6c;
  font-weight: bold;
}

.error-cell {
  max-width: 300px;
}

.changes-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #409eff;
}

:deep(.el-descriptions__label) {
  font-weight: bold;
}

:deep(.el-tab-pane) {
  min-height: 300px;
}
</style>

