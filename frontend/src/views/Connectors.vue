<template>
  <div class="connectors">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Connectors</span>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            Create Connector
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="All" name="all"></el-tab-pane>
        <el-tab-pane label="Source" name="source"></el-tab-pane>
        <el-tab-pane label="Destination" name="destination"></el-tab-pane>
      </el-tabs>

      <el-table :data="filteredConnectors" v-loading="connectorStore.loading">
        <el-table-column prop="name" label="Name" width="200" />
        <el-table-column prop="connector_type" label="Type" width="120">
          <template #default="{ row }">
            <el-tag :type="row.connector_type === 'source' ? 'primary' : 'success'">
              {{ row.connector_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Database/Service" width="150">
          <template #default="{ row }">
            <el-tag size="small">
              {{ row.source_type || row.destination_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="Description" />
        <el-table-column label="Status" width="120">
          <template #default="{ row }">
            <el-tag 
              v-if="row.test_status"
              :type="row.test_status === 'success' ? 'success' : 'danger'"
              size="small"
            >
              {{ row.test_status }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="250" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              @click="testConnection(row.id)"
              :loading="testingId === row.id"
            >
              Test
            </el-button>
            <el-button 
              v-if="row.connector_type === 'source'"
              size="small" 
              @click="viewTables(row)"
            >
              Tables
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteConnector(row.id)"
            >
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create Connector Dialog -->
    <el-dialog 
      v-model="createDialogVisible" 
      title="Create Connector" 
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="connectorForm" label-width="150px">
        <el-form-item label="Name">
          <el-input v-model="connectorForm.name" placeholder="My Connector" />
        </el-form-item>

        <el-form-item label="Description">
          <el-input 
            v-model="connectorForm.description" 
            type="textarea" 
            placeholder="Description"
          />
        </el-form-item>

        <el-form-item label="Type">
          <el-select v-model="connectorForm.connector_type" @change="handleTypeChange">
            <el-option label="Source" value="source" />
            <el-option label="Destination" value="destination" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="connectorForm.connector_type === 'source'" label="Source Type">
          <el-select v-model="connectorForm.source_type">
            <el-option label="SQL Server" value="sql_server" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="connectorForm.connector_type === 'destination'" label="Destination Type">
          <el-select v-model="connectorForm.destination_type" @change="handleDestinationTypeChange">
            <el-option label="Snowflake" value="snowflake" />
            <el-option label="S3" value="s3" />
          </el-select>
        </el-form-item>

        <!-- SQL Server Config -->
        <template v-if="connectorForm.source_type === 'sql_server'">
          <el-divider content-position="left">SQL Server Configuration</el-divider>
          <el-form-item label="Server">
            <el-input v-model="connectorForm.connection_config.server" placeholder="localhost" />
          </el-form-item>
          <el-form-item label="Database">
            <el-input v-model="connectorForm.connection_config.database" placeholder="mydb" />
          </el-form-item>
          <el-form-item label="Username">
            <el-input v-model="connectorForm.connection_config.username" placeholder="sa" />
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="connectorForm.connection_config.password" type="password" />
          </el-form-item>
          <el-form-item label="Port">
            <el-input-number v-model="connectorForm.connection_config.port" :min="1" :max="65535" />
          </el-form-item>
        </template>

        <!-- Snowflake Config -->
        <template v-if="connectorForm.destination_type === 'snowflake'">
          <el-divider content-position="left">Snowflake Configuration</el-divider>
          <el-form-item label="Account">
            <el-input v-model="connectorForm.connection_config.account" placeholder="account.region" />
          </el-form-item>
          <el-form-item label="User">
            <el-input v-model="connectorForm.connection_config.user" />
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="connectorForm.connection_config.password" type="password" />
          </el-form-item>
          <el-form-item label="Warehouse">
            <el-input v-model="connectorForm.connection_config.warehouse" placeholder="COMPUTE_WH" />
          </el-form-item>
          <el-form-item label="Database">
            <el-input v-model="connectorForm.connection_config.database" />
          </el-form-item>
          <el-form-item label="Schema">
            <el-input v-model="connectorForm.connection_config.schema" placeholder="PUBLIC" />
          </el-form-item>
        </template>

        <!-- S3 Config -->
        <template v-if="connectorForm.destination_type === 's3'">
          <el-divider content-position="left">S3 Configuration</el-divider>
          <el-form-item label="Bucket">
            <el-input v-model="connectorForm.connection_config.bucket" placeholder="my-bucket" />
          </el-form-item>
          <el-form-item label="Prefix">
            <el-input v-model="connectorForm.connection_config.prefix" placeholder="data/" />
          </el-form-item>
          <el-form-item label="Region">
            <el-input v-model="connectorForm.connection_config.region" placeholder="us-east-1" />
          </el-form-item>
          <el-form-item label="Access Key ID">
            <el-input v-model="connectorForm.connection_config.access_key_id" />
          </el-form-item>
          <el-form-item label="Secret Access Key">
            <el-input v-model="connectorForm.connection_config.secret_access_key" type="password" />
          </el-form-item>
          <el-form-item label="File Format">
            <el-select v-model="connectorForm.connection_config.file_format">
              <el-option label="Parquet" value="parquet" />
              <el-option label="CSV" value="csv" />
              <el-option label="JSON" value="json" />
            </el-select>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="createConnector" :loading="connectorStore.loading">
          Create
        </el-button>
      </template>
    </el-dialog>

    <!-- Tables Dialog -->
    <el-dialog v-model="tablesDialogVisible" title="Available Tables" width="800px">
      <el-table :data="tables" v-loading="loadingTables">
        <el-table-column prop="schema_name" label="Schema" width="150" />
        <el-table-column prop="table_name" label="Table" width="200" />
        <el-table-column prop="row_count" label="Rows" width="150" />
        <el-table-column label="CDC Enabled" width="150">
          <template #default="{ row }">
            <el-tag :type="row.cdc_enabled ? 'success' : 'info'" size="small">
              {{ row.cdc_enabled ? 'Yes' : 'No' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Columns">
          <template #default="{ row }">
            {{ row.columns.length }} columns
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useConnectorStore } from '@/stores/connectorStore'
import { ElMessage, ElMessageBox } from 'element-plus'

const connectorStore = useConnectorStore()
const activeTab = ref('all')
const createDialogVisible = ref(false)
const tablesDialogVisible = ref(false)
const testingId = ref(null)
const loadingTables = ref(false)
const tables = ref([])

const connectorForm = ref({
  name: '',
  description: '',
  connector_type: 'source',
  source_type: null,
  destination_type: null,
  connection_config: {
    server: '',
    database: '',
    username: '',
    password: '',
    port: 1433,
    account: '',
    user: '',
    warehouse: '',
    schema: 'PUBLIC',
    bucket: '',
    prefix: '',
    region: 'us-east-1',
    access_key_id: '',
    secret_access_key: '',
    file_format: 'parquet'
  }
})

const filteredConnectors = computed(() => {
  if (activeTab.value === 'all') {
    return connectorStore.connectors
  }
  return connectorStore.connectors.filter(c => c.connector_type === activeTab.value)
})

const handleTabChange = () => {
  // Tab changed
}

const handleTypeChange = () => {
  connectorForm.value.source_type = null
  connectorForm.value.destination_type = null
}

const handleDestinationTypeChange = () => {
  // Reset config when destination type changes
}

const openCreateDialog = () => {
  connectorForm.value = {
    name: '',
    description: '',
    connector_type: 'source',
    source_type: 'sql_server',
    destination_type: null,
    connection_config: {
      server: '',
      database: '',
      username: '',
      password: '',
      port: 1433,
      account: '',
      user: '',
      warehouse: '',
      schema: 'PUBLIC',
      bucket: '',
      prefix: '',
      region: 'us-east-1',
      access_key_id: '',
      secret_access_key: '',
      file_format: 'parquet'
    }
  }
  createDialogVisible.value = true
}

const createConnector = async () => {
  try {
    await connectorStore.createConnector(connectorForm.value)
    ElMessage.success('Connector created successfully')
    createDialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to create connector')
  }
}

const testConnection = async (id) => {
  testingId.value = id
  try {
    const result = await connectorStore.testConnector(id)
    ElMessage.success(result.message)
    await connectorStore.fetchConnectors()
  } catch (error) {
    ElMessage.error('Connection test failed')
  } finally {
    testingId.value = null
  }
}

const viewTables = async (connector) => {
  loadingTables.value = true
  tablesDialogVisible.value = true
  try {
    tables.value = await connectorStore.listTables(connector.id)
  } catch (error) {
    ElMessage.error('Failed to load tables')
  } finally {
    loadingTables.value = false
  }
}

const deleteConnector = async (id) => {
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this connector?', 'Warning', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    await connectorStore.deleteConnector(id)
    ElMessage.success('Connector deleted successfully')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete connector')
    }
  }
}

onMounted(() => {
  connectorStore.fetchConnectors()
})
</script>

<style scoped>
.connectors {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

