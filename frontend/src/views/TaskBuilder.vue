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
              <el-select 
                v-model="taskConfig.source_tables" 
                multiple 
                placeholder="Select tables"
                :disabled="!taskConfig.source_connector_id"
                @visible-change="loadSourceTables"
              >
                <el-option 
                  v-for="table in sourceTables" 
                  :key="`${table.schema_name}.${table.table_name}`"
                  :label="`${table.schema_name}.${table.table_name}`" 
                  :value="`${table.schema_name}.${table.table_name}`"
                >
                  <span>{{ table.schema_name }}.{{ table.table_name }}</span>
                  <el-tag v-if="table.cdc_enabled" type="success" size="small" style="margin-left: 8px;">
                    CDC
                  </el-tag>
                </el-option>
              </el-select>
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

            <el-form-item label="Batch Size (MB)">
              <el-input-number v-model="taskConfig.batch_size_mb" :min="1" :max="500" />
            </el-form-item>

            <el-form-item label="Batch Rows">
              <el-input-number v-model="taskConfig.batch_rows" :min="100" :max="100000" />
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

            <el-divider content-position="left">Transformations</el-divider>

            <div class="transformations-list">
              <el-card 
                v-for="(transform, index) in taskConfig.transformations" 
                :key="index"
                class="transform-card"
                shadow="hover"
              >
                <div class="transform-header">
                  <el-tag size="small">{{ transform.type }}</el-tag>
                  <el-button 
                    size="small" 
                    type="danger" 
                    link
                    @click="removeTransformation(index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <div class="transform-config">
                  <pre>{{ JSON.stringify(transform.config, null, 2) }}</pre>
                </div>
              </el-card>
            </div>

            <el-button 
              type="primary" 
              plain 
              style="width: 100%; margin-top: 10px;"
              @click="addTransformationDialogVisible = true"
            >
              <el-icon><Plus /></el-icon>
              Add Transformation
            </el-button>

            <el-divider />

            <el-button 
              type="primary" 
              style="width: 100%;"
              @click="createTask"
              :loading="creating"
            >
              Create Task
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

    <!-- Add Transformation Dialog -->
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { VueFlow } from '@vueflow/core'
import { Background } from '@vueflow/background'
import { Controls } from '@vueflow/controls'
import { useConnectorStore } from '@/stores/connectorStore'
import { useTaskStore } from '@/stores/taskStore'
import { ElMessage } from 'element-plus'
import '@vueflow/core/dist/style.css'
import '@vueflow/core/dist/theme-default.css'
import '@vueflow/background/dist/style.css'
import '@vueflow/controls/dist/style.css'

const router = useRouter()
const connectorStore = useConnectorStore()
const taskStore = useTaskStore()

const taskConfig = ref({
  name: '',
  description: '',
  source_connector_id: null,
  destination_connector_id: null,
  source_tables: [],
  table_mappings: {},
  mode: 'full_load',
  schedule_type: 'on_demand',
  schedule_interval_seconds: 60,
  batch_size_mb: 50,
  batch_rows: 10000,
  s3_file_format: 'parquet',
  handle_schema_drift: true,
  transformations: []
})

const sourceTables = ref([])
const loadingTables = ref(false)
const creating = ref(false)
const addTransformationDialogVisible = ref(false)

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

const loadSourceTables = async (visible) => {
  if (!visible || !taskConfig.value.source_connector_id || sourceTables.value.length > 0) return
  
  loadingTables.value = true
  try {
    sourceTables.value = await connectorStore.listTables(taskConfig.value.source_connector_id)
  } catch (error) {
    ElMessage.error('Failed to load tables')
  } finally {
    loadingTables.value = false
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
    await taskStore.createTask(taskConfig.value)
    ElMessage.success('Task created successfully')
    router.push('/tasks')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to create task')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await connectorStore.fetchConnectors()
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

