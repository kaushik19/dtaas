<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h2>Dashboard</h2>
      <el-tooltip content="Refresh dashboard data" placement="bottom">
        <el-button 
          @click="refreshDashboard" 
          :icon="Refresh" 
          type="primary"
          circle
          :loading="dashboardStore.loading"
        />
      </el-tooltip>
    </div>
    
    <el-row :gutter="20" class="metrics-row">
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-icon" style="background-color: #409eff;">
            <el-icon size="24"><List /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ metrics.total_tasks }}</div>
            <div class="metric-label">Total Tasks</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-icon" style="background-color: #67c23a;">
            <el-icon size="24"><VideoPlay /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ metrics.running_tasks }}</div>
            <div class="metric-label">Running Tasks</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-icon" style="background-color: #e6a23c;">
            <el-icon size="24"><DataLine /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ formatNumber(metrics.total_rows_transferred) }}</div>
            <div class="metric-label">Rows Transferred</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-icon" style="background-color: #f56c6c;">
            <el-icon size="24"><Finished /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ formatSize(metrics.total_data_transferred_mb) }}</div>
            <div class="metric-label">Data Transferred</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>Execution Success Rate</span>
          </template>
          <div class="chart-container">
            <Pie :data="executionChartData" :options="chartOptions" />
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span>Performance Metrics</span>
          </template>
          <div class="performance-metrics">
            <el-statistic title="Avg Rows/Second" :value="metrics.avg_rows_per_second" :precision="2">
              <template #suffix>
                <el-icon><TopRight /></el-icon>
              </template>
            </el-statistic>
            <el-divider />
            <el-statistic 
              title="Success Rate" 
              :value="successRate" 
              suffix="%"
              :precision="1"
            />
            <el-divider />
            <el-statistic 
              title="Active Tasks" 
              :value="metrics.active_tasks"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>Recent Executions</span>
          </template>
          <el-table :data="metrics.recent_executions" style="width: 100%">
            <el-table-column prop="id" label="Execution ID" width="150">
              <template #default="{ row }">
                {{ row.id }}
                <el-tag 
                  v-if="isLatestExecution(row)" 
                  type="success" 
                  size="small"
                  style="margin-left: 8px;"
                >
                  Latest
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="task_id" label="Task ID" width="100">
              <template #default="{ row }">
                <el-link 
                  :href="`/tasks/${row.task_id}/detail`" 
                  type="primary"
                  @click.prevent="viewTaskDetail(row.task_id)"
                >
                  {{ row.task_id }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column prop="execution_type" label="Type" width="150">
              <template #default="{ row }">
                <el-tag :type="row.execution_type === 'full_load' ? 'primary' : 'success'" size="small">
                  {{ row.execution_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="Status" width="120">
              <template #default="{ row }">
                <el-tag 
                  :type="getStatusType(row.status)" 
                  size="small"
                >
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
                <el-progress :percentage="row.progress_percent" :status="row.status === 'success' ? 'success' : null" />
              </template>
            </el-table-column>
            <el-table-column prop="duration_seconds" label="Duration" width="120">
              <template #default="{ row }">
                {{ row.duration_seconds ? `${row.duration_seconds.toFixed(1)}s` : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="Started At" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="Actions" width="180" fixed="right">
              <template #default="{ row }">
                <el-button 
                  v-if="isLatestExecution(row)"
                  type="primary" 
                  size="small"
                  @click="viewTaskDetail(row.task_id)"
                >
                  <el-icon><View /></el-icon>
                  View Detail
                </el-button>
                <el-tooltip 
                  v-else
                  content="Only the latest execution can be viewed in detail"
                  placement="top"
                >
                  <el-tag size="small" type="info">Historical</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboardStore'
import { Pie } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { List, VideoPlay, DataLine, Finished, View, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()

ChartJS.register(ArcElement, Tooltip, Legend)

const dashboardStore = useDashboardStore()
const metrics = computed(() => dashboardStore.metrics)

// Determine which executions are the latest for each task
const latestExecutionIds = computed(() => {
  if (!metrics.value.recent_executions) return new Set()
  
  const taskLatestMap = {}
  metrics.value.recent_executions.forEach(exec => {
    if (!taskLatestMap[exec.task_id] || exec.id > taskLatestMap[exec.task_id]) {
      taskLatestMap[exec.task_id] = exec.id
    }
  })
  
  return new Set(Object.values(taskLatestMap))
})

const isLatestExecution = (execution) => {
  return latestExecutionIds.value.has(execution.id)
}

const executionChartData = computed(() => ({
  labels: ['Successful', 'Failed'],
  datasets: [{
    data: [
      metrics.value.successful_executions,
      metrics.value.failed_executions
    ],
    backgroundColor: ['#67c23a', '#f56c6c']
  }]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false
}

const successRate = computed(() => {
  const total = metrics.value.successful_executions + metrics.value.failed_executions
  return total > 0 ? (metrics.value.successful_executions / total) * 100 : 0
})

const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num
}

const formatSize = (mb) => {
  if (mb >= 1024) {
    return (mb / 1024).toFixed(2) + ' GB'
  }
  return mb.toFixed(2) + ' MB'
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const getStatusType = (status) => {
  const types = {
    'success': 'success',
    'running': 'primary',
    'pending': 'info',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const viewTaskDetail = (taskId) => {
  router.push(`/tasks/${taskId}/detail`)
}

const refreshDashboard = async () => {
  try {
    await dashboardStore.fetchMetrics()
    ElMessage.success('Dashboard refreshed')
  } catch (error) {
    ElMessage.error('Failed to refresh dashboard')
    console.error('Failed to refresh dashboard metrics:', error)
  }
}

onMounted(async () => {
  try {
    await dashboardStore.fetchMetrics()
  } catch (error) {
    console.error('Failed to load dashboard metrics:', error)
  }
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 10px 0;
}

.dashboard-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.metrics-row {
  margin-bottom: 20px;
}

.charts-row {
  margin-bottom: 20px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 10px;
}

.metric-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 16px;
}

.metric-content {
  flex: 1;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.metric-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.chart-container {
  height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.performance-metrics {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>

