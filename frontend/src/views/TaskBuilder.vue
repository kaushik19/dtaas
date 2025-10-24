<template>
  <div class="task-builder">
    <el-row :gutter="20">
      <!-- Left Panel - Configuration -->
      <el-col :span="8">
        <el-card class="config-panel">
          <template #header>
            <span>Task Configuration</span>
          </template>

          <el-form :model="taskConfig" label-width="140px" size="default">
            <el-form-item label="Task Name">
              <el-input v-model="taskConfig.name" placeholder="My Transfer Task" />
            </el-form-item>

            <el-form-item label="Description">
              <el-input 
                v-model="taskConfig.description" 
                type="textarea" 
                :rows="2"
                placeholder="Task description"
              />
            </el-form-item>

            <el-divider content-position="left">Connectors</el-divider>

            <el-form-item label="Source">
              <el-select 
                v-model="taskConfig.source_connector_id" 
                placeholder="Select source"
                @change="onSourceChange"
              >
                <el-option 
                  v-for="conn in sourceConnectors" 
                  :key="conn.id"
                  :label="conn.name" 
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="Tables">
              <el-button 
                @click="openTableSelection"
                :disabled="!taskConfig.source_connector_id"
                style="width: 100%;"
              >
                <el-icon><List /></el-icon>
                {{ taskConfig.source_tables.length > 0 
                  ? `${taskConfig.source_tables.length} table(s) selected` 
                  : 'Select Tables' }}
              </el-button>
            </el-form-item>

            <el-form-item label="Destination">
              <el-select 
                v-model="taskConfig.destination_connector_id" 
                placeholder="Select destination"
              >
                <el-option 
                  v-for="conn in destinationConnectors" 
                  :key="conn.id"
                  :label="`${conn.name} (${conn.destination_type})`" 
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>

            <el-divider content-position="left">Transfer Settings</el-divider>

            <el-form-item label="Mode">
              <el-select v-model="taskConfig.mode">
                <el-option label="Full Load" value="full_load" />
                <el-option label="CDC" value="cdc" />
                <el-option label="Full Load + CDC" value="full_load_then_cdc" />
              </el-select>
            </el-form-item>

            <el-form-item label="Schedule Type">
              <el-select v-model="taskConfig.schedule_type">
                <el-option label="On Demand" value="on_demand" />
                <el-option label="Continuous" value="continuous" />
                <el-option label="Interval" value="interval" />
              </el-select>
            </el-form-item>

            <el-form-item 
              v-if="taskConfig.schedule_type === 'interval'" 
              label="Interval (seconds)"
            >
              <el-input-number v-model="taskConfig.schedule_interval_seconds" :min="10" />
            </el-form-item>

            <el-divider content-position="left">Batch Configuration</el-divider>

            <el-form-item label="Batch Mode">
              <el-radio-group v-model="batchMode">
                <el-radio label="rows">By Row Count</el-radio>
                <el-radio label="size">By Data Size (MB)</el-radio>
              </el-radio-group>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                Smaller batches = more frequent progress updates but slightly slower
              </div>
            </el-form-item>

            <el-form-item 
              v-if="batchMode === 'rows'" 
              label="Rows per Batch"
            >
              <el-input-number 
                v-model="taskConfig.batch_rows" 
                :min="1000" 
                :max="10000000"
                :step="10000"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                Recommended: 50,000 - 100,000 for real-time progress updates
              </div>
            </el-form-item>

            <el-form-item 
              v-if="batchMode === 'size'" 
              label="Batch Size (MB)"
            >
              <el-input-number 
                v-model="taskConfig.batch_size_mb" 
                :min="1" 
                :max="1000"
                :step="10"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                Maximum data size in memory before writing to destination
              </div>
            </el-form-item>

            <el-form-item label="Parallel Tables">
              <el-input-number 
                v-model="taskConfig.parallel_tables" 
                :min="1" 
                :max="10"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                Number of tables to process simultaneously (1 = sequential)
              </div>
            </el-form-item>

            <el-form-item 
              v-if="destinationType === 's3'" 
              label="S3 File Format"
            >
              <el-select v-model="taskConfig.s3_file_format">
                <el-option label="Parquet" value="parquet" />
                <el-option label="CSV" value="csv" />
                <el-option label="JSON" value="json" />
              </el-select>
            </el-form-item>

            <el-form-item label="Schema Drift">
              <el-switch v-model="taskConfig.handle_schema_drift" />
            </el-form-item>

            <el-divider content-position="left">Retry Configuration</el-divider>

            <el-form-item label="Enable Retry">
              <el-switch v-model="taskConfig.retry_enabled" />
            </el-form-item>

            <el-form-item 
              v-if="taskConfig.retry_enabled" 
              label="Max Retries"
            >
              <el-input-number v-model="taskConfig.max_retries" :min="1" :max="10" />
            </el-form-item>

            <el-form-item 
              v-if="taskConfig.retry_enabled" 
              label="Retry Delay (sec)"
            >
              <el-input-number v-model="taskConfig.retry_delay_seconds" :min="5" :max="300" />
            </el-form-item>

            <el-form-item 
              v-if="taskConfig.retry_enabled" 
              label="Cleanup on Retry"
            >
              <el-switch v-model="taskConfig.cleanup_on_retry" />
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                Delete partial files before retrying failed table
              </div>
            </el-form-item>

            <el-divider />

            <el-button 
              type="primary" 
              style="width: 100%;"
              @click="createTask"
              :loading="creating"
            >
              {{ isEditMode ? 'Update Task' : 'Create Task' }}
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- Right Panel - Visual Builder -->
      <el-col :span="16">
        <el-card class="flow-panel">
          <template #header>
            <span>Visual Task Builder</span>
          </template>

          <div class="flow-container">
            <VueFlow
              v-model="elements"
              :default-zoom="1"
              :min-zoom="0.5"
              :max-zoom="2"
              class="vue-flow"
            >
              <Background />
              <Controls />
            </VueFlow>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Selected Tables List - Full Width -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card>
          <SelectedTablesList
            :tables="taskConfig.source_tables"
            :table-configs="taskConfig.table_configs || {}"
            @open-table-selection="openTableSelection"
            @configure-transform="openTransformDialog"
            @toggle-table="toggleTable"
            @remove-table="removeTable"
            @bulk-transform="openBulkTransformDialog"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- Per-Table Transform Dialog -->
    <TableTransformDialog
      v-model="transformDialogVisible"
      :table-name="currentTransformTable"
      :source-connector-id="taskConfig.source_connector_id"
      :transformations="getCurrentTableTransformations()"
      @save="saveTableTransformations"
    />

    <!-- Bulk Transform Dialog -->
    <BulkTransformDialog
      v-model="bulkTransformDialogVisible"
      @save="addBulkTransform"
    />

    <!-- Table Selection Dialog -->
    <TableSelectionDialog
      v-model="tableSelectionDialogVisible"
      :tables="sourceTables"
      :selectedTables="taskConfig.source_tables"
      @confirm="handleTableSelection"
    />
    
    <!-- Add Transformation Dialog (OLD - can be removed) -->
    <el-dialog 
      v-model="addTransformationDialogVisible" 
      title="Add Transformation" 
      width="600px"
    >
      <el-form :model="newTransform" label-width="120px">
        <el-form-item label="Type">
          <el-select v-model="newTransform.type" @change="onTransformTypeChange">
            <el-option label="Add Column" value="add_column" />
            <el-option label="Rename Column" value="rename_column" />
            <el-option label="Drop Column" value="drop_column" />
            <el-option label="Cast Type" value="cast_type" />
            <el-option label="Filter Rows" value="filter_rows" />
            <el-option label="Replace Value" value="replace_value" />
          </el-select>
        </el-form-item>

        <!-- Add Column Config -->
        <template v-if="newTransform.type === 'add_column'">
          <el-form-item label="Column Name">
            <el-input v-model="newTransform.config.column_name" />
          </el-form-item>
          <el-form-item label="Expression Type">
            <el-select v-model="newTransform.config.expression_type">
              <el-option label="Constant" value="constant" />
              <el-option label="Function" value="function" />
            </el-select>
          </el-form-item>
          <el-form-item label="Value">
            <el-input v-model="newTransform.config.value" />
          </el-form-item>
        </template>

        <!-- Rename Column Config -->
        <template v-if="newTransform.type === 'rename_column'">
          <el-form-item label="Old Name">
            <el-input v-model="newTransform.config.old_name" />
          </el-form-item>
          <el-form-item label="New Name">
            <el-input v-model="newTransform.config.new_name" />
          </el-form-item>
        </template>

        <!-- Drop Column Config -->
        <template v-if="newTransform.type === 'drop_column'">
          <el-form-item label="Column Name">
            <el-input v-model="newTransform.config.column_name" />
          </el-form-item>
        </template>

        <!-- Cast Type Config -->
        <template v-if="newTransform.type === 'cast_type'">
          <el-form-item label="Column Name">
            <el-input v-model="newTransform.config.column_name" />
          </el-form-item>
          <el-form-item label="Target Type">
            <el-select v-model="newTransform.config.target_type">
              <el-option label="int64" value="int64" />
              <el-option label="float64" value="float64" />
              <el-option label="string" value="object" />
              <el-option label="datetime" value="datetime64[ns]" />
            </el-select>
          </el-form-item>
        </template>

        <!-- Filter Rows Config -->
        <template v-if="newTransform.type === 'filter_rows'">
          <el-form-item label="Column Name">
            <el-input v-model="newTransform.config.column_name" />
          </el-form-item>
          <el-form-item label="Operator">
            <el-select v-model="newTransform.config.operator">
              <el-option label="=" value="==" />
              <el-option label="!=" value="!=" />
              <el-option label=">" value=">" />
              <el-option label="<" value="<" />
              <el-option label=">=" value=">=" />
              <el-option label="<=" value="<=" />
            </el-select>
          </el-form-item>
          <el-form-item label="Value">
            <el-input v-model="newTransform.config.value" />
          </el-form-item>
        </template>

        <!-- Replace Value Config -->
        <template v-if="newTransform.type === 'replace_value'">
          <el-form-item label="Column Name">
            <el-input v-model="newTransform.config.column_name" />
          </el-form-item>
          <el-form-item label="Old Value">
            <el-input v-model="newTransform.config.old_value" />
          </el-form-item>
          <el-form-item label="New Value">
            <el-input v-model="newTransform.config.new_value" />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="addTransformationDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="addTransformation">Add</el-button>
      </template>
    </el-dialog>

    <!-- Table Selection Dialog -->
    <TableSelectionDialog
      v-model="tableSelectionDialogVisible"
      :tables="sourceTables"
      :selectedTables="taskConfig.source_tables"
      @confirm="handleTableSelection"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConnectorStore } from '@/stores/connectorStore'
import { useTaskStore } from '@/stores/taskStore'
import { ElMessage } from 'element-plus'
import { List, SetUp } from '@element-plus/icons-vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import TableSelectionDialog from '@/components/TableSelectionDialog.vue'
import SelectedTablesList from '@/components/SelectedTablesList.vue'
import TableTransformDialog from '@/components/TableTransformDialog.vue'
import BulkTransformDialog from '@/components/BulkTransformDialog.vue'

const router = useRouter()
const route = router.currentRoute
const connectorStore = useConnectorStore()
const taskStore = useTaskStore()

const isEditMode = computed(() => !!route.value.params.id)
const taskId = computed(() => route.value.params.id)

const taskConfig = ref({
  name: '',
  description: '',
  source_connector_id: null,
  destination_connector_id: null,
  source_tables: [],
  table_mappings: {},
  table_configs: {},  // Per-table configuration
  mode: 'full_load',
  schedule_type: 'on_demand',
  schedule_interval_seconds: 60,
  batch_size_mb: 50,
  batch_rows: 50000,  // Default to 50k for good progress updates
  parallel_tables: 3,  // Default to 3 parallel tables
  s3_file_format: 'parquet',
  retry_enabled: true,
  max_retries: 3,
  retry_delay_seconds: 20,
  cleanup_on_retry: true,
  handle_schema_drift: true,
  transformations: []  // Global transformations (deprecated)
})

const batchMode = ref('rows')  // 'rows' or 'size'

const sourceTables = ref([])
const loadingTables = ref(false)
const creating = ref(false)
const addTransformationDialogVisible = ref(false)
const tableSelectionDialogVisible = ref(false)
const transformDialogVisible = ref(false)
const bulkTransformDialogVisible = ref(false)
const currentTransformTable = ref('')

const newTransform = ref({
  type: 'add_column',
  config: {}
})

const elements = ref([])

const sourceConnectors = computed(() => connectorStore.getSourceConnectors())
const destinationConnectors = computed(() => connectorStore.getDestinationConnectors())

const destinationType = computed(() => {
  if (!taskConfig.value.destination_connector_id) return null
  const dest = destinationConnectors.value.find(c => c.id === taskConfig.value.destination_connector_id)
  return dest?.destination_type
})

// Update visual flow based on configuration
watch([() => taskConfig.value.source_connector_id, () => taskConfig.value.destination_connector_id, () => taskConfig.value.source_tables], () => {
  updateFlowElements()
}, { deep: true })

const updateFlowElements = () => {
  const nodes = []
  const edges = []

  // Source node
  if (taskConfig.value.source_connector_id) {
    const sourceConn = sourceConnectors.value.find(c => c.id === taskConfig.value.source_connector_id)
    nodes.push({
      id: 'source',
      type: 'input',
      position: { x: 100, y: 150 },
      label: `Source: ${sourceConn?.name || 'N/A'}`,
      data: { label: `Source: ${sourceConn?.name || 'N/A'}` }
    })
  }

  // Table nodes
  const tableYStart = 100
  const tableYSpacing = 80
  taskConfig.value.source_tables.forEach((table, index) => {
    nodes.push({
      id: `table-${index}`,
      position: { x: 350, y: tableYStart + (index * tableYSpacing) },
      label: table,
      data: { label: table }
    })
    
    if (taskConfig.value.source_connector_id) {
      edges.push({
        id: `e-source-table-${index}`,
        source: 'source',
        target: `table-${index}`
      })
    }
  })

  // Transformation node
  if (taskConfig.value.transformations.length > 0) {
    nodes.push({
      id: 'transform',
      position: { x: 600, y: 200 },
      label: `Transforms (${taskConfig.value.transformations.length})`,
      data: { label: `Transforms (${taskConfig.value.transformations.length})` }
    })
    
    taskConfig.value.source_tables.forEach((table, index) => {
      edges.push({
        id: `e-table-transform-${index}`,
        source: `table-${index}`,
        target: 'transform'
      })
    })
  }

  // Destination node
  if (taskConfig.value.destination_connector_id) {
    const destConn = destinationConnectors.value.find(c => c.id === taskConfig.value.destination_connector_id)
    nodes.push({
      id: 'destination',
      type: 'output',
      position: { x: 850, y: 200 },
      label: `Dest: ${destConn?.name || 'N/A'}`,
      data: { label: `Dest: ${destConn?.name || 'N/A'}` }
    })

    // Connect to destination
    const sourceNodeId = taskConfig.value.transformations.length > 0 ? 'transform' : 
                         (taskConfig.value.source_tables.length > 0 ? 'table-0' : 'source')
    
    if (sourceNodeId) {
      edges.push({
        id: 'e-to-dest',
        source: sourceNodeId,
        target: 'destination'
      })
    }
  }

  elements.value = [...nodes, ...edges]
}

const onSourceChange = async () => {
  taskConfig.value.source_tables = []
  sourceTables.value = []
}

const loadSourceTables = async () => {
  if (!taskConfig.value.source_connector_id) return
  
  loadingTables.value = true
  try {
    sourceTables.value = await connectorStore.listTables(taskConfig.value.source_connector_id)
  } catch (error) {
    ElMessage.error('Failed to load tables')
  } finally {
    loadingTables.value = false
  }
}

const openTableSelection = async () => {
  await loadSourceTables()
  tableSelectionDialogVisible.value = true
}

const handleTableSelection = (selectedTableNames) => {
  taskConfig.value.source_tables = selectedTableNames
  
  // Initialize table_configs for new tables
  if (!taskConfig.value.table_configs) {
    taskConfig.value.table_configs = {}
  }
  
  // Add config for new tables
  selectedTableNames.forEach(tableName => {
    if (!taskConfig.value.table_configs[tableName]) {
      taskConfig.value.table_configs[tableName] = {
        enabled: true,
        transformations: []
      }
    }
  })
  
  // Remove config for unselected tables
  const tableSet = new Set(selectedTableNames)
  Object.keys(taskConfig.value.table_configs).forEach(tableName => {
    if (!tableSet.has(tableName)) {
      delete taskConfig.value.table_configs[tableName]
    }
  })
}

const openTransformDialog = (tableName) => {
  currentTransformTable.value = tableName
  transformDialogVisible.value = true
}

const getCurrentTableTransformations = () => {
  if (!taskConfig.value.table_configs) return []
  const tableConfig = taskConfig.value.table_configs[currentTransformTable.value]
  return tableConfig?.transformations || []
}

const saveTableTransformations = (tableName, transformations) => {
  if (!taskConfig.value.table_configs) {
    taskConfig.value.table_configs = {}
  }
  if (!taskConfig.value.table_configs[tableName]) {
    taskConfig.value.table_configs[tableName] = { enabled: true }
  }
  taskConfig.value.table_configs[tableName].transformations = transformations
  ElMessage.success(`Transformations saved for ${tableName}`)
}

const toggleTable = (tableName) => {
  if (!taskConfig.value.table_configs[tableName]) {
    taskConfig.value.table_configs[tableName] = { enabled: true, transformations: [] }
  }
  taskConfig.value.table_configs[tableName].enabled = !taskConfig.value.table_configs[tableName].enabled
}

const removeTable = (tableName) => {
  const index = taskConfig.value.source_tables.indexOf(tableName)
  if (index > -1) {
    taskConfig.value.source_tables.splice(index, 1)
  }
  if (taskConfig.value.table_configs[tableName]) {
    delete taskConfig.value.table_configs[tableName]
  }
}

const onTransformTypeChange = () => {
  newTransform.value.config = {}
}

const addTransformation = () => {
  taskConfig.value.transformations.push({
    type: newTransform.value.type,
    config: { ...newTransform.value.config }
  })
  addTransformationDialogVisible.value = false
  newTransform.value = {
    type: 'add_column',
    config: {}
  }
}

const removeTransformation = (index) => {
  taskConfig.value.transformations.splice(index, 1)
}

// Bulk transformations methods
const openBulkTransformDialog = () => {
  bulkTransformDialogVisible.value = true
}

const addBulkTransform = (transform) => {
  let addedCount = 0
  let skippedCount = 0
  
  // Apply the transformation to ALL selected tables
  taskConfig.value.source_tables.forEach(tableName => {
    // Initialize table config if it doesn't exist
    if (!taskConfig.value.table_configs) {
      taskConfig.value.table_configs = {}
    }
    if (!taskConfig.value.table_configs[tableName]) {
      taskConfig.value.table_configs[tableName] = {
        enabled: true,
        transformations: []
      }
    }
    if (!taskConfig.value.table_configs[tableName].transformations) {
      taskConfig.value.table_configs[tableName].transformations = []
    }
    
    // Check for duplicates based on transformation type
    const existingTransforms = taskConfig.value.table_configs[tableName].transformations
    let isDuplicate = false
    
    if (transform.type === 'add_column') {
      // For add_column, check if column_name already exists
      isDuplicate = existingTransforms.some(t => 
        t.type === 'add_column' && 
        t.config.column_name === transform.config.column_name
      )
    } else if (transform.type === 'rename_column') {
      // For rename_column, check if same column_name exists
      isDuplicate = existingTransforms.some(t => 
        t.type === 'rename_column' && 
        t.config.column_name === transform.config.column_name
      )
    } else if (transform.type === 'drop_column') {
      // For drop_column, check if same column_name exists
      isDuplicate = existingTransforms.some(t => 
        t.type === 'drop_column' && 
        t.config.column_name === transform.config.column_name
      )
    }
    
    // Add the transformation only if not duplicate
    if (!isDuplicate) {
      taskConfig.value.table_configs[tableName].transformations.push(transform)
      addedCount++
    } else {
      skippedCount++
    }
  })
  
  // Show appropriate success message
  if (addedCount > 0 && skippedCount === 0) {
    ElMessage.success(`Transformation added to ${addedCount} table(s)`)
  } else if (addedCount > 0 && skippedCount > 0) {
    ElMessage.success({
      message: `Transformation added to ${addedCount} table(s), skipped ${skippedCount} table(s) (already exists)`,
      duration: 5000
    })
  } else if (addedCount === 0) {
    ElMessage.warning('Transformation already exists in all selected tables')
  }
}

const createTask = async () => {
  if (!taskConfig.value.name) {
    ElMessage.error('Please enter a task name')
    return
  }
  if (!taskConfig.value.source_connector_id) {
    ElMessage.error('Please select a source connector')
    return
  }
  if (!taskConfig.value.destination_connector_id) {
    ElMessage.error('Please select a destination connector')
    return
  }
  if (taskConfig.value.source_tables.length === 0) {
    ElMessage.error('Please select at least one table')
    return
  }

  creating.value = true
  try {
    if (isEditMode.value) {
      await taskStore.updateTask(taskId.value, taskConfig.value)
      ElMessage.success('Task updated successfully')
    } else {
      await taskStore.createTask(taskConfig.value)
      ElMessage.success('Task created successfully')
    }
    router.push('/tasks')
  } catch (error) {
    const action = isEditMode.value ? 'update' : 'create'
    ElMessage.error(error.response?.data?.detail || `Failed to ${action} task`)
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await connectorStore.fetchConnectors()
  
  // Load existing task if in edit mode
  if (isEditMode.value) {
    try {
      const task = await taskStore.getTask(taskId.value)
      taskConfig.value = {
        name: task.name,
        description: task.description || '',
        source_connector_id: task.source_connector_id,
        destination_connector_id: task.destination_connector_id,
        source_tables: task.source_tables,
        table_mappings: task.table_mappings || {},
        table_configs: task.table_configs || {},
        mode: task.mode,
        schedule_type: task.schedule_type,
        schedule_interval_seconds: task.schedule_interval_seconds || 3600,
        batch_size_mb: task.batch_size_mb || 50,
        batch_rows: task.batch_rows || 10000,
        s3_file_format: task.s3_file_format || 'parquet',
        handle_schema_drift: task.handle_schema_drift,
        retry_enabled: task.retry_enabled !== undefined ? task.retry_enabled : true,
        max_retries: task.max_retries || 3,
        retry_delay_seconds: task.retry_delay_seconds || 20,
        cleanup_on_retry: task.cleanup_on_retry !== undefined ? task.cleanup_on_retry : true,
        transformations: task.transformations || []
      }
      
      // Load tables for the source connector BEFORE user opens dialog
      if (task.source_connector_id) {
        await loadSourceTables()
      }
    } catch (error) {
      ElMessage.error('Failed to load task')
      router.push('/tasks')
    }
  }
  
  updateFlowElements()
})
</script>

<style scoped>
.task-builder {
  width: 100%;
  height: calc(100vh - 120px);
}

.config-panel {
  height: calc(100vh - 120px);
  overflow-y: auto;
}

.flow-panel {
  height: calc(100vh - 120px);
}

.flow-container {
  height: calc(100vh - 200px);
  width: 100%;
}

.vue-flow {
  background-color: #fafafa;
}

.transformations-list {
  max-height: 300px;
  overflow-y: auto;
}

.transform-card {
  margin-bottom: 10px;
}

.transform-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.transform-config {
  font-size: 12px;
  background-color: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
}

.transform-config pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>

