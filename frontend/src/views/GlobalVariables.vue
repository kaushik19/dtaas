<template>
  <div class="global-variables">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Global Variables</span>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            Create Variable
          </el-button>
        </div>
      </template>

      <el-alert 
        type="info" 
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <template #title>
          Define reusable variables that can be used in S3 path templates. Variables can be static values, database queries, or expressions.
        </template>
      </el-alert>

      <el-table :data="variables" v-loading="loading">
        <el-table-column prop="name" label="Name" width="200">
          <template #default="{ row }">
            <code>${{ row.name }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="Description" />
        <el-table-column prop="variable_type" label="Type" width="150">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.variable_type)">
              {{ formatType(row.variable_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Configuration" width="300">
          <template #default="{ row }">
            <div style="font-size: 12px;">
              <template v-if="row.variable_type === 'static'">
                Value: <code>{{ row.config.value }}</code>
              </template>
              <template v-else-if="row.variable_type === 'db_query'">
                Query: <code>SELECT {{ row.config.column }} FROM {{ row.config.schema }}.{{ row.config.table }}</code>
              </template>
              <template v-else-if="row.variable_type === 'expression'">
                Expression: <code>{{ row.config.expression }}</code>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Status" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? 'Active' : 'Inactive' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              type="primary"
              @click="openEditDialog(row)"
            >
              Edit
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteVariable(row.id)"
            >
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEditMode ? 'Edit Variable' : 'Create Variable'" 
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="variableForm" label-width="140px">
        <el-form-item label="Variable Name">
          <el-input 
            v-model="variableForm.name" 
            placeholder="e.g., customerId"
            :disabled="isEditMode"
          />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            Use this as ${{ variableForm.name || 'variableName' }} in path templates
          </div>
        </el-form-item>

        <el-form-item label="Description">
          <el-input 
            v-model="variableForm.description" 
            type="textarea"
            placeholder="Describe what this variable represents"
          />
        </el-form-item>

        <el-form-item label="Type">
          <el-select v-model="variableForm.variable_type" @change="handleTypeChange">
            <el-option label="Static Value" value="static" />
            <el-option label="Database Query" value="db_query" />
            <el-option label="Expression" value="expression" />
          </el-select>
        </el-form-item>

        <!-- Static Configuration -->
        <template v-if="variableForm.variable_type === 'static'">
          <el-form-item label="Value">
            <el-input v-model="variableForm.config.value" placeholder="Enter static value" />
          </el-form-item>
        </template>

        <!-- DB Query Configuration -->
        <template v-if="variableForm.variable_type === 'db_query'">
          <el-card style="background-color: #f5f7fa;">
            <template #header>
              <div style="font-size: 14px; font-weight: 600;">
                Database Query Configuration
              </div>
            </template>

            <el-alert 
              type="info" 
              :closable="false"
              style="margin-bottom: 16px;"
            >
              <strong>Query Database Configuration</strong><br/>
              Connect to the database where this variable's value will be queried from (e.g., Tenants database for customer lookup)
            </el-alert>

            <el-form-item label="Query Server">
              <el-input v-model="dbConnection.server" placeholder="localhost or server.database.windows.net" />
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                Database server hostname or IP address
              </div>
            </el-form-item>

            <el-form-item label="Query Port">
              <el-input-number v-model="dbConnection.port" :min="1" :max="65535" />
            </el-form-item>

            <el-form-item label="Query Username">
              <el-input v-model="dbConnection.username" placeholder="sa or username" />
            </el-form-item>

            <el-form-item label="Query Password">
              <el-input v-model="dbConnection.password" type="password" placeholder="password" show-password />
            </el-form-item>

            <el-button 
              type="primary" 
              @click="connectAndLoadDatabases"
              :loading="loadingDatabases"
              :disabled="!dbConnection.server || !dbConnection.username || !dbConnection.password"
              style="width: 100%; margin-bottom: 16px;"
            >
              <el-icon><Connection /></el-icon>
              Connect & Load Databases
            </el-button>

            <template v-if="databases.length > 0">
              <el-form-item label="Query Database">
                <el-select 
                  v-model="selectedDatabase" 
                  placeholder="Select database to query"
                  @change="loadTables"
                  filterable
                  style="width: 100%;"
                >
                  <el-option 
                    v-for="db in databases" 
                    :key="db" 
                    :label="db" 
                    :value="db"
                  />
                </el-select>
                <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                  💡 This is the database where the variable value will be queried from
                </div>
              </el-form-item>
            </template>

            <template v-if="selectedDatabase">
              <el-form-item label="Table">
                <el-select 
                  v-model="selectedTable" 
                  placeholder="Select table"
                  @change="onTableSelect"
                  filterable
                  :loading="loadingTables"
                  style="width: 100%;"
                >
                  <el-option 
                    v-for="table in tables" 
                    :key="`${table.schema}.${table.table}`" 
                    :label="`${table.schema}.${table.table} (${table.row_count} rows)`" 
                    :value="`${table.schema}.${table.table}`"
                  />
                </el-select>
                <div v-if="loadingTables" style="font-size: 12px; color: #909399; margin-top: 4px;">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  Loading tables from {{ selectedDatabase }}...
                </div>
                <div v-else-if="!loadingTables && tables.length === 0" style="font-size: 12px; color: #e6a23c; margin-top: 4px;">
                  ⚠️ No tables found in {{ selectedDatabase }}
                </div>
                <div v-else-if="!loadingTables && tables.length > 0" style="font-size: 12px; color: #67c23a; margin-top: 4px;">
                  ✓ Found {{ tables.length }} tables
                </div>
              </el-form-item>
            </template>

            <template v-if="selectedTable">
              <el-form-item label="Column to SELECT">
                <el-select 
                  v-model="variableForm.config.column" 
                  placeholder="Select column to retrieve"
                  filterable
                  :loading="loadingColumns"
                  style="width: 100%;"
                >
                  <el-option 
                    v-for="col in columns" 
                    :key="col" 
                    :label="col" 
                    :value="col"
                  />
                </el-select>
                <div v-if="loadingColumns" style="font-size: 12px; color: #909399; margin-top: 4px;">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  Loading columns from {{ selectedTable }}...
                </div>
                <div v-else-if="!loadingColumns && columns.length === 0" style="font-size: 12px; color: #e6a23c; margin-top: 4px;">
                  ⚠️ No columns found
                </div>
                <div v-else-if="!loadingColumns && columns.length > 0" style="font-size: 12px; color: #67c23a; margin-top: 4px;">
                  ✓ Found {{ columns.length }} columns
                </div>
              </el-form-item>

              <!-- WHERE Conditions Section - Only show after columns are loaded -->
              <el-divider content-position="left">
                <el-icon><Filter /></el-icon>
                WHERE Conditions (Optional)
              </el-divider>

              <el-alert 
                type="info" 
                :closable="false"
                style="margin-bottom: 16px;"
              >
                Add conditions to filter which row's value to retrieve from {{ variableForm.config.schema }}.{{ variableForm.config.table }}
              </el-alert>

              <div 
                v-for="(condition, index) in variableForm.config.where_conditions" 
                :key="index" 
                class="condition-row"
              >
                <el-card class="condition-card" shadow="hover">
                  <div class="condition-content">
                    <div class="condition-field-group">
                      <label class="condition-label">Field</label>
                      <el-select 
                        v-model="condition.field" 
                        placeholder="Select column"
                        filterable
                        allow-create
                        default-first-option
                        class="condition-select"
                      >
                        <el-option-group label="Available Columns from {{ variableForm.config.schema }}.{{ variableForm.config.table }}">
                          <el-option 
                            v-for="col in columns" 
                            :key="col" 
                            :label="col" 
                            :value="col"
                          >
                            <span style="float: left">{{ col }}</span>
                            <span style="float: right; color: #8492a6; font-size: 13px">Column</span>
                          </el-option>
                        </el-option-group>
                      </el-select>
                    </div>

                    <div class="condition-operator-group">
                      <label class="condition-label">Operator</label>
                      <el-select v-model="condition.operator" class="operator-select">
                        <el-option label="=" value="=" />
                        <el-option label="!=" value="!=" />
                        <el-option label=">" value=">" />
                        <el-option label="<" value="<" />
                        <el-option label=">=" value=">=" />
                        <el-option label="<=" value="<=" />
                        <el-option label="LIKE" value="LIKE" />
                        <el-option label="IN" value="IN" />
                        <el-option label="IS NULL" value="IS NULL" />
                        <el-option label="IS NOT NULL" value="IS NOT NULL" />
                      </el-select>
                    </div>

                    <div class="condition-value-group" v-if="!['IS NULL', 'IS NOT NULL'].includes(condition.operator)">
                      <label class="condition-label">Value</label>
                      <el-input 
                        v-model="condition.value" 
                        placeholder="Enter value or use $variableName"
                        class="condition-input"
                      >
                        <template #prepend>
                          <el-icon><Edit /></el-icon>
                        </template>
                      </el-input>
                      <div class="condition-hint">
                        💡 Use <code>$variableName</code> to reference other variables
                      </div>
                    </div>

                    <el-button 
                      type="danger" 
                      size="default"
                      circle
                      @click="removeCondition(index)"
                      class="condition-remove-btn"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>

                  <div v-if="index < variableForm.config.where_conditions.length - 1" class="condition-and">
                    <el-tag type="info" size="small">AND</el-tag>
                  </div>
                </el-card>
              </div>

              <el-button 
                type="primary" 
                size="default"
                @click="addCondition"
                class="add-condition-btn"
              >
                <el-icon><Plus /></el-icon>
                Add WHERE Condition
              </el-button>

              <!-- Query Preview -->
              <template v-if="variableForm.config.table && variableForm.config.column">
                <el-divider content-position="left">
                  <el-icon><View /></el-icon>
                  Query Preview
                </el-divider>
                <el-card class="query-preview">
                  <code class="sql-preview">
                    SELECT {{ variableForm.config.column }}<br/>
                    FROM {{ variableForm.config.schema }}.{{ variableForm.config.table }}
                    <template v-if="variableForm.config.where_conditions.length > 0">
                      <br/>WHERE 
                      <template v-for="(cond, idx) in variableForm.config.where_conditions" :key="idx">
                        <span v-if="idx > 0"> AND </span>
                        {{ cond.field }} {{ cond.operator }}
                        <span v-if="!['IS NULL', 'IS NOT NULL'].includes(cond.operator)"> '{{ cond.value }}'</span>
                      </template>
                    </template>
                  </code>
                </el-card>
              </template>
            </template>
          </el-card>
        </template>

        <!-- Expression Configuration -->
        <template v-if="variableForm.variable_type === 'expression'">
          <el-form-item label="Expression">
            <el-input 
              v-model="variableForm.config.expression" 
              type="textarea"
              placeholder="e.g., $databaseName-$timestamp or $customerId/folder"
            />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              You can reference other variables using $variableName syntax
            </div>
          </el-form-item>
        </template>

        <el-form-item label="Active">
          <el-switch v-model="variableForm.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="saveVariable" :loading="loading">
          {{ isEditMode ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Filter, Delete, Edit, View, Loading } from '@element-plus/icons-vue'
import api from '@/api'

const variables = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEditMode = ref(false)

// Database browser state
const dbConnection = ref({
  server: '',
  port: 1433,
  username: '',
  password: ''
})
const databases = ref([])
const tables = ref([])
const columns = ref([])
const selectedDatabase = ref('')
const selectedTable = ref('')
const loadingDatabases = ref(false)
const loadingTables = ref(false)
const loadingColumns = ref(false)

const variableForm = ref({
  name: '',
  description: '',
  variable_type: 'static',
  config: {
    value: '',
    schema: 'dbo',
    table: '',
    column: '',
    where_conditions: [],
    expression: ''
  },
  is_active: true
})

onMounted(() => {
  fetchVariables()
})

const fetchVariables = async () => {
  loading.value = true
  try {
    const response = await api.get('/variables/')
    variables.value = response.data
  } catch (error) {
    ElMessage.error('Failed to fetch variables')
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  isEditMode.value = false
  resetForm()
  dialogVisible.value = true
}

const resetForm = () => {
  variableForm.value = {
    name: '',
    description: '',
    variable_type: 'static',
    config: {
      value: '',
      schema: 'dbo',
      table: '',
      column: '',
      where_conditions: [],
      expression: ''
    },
    is_active: true
  }
  
  // Reset database browser state
  dbConnection.value = {
    server: '',
    port: 1433,
    username: '',
    password: ''
  }
  databases.value = []
  tables.value = []
  columns.value = []
  selectedDatabase.value = ''
  selectedTable.value = ''
}

const openEditDialog = async (variable) => {
  isEditMode.value = true
  
  // Deep clone the config to avoid reference issues
  const configCopy = JSON.parse(JSON.stringify(variable.config))
  
  variableForm.value = {
    id: variable.id,
    name: variable.name,
    description: variable.description || '',
    variable_type: variable.variable_type,
    config: configCopy,
    is_active: variable.is_active
  }
  
  // For db_query type, populate database connection details and load data
  if (variableForm.value.variable_type === 'db_query') {
    // Ensure config has proper structure
    if (!variableForm.value.config.where_conditions) {
      variableForm.value.config.where_conditions = []
    }
    if (!variableForm.value.config.schema) {
      variableForm.value.config.schema = 'dbo'
    }
    
    // Populate database connection from saved config
    if (variableForm.value.config.server) {
      dbConnection.value = {
        server: variableForm.value.config.server || '',
        port: variableForm.value.config.port || 1433,
        username: variableForm.value.config.username || '',
        password: variableForm.value.config.password || ''
      }
      
      // Set selected database
      if (variableForm.value.config.database) {
        selectedDatabase.value = variableForm.value.config.database
        databases.value = [variableForm.value.config.database]
        
        // If we have table and schema, set them
        if (variableForm.value.config.table && variableForm.value.config.schema) {
          selectedTable.value = `${variableForm.value.config.schema}.${variableForm.value.config.table}`
          
          // Try to load tables and columns
          try {
            await loadTablesForEdit()
            await loadColumnsForEdit()
          } catch (error) {
            console.error('Failed to load tables/columns for editing:', error)
          }
        }
      }
    }
  }
  
  dialogVisible.value = true
}

const handleTypeChange = () => {
  // Reset config based on type
  if (variableForm.value.variable_type === 'static') {
    variableForm.value.config = { value: '' }
  } else if (variableForm.value.variable_type === 'db_query') {
    variableForm.value.config = {
      schema: 'dbo',
      table: '',
      column: '',
      where_conditions: []
    }
  } else if (variableForm.value.variable_type === 'expression') {
    variableForm.value.config = { expression: '' }
  }
}

const addCondition = () => {
  variableForm.value.config.where_conditions.push({
    field: '',
    operator: '=',
    value: ''
  })
}

const removeCondition = (index) => {
  variableForm.value.config.where_conditions.splice(index, 1)
}

const saveVariable = async () => {
  loading.value = true
  try {
    // If it's a DB query variable and we have database connection details, save them
    if (variableForm.value.variable_type === 'db_query' && selectedDatabase.value) {
      // Save connection details in config for cross-database queries
      variableForm.value.config.server = dbConnection.value.server
      variableForm.value.config.port = dbConnection.value.port
      variableForm.value.config.username = dbConnection.value.username
      variableForm.value.config.password = dbConnection.value.password
      variableForm.value.config.database = selectedDatabase.value
    }
    
    if (isEditMode.value) {
      await api.put(`/variables/${variableForm.value.id}`, variableForm.value)
      ElMessage.success('Variable updated successfully')
    } else {
      await api.post('/variables/', variableForm.value)
      ElMessage.success('Variable created successfully')
    }
    dialogVisible.value = false
    await fetchVariables()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to save variable')
  } finally {
    loading.value = false
  }
}

const deleteVariable = async (id) => {
  try {
    await ElMessageBox.confirm(
      'This will permanently delete the variable. Continue?',
      'Warning',
      {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    await api.delete(`/variables/${id}`)
    ElMessage.success('Variable deleted successfully')
    await fetchVariables()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete variable')
    }
  }
}

const getTypeColor = (type) => {
  switch (type) {
    case 'static':
      return 'info'
    case 'db_query':
      return 'primary'
    case 'expression':
      return 'warning'
    default:
      return ''
  }
}

const formatType = (type) => {
  switch (type) {
    case 'static':
      return 'Static'
    case 'db_query':
      return 'DB Query'
    case 'expression':
      return 'Expression'
    default:
      return type
  }
}

// Database browser methods
const connectAndLoadDatabases = async () => {
  loadingDatabases.value = true
  databases.value = []
  tables.value = []
  columns.value = []
  selectedDatabase.value = ''
  selectedTable.value = ''
  
  try {
    const response = await api.post('/database-browser/databases', dbConnection.value)
    databases.value = response.data.databases
    ElMessage.success(`Connected! Found ${databases.value.length} databases`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to connect to database')
  } finally {
    loadingDatabases.value = false
  }
}

const loadTables = async () => {
  if (!selectedDatabase.value) return
  
  loadingTables.value = true
  tables.value = []
  columns.value = []
  selectedTable.value = ''
  
  try {
    const response = await api.post(
      `/database-browser/tables?database=${encodeURIComponent(selectedDatabase.value)}`,
      dbConnection.value
    )
    tables.value = response.data.tables
    ElMessage.success(`Found ${tables.value.length} tables`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to load tables')
  } finally {
    loadingTables.value = false
  }
}

const onTableSelect = async () => {
  if (!selectedTable.value) return
  
  const [schema, table] = selectedTable.value.split('.')
  
  // Update form config
  variableForm.value.config.schema = schema
  variableForm.value.config.table = table
  
  // Load columns
  loadingColumns.value = true
  columns.value = []
  
  try {
    const response = await api.post(
      `/database-browser/columns?database=${encodeURIComponent(selectedDatabase.value)}&schema=${encodeURIComponent(schema)}&table=${encodeURIComponent(table)}`,
      dbConnection.value
    )
    columns.value = response.data.columns
    ElMessage.success(`Found ${columns.value.length} columns`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to load columns')
  } finally {
    loadingColumns.value = false
  }
}

// Helper methods for loading data when editing
const loadTablesForEdit = async () => {
  if (!selectedDatabase.value) return
  
  loadingTables.value = true
  tables.value = []
  
  try {
    const response = await api.post(
      `/database-browser/tables?database=${encodeURIComponent(selectedDatabase.value)}`,
      dbConnection.value
    )
    tables.value = response.data.tables
  } catch (error) {
    console.error('Failed to load tables:', error)
  } finally {
    loadingTables.value = false
  }
}

const loadColumnsForEdit = async () => {
  if (!selectedTable.value) return
  
  const [schema, table] = selectedTable.value.split('.')
  loadingColumns.value = true
  columns.value = []
  
  try {
    const response = await api.post(
      `/database-browser/columns?database=${encodeURIComponent(selectedDatabase.value)}&schema=${encodeURIComponent(schema)}&table=${encodeURIComponent(table)}`,
      dbConnection.value
    )
    columns.value = response.data.columns
  } catch (error) {
    console.error('Failed to load columns:', error)
  } finally {
    loadingColumns.value = false
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.condition-row {
  margin-bottom: 16px;
}

.condition-card {
  border: 2px solid #e4e7ed;
  transition: all 0.3s;
}

.condition-card:hover {
  border-color: #409eff;
}

.condition-content {
  display: grid;
  grid-template-columns: 2fr 1.2fr 2fr auto;
  gap: 16px;
  align-items: start;
}

.condition-field-group,
.condition-operator-group,
.condition-value-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.condition-select,
.operator-select,
.condition-input {
  width: 100%;
}

.condition-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.condition-remove-btn {
  margin-top: 28px;
}

.condition-and {
  text-align: center;
  margin-top: 8px;
}

.add-condition-btn {
  width: 100%;
  height: 48px;
  font-size: 15px;
  border-style: dashed;
}

.query-preview {
  background-color: #f5f7fa;
  border-left: 4px solid #409eff;
}

.sql-preview {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  display: block;
  white-space: pre-wrap;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .condition-content {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .condition-remove-btn {
    margin-top: 0;
    align-self: flex-end;
  }
}
</style>

