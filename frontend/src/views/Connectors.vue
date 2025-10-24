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
        <el-table-column label="Actions" width="300" fixed="right">
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
              type="primary"
              @click="openEditDialog(row)"
            >
              Edit
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

    <!-- Create/Edit Connector Dialog -->
    <el-dialog 
      v-model="createDialogVisible" 
      :title="isEditMode ? 'Edit Connector' : 'Create Connector'" 
      width="600px"
      :close-on-click-modal="false"
    >
      <el-alert 
        v-if="isEditMode" 
        type="info" 
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <template #title>
          Editing connector. Leave password fields empty to keep existing passwords.
        </template>
      </el-alert>

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
          <el-select v-model="connectorForm.source_type" @change="handleSourceTypeChange">
            <el-option label="SQL Server" value="sql_server" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="MySQL" value="mysql" />
            <el-option label="Oracle" value="oracle" />
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
          <el-form-item label="Source Database">
            <el-input v-model="connectorForm.connection_config.database" placeholder="mydb" />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              💡 The database to read data from
            </div>
          </el-form-item>
          <el-form-item label="Username">
            <el-input v-model="connectorForm.connection_config.username" placeholder="sa" />
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="connectorForm.connection_config.password" type="password" />
          </el-form-item>
          <el-form-item label="Port">
            <el-input-number v-model="connectorForm.connection_config.port" :min="1" :max="65535" :placeholder="1433" />
          </el-form-item>
        </template>

        <!-- PostgreSQL Config -->
        <template v-if="connectorForm.source_type === 'postgresql'">
          <el-divider content-position="left">PostgreSQL Configuration</el-divider>
          <el-form-item label="Host">
            <el-input v-model="connectorForm.connection_config.host" placeholder="localhost" />
          </el-form-item>
          <el-form-item label="Port">
            <el-input-number v-model="connectorForm.connection_config.port" :min="1" :max="65535" :placeholder="5432" />
          </el-form-item>
          <el-form-item label="Database">
            <el-input v-model="connectorForm.connection_config.database" placeholder="postgres" />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              💡 The database to read data from
            </div>
          </el-form-item>
          <el-form-item label="Username">
            <el-input v-model="connectorForm.connection_config.username" placeholder="postgres" />
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="connectorForm.connection_config.password" type="password" />
          </el-form-item>
          <el-form-item label="SSL Mode">
            <el-select v-model="connectorForm.connection_config.ssl_mode" placeholder="prefer">
              <el-option label="Disable" value="disable" />
              <el-option label="Allow" value="allow" />
              <el-option label="Prefer" value="prefer" />
              <el-option label="Require" value="require" />
              <el-option label="Verify-CA" value="verify-ca" />
              <el-option label="Verify-Full" value="verify-full" />
            </el-select>
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              SSL connection mode (default: prefer)
            </div>
          </el-form-item>
        </template>

        <!-- MySQL Config -->
        <template v-if="connectorForm.source_type === 'mysql'">
          <el-divider content-position="left">MySQL Configuration</el-divider>
          <el-form-item label="Host">
            <el-input v-model="connectorForm.connection_config.host" placeholder="localhost" />
          </el-form-item>
          <el-form-item label="Port">
            <el-input-number v-model="connectorForm.connection_config.port" :min="1" :max="65535" :placeholder="3306" />
          </el-form-item>
          <el-form-item label="Database">
            <el-input v-model="connectorForm.connection_config.database" placeholder="mydb" />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              💡 The database to read data from
            </div>
          </el-form-item>
          <el-form-item label="Username">
            <el-input v-model="connectorForm.connection_config.username" placeholder="root" />
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="connectorForm.connection_config.password" type="password" />
          </el-form-item>
          <el-form-item label="SSL Disabled">
            <el-switch v-model="connectorForm.connection_config.ssl_disabled" />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              Disable SSL connection (not recommended for production)
            </div>
          </el-form-item>
        </template>

        <!-- Oracle Config -->
        <template v-if="connectorForm.source_type === 'oracle'">
          <el-divider content-position="left">Oracle Configuration</el-divider>
          <el-form-item label="Host">
            <el-input v-model="connectorForm.connection_config.host" placeholder="localhost" />
          </el-form-item>
          <el-form-item label="Port">
            <el-input-number v-model="connectorForm.connection_config.port" :min="1" :max="65535" :placeholder="1521" />
          </el-form-item>
          <el-form-item label="Connection Type">
            <el-radio-group v-model="connectorForm.connection_config.connection_type">
              <el-radio label="service_name">Service Name</el-radio>
              <el-radio label="sid">SID</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="connectorForm.connection_config.connection_type === 'service_name'" label="Service Name">
            <el-input v-model="connectorForm.connection_config.service_name" placeholder="ORCL" />
          </el-form-item>
          <el-form-item v-else label="SID">
            <el-input v-model="connectorForm.connection_config.sid" placeholder="XE" />
          </el-form-item>
          <el-form-item label="Username">
            <el-input v-model="connectorForm.connection_config.username" placeholder="system" />
          </el-form-item>
          <el-form-item label="Password">
            <el-input v-model="connectorForm.connection_config.password" type="password" />
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
          <el-form-item label="Target Database">
            <el-input v-model="connectorForm.connection_config.database" />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              💡 The database to write data to
            </div>
          </el-form-item>
          <el-form-item label="Schema">
            <el-input v-model="connectorForm.connection_config.schema" placeholder="PUBLIC" />
          </el-form-item>
        </template>

        <!-- S3 Config -->
        <template v-if="connectorForm.destination_type === 's3'">
          <el-divider content-position="left">S3 Configuration</el-divider>
          
          <el-form-item label="Use LocalStack">
            <el-switch v-model="connectorForm.connection_config.use_localstack" />
            <el-text size="small" type="info" style="margin-left: 10px;">
              Enable for local testing with LocalStack
            </el-text>
          </el-form-item>

          <el-form-item label="Bucket">
            <el-input v-model="connectorForm.connection_config.bucket" placeholder="my-bucket" />
          </el-form-item>
          <el-form-item label="Prefix">
            <el-input v-model="connectorForm.connection_config.prefix" placeholder="data/" />
          </el-form-item>
          <el-form-item label="Region">
            <el-input v-model="connectorForm.connection_config.region" placeholder="us-east-1" />
          </el-form-item>
          
          <template v-if="!connectorForm.connection_config.use_localstack">
            <el-form-item label="Access Key ID">
              <el-input v-model="connectorForm.connection_config.access_key_id" />
            </el-form-item>
            <el-form-item label="Secret Access Key">
              <el-input v-model="connectorForm.connection_config.secret_access_key" type="password" />
            </el-form-item>
          </template>
          
          <template v-else>
            <el-form-item label="Access Key ID">
              <el-input v-model="connectorForm.connection_config.access_key_id" placeholder="test (default)" />
            </el-form-item>
            <el-form-item label="Secret Access Key">
              <el-input v-model="connectorForm.connection_config.secret_access_key" type="password" placeholder="test (default)" />
            </el-form-item>
            <el-form-item label="Endpoint URL">
              <el-input v-model="connectorForm.connection_config.endpoint_url" placeholder="http://localhost:4566" />
            </el-form-item>
          </template>

          <el-form-item label="File Format">
            <el-select v-model="connectorForm.connection_config.file_format">
              <el-option label="Parquet" value="parquet" />
              <el-option label="CSV" value="csv" />
              <el-option label="JSON" value="json" />
            </el-select>
          </el-form-item>

          <el-divider content-position="left">Dynamic Path Configuration (Optional)</el-divider>
          
          <el-form-item label="Path Template">
            <el-input 
              v-model="connectorForm.connection_config.path_template" 
              placeholder="e.g., data/$customerId/$tableName/$uuid-$timestamp.json"
            >
              <template #prepend>s3://{{ connectorForm.connection_config.bucket }}/</template>
            </el-input>
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              Available variables: $customerId, $tableName, $timestamp, $date, $uuid, $databaseName
            </div>
          </el-form-item>

          <el-form-item label="Enable Customer Query">
            <el-switch v-model="customerQueryEnabled" @change="toggleCustomerQuery" />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              Required if using $customerId in path template
            </div>
          </el-form-item>

          <template v-if="customerQueryEnabled">
            <el-card style="background-color: #f5f7fa; margin-bottom: 20px;">
              <template #header>
                <div style="font-size: 14px; font-weight: 600;">
                  Customer ID Query Builder
                </div>
              </template>

              <el-form-item label="Schema">
                <el-input v-model="customerQueryConfig.schema" placeholder="dbo" />
              </el-form-item>

              <el-form-item label="Table">
                <el-input v-model="customerQueryConfig.table" placeholder="Customers" />
              </el-form-item>

              <el-form-item label="Column to Select">
                <el-input v-model="customerQueryConfig.column" placeholder="Id" />
              </el-form-item>

              <el-divider content-position="left">WHERE Conditions</el-divider>

              <div v-for="(condition, index) in customerQueryConfig.where_conditions" :key="index" style="margin-bottom: 16px;">
                <el-card style="background-color: white;">
                  <div style="display: flex; gap: 8px; align-items: flex-start;">
                    <el-form-item label="Field" style="flex: 1; margin-bottom: 0;">
                      <el-input v-model="condition.field" placeholder="DatabaseName" />
                    </el-form-item>
                    <el-form-item label="Operator" style="width: 120px; margin-bottom: 0;">
                      <el-select v-model="condition.operator">
                        <el-option label="=" value="=" />
                        <el-option label="!=" value="!=" />
                        <el-option label=">" value=">" />
                        <el-option label="<" value="<" />
                        <el-option label=">=" value=">=" />
                        <el-option label="<=" value="<=" />
                        <el-option label="LIKE" value="LIKE" />
                        <el-option label="IN" value="IN" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="Value" style="flex: 1; margin-bottom: 0;">
                      <el-input v-model="condition.value" placeholder="$databaseName" />
                    </el-form-item>
                    <el-button 
                      type="danger" 
                      size="small" 
                      @click="removeWhereCondition(index)"
                      style="margin-top: 32px;"
                    >
                      Remove
                    </el-button>
                  </div>
                </el-card>
              </div>

              <el-button 
                type="primary" 
                size="small" 
                @click="addWhereCondition"
                style="width: 100%;"
              >
                <el-icon><Plus /></el-icon>
                Add WHERE Condition
              </el-button>

              <div style="margin-top: 12px; padding: 8px; background-color: #ecf5ff; border-radius: 4px; font-size: 12px; color: #409eff;">
                <strong>Query Preview:</strong><br>
                <code>{{ buildQueryPreview() }}</code>
              </div>
            </el-card>
          </template>
        </template>
      </el-form>

      <template #footer>
        <span style="float: left;">
          <el-button 
            type="success" 
            @click="testConnectionInDialog" 
            :loading="testingInDialog"
          >
            Test Connection
          </el-button>
        </span>
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="createConnector" :loading="connectorStore.loading">
          {{ isEditMode ? 'Update' : 'Create' }}
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
const isEditMode = ref(false)
const testingInDialog = ref(false)
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
    file_format: 'parquet',
    path_template: '',
    customer_query_config: null
  }
})

// Customer query configuration
const customerQueryEnabled = ref(false)
const customerQueryConfig = ref({
  enabled: false,
  schema: 'dbo',
  table: '',
  column: '',
  where_conditions: []
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

const handleSourceTypeChange = () => {
  // Set default config values based on source type
  if (connectorForm.value.source_type === 'postgresql') {
    connectorForm.value.connection_config = {
      host: '',
      port: 5432,
      database: '',
      username: '',
      password: '',
      ssl_mode: 'prefer'
    }
  } else if (connectorForm.value.source_type === 'mysql') {
    connectorForm.value.connection_config = {
      host: '',
      port: 3306,
      database: '',
      username: '',
      password: '',
      ssl_disabled: false
    }
  } else if (connectorForm.value.source_type === 'oracle') {
    connectorForm.value.connection_config = {
      host: '',
      port: 1521,
      username: '',
      password: '',
      connection_type: 'service_name',
      service_name: '',
      sid: ''
    }
  } else if (connectorForm.value.source_type === 'sql_server') {
    connectorForm.value.connection_config = {
      server: '',
      port: 1433,
      database: '',
      username: '',
      password: ''
    }
  }
}

const handleDestinationTypeChange = () => {
  // Reset config when destination type changes
}

const openCreateDialog = () => {
  isEditMode.value = false
  connectorForm.value = {
    id: null,
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
      file_format: 'parquet',
      use_localstack: false,
      endpoint_url: 'http://localhost:4566',
      path_template: '',
      customer_query_config: null
    }
  }
  
  // Reset customer query config
  customerQueryEnabled.value = false
  customerQueryConfig.value = {
    enabled: false,
    schema: 'dbo',
    table: '',
    column: '',
    where_conditions: []
  }
  
  createDialogVisible.value = true
}

const openEditDialog = (connector) => {
  isEditMode.value = true
  connectorForm.value = {
    id: connector.id,
    name: connector.name,
    description: connector.description || '',
    connector_type: connector.connector_type,
    source_type: connector.source_type,
    destination_type: connector.destination_type,
    connection_config: {
      // Copy all connection config fields
      ...connector.connection_config,
      // Ensure password fields are empty for security (user must re-enter)
      password: '',
      secret_access_key: connector.connection_config.secret_access_key ? '' : '',
      // Preserve other fields
      port: connector.connection_config.port || 1433,
      schema: connector.connection_config.schema || 'PUBLIC',
      file_format: connector.connection_config.file_format || 'parquet',
      use_localstack: connector.connection_config.use_localstack || false,
      endpoint_url: connector.connection_config.endpoint_url || 'http://localhost:4566'
    }
  }
  
  // Load customer query config if it exists
  if (connector.connection_config.customer_query_config) {
    customerQueryEnabled.value = connector.connection_config.customer_query_config.enabled || false
    customerQueryConfig.value = {
      ...connector.connection_config.customer_query_config
    }
  } else {
    customerQueryEnabled.value = false
    customerQueryConfig.value = {
      enabled: false,
      schema: 'dbo',
      table: '',
      column: '',
      where_conditions: []
    }
  }
  
  createDialogVisible.value = true
}

// Customer Query Config Methods
const toggleCustomerQuery = (enabled) => {
  customerQueryConfig.value.enabled = enabled
  if (!enabled) {
    // Reset config when disabled
    customerQueryConfig.value = {
      enabled: false,
      schema: 'dbo',
      table: '',
      column: '',
      where_conditions: []
    }
  }
}

const addWhereCondition = () => {
  customerQueryConfig.value.where_conditions.push({
    field: '',
    operator: '=',
    value: ''
  })
}

const removeWhereCondition = (index) => {
  customerQueryConfig.value.where_conditions.splice(index, 1)
}

const buildQueryPreview = () => {
  if (!customerQueryConfig.value.table || !customerQueryConfig.value.column) {
    return 'Please fill in Table and Column fields'
  }
  
  const schema = customerQueryConfig.value.schema || 'dbo'
  const table = customerQueryConfig.value.table
  const column = customerQueryConfig.value.column
  
  let query = `SELECT [${column}] FROM [${schema}].[${table}]`
  
  const conditions = customerQueryConfig.value.where_conditions
  if (conditions && conditions.length > 0) {
    const whereClauses = conditions
      .filter(c => c.field && c.operator && c.value)
      .map(c => `[${c.field}] ${c.operator} ?`)
    
    if (whereClauses.length > 0) {
      query += ' WHERE ' + whereClauses.join(' AND ')
    }
  }
  
  return query
}

const createConnector = async () => {
  try {
    // Include customer query config if enabled
    if (customerQueryEnabled.value) {
      connectorForm.value.connection_config.customer_query_config = customerQueryConfig.value
    } else {
      // Remove it if disabled
      connectorForm.value.connection_config.customer_query_config = null
    }
    
    if (isEditMode.value) {
      // Update existing connector
      await connectorStore.updateConnector(connectorForm.value.id, connectorForm.value)
      ElMessage.success('Connector updated successfully')
    } else {
      // Create new connector
      await connectorStore.createConnector(connectorForm.value)
      ElMessage.success('Connector created successfully')
    }
    createDialogVisible.value = false
    await connectorStore.fetchConnectors()
  } catch (error) {
    const action = isEditMode.value ? 'update' : 'create'
    ElMessage.error(error.response?.data?.detail || `Failed to ${action} connector`)
  }
}

const testConnection = async (id) => {
  testingId.value = id
  try {
    const result = await connectorStore.testConnector(id)
    
    // Show detailed success message
    if (result.success) {
      let message = result.message
      if (result.details) {
        const details = Object.entries(result.details)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ')
        message += ` (${details})`
      }
      
      ElMessage({
        message: message,
        type: 'success',
        duration: 5000,
        showClose: true
      })
    }
    
    await connectorStore.fetchConnectors()
  } catch (error) {
    // Show detailed error message
    const errorMessage = error.response?.data?.detail || error.message || 'Connection test failed'
    
    ElMessage({
      message: errorMessage,
      type: 'error',
      duration: 8000,
      showClose: true,
      dangerouslyUseHTMLString: false
    })
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

const testConnectionInDialog = async () => {
  testingInDialog.value = true
  try {
    const { connectorsAPI } = await import('@/api')
    const result = await connectorsAPI.testConfig(connectorForm.value)
    
    // Show detailed success message
    if (result.data.success) {
      let message = result.data.message
      if (result.data.details) {
        const details = Object.entries(result.data.details)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ')
        message += ` (${details})`
      }
      
      ElMessage({
        message: message,
        type: 'success',
        duration: 5000,
        showClose: true
      })
    }
  } catch (error) {
    // Show detailed error message
    const errorMessage = error.response?.data?.detail || error.message || 'Connection test failed'
    
    ElMessage({
      message: errorMessage,
      type: 'error',
      duration: 8000,
      showClose: true
    })
  } finally {
    testingInDialog.value = false
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

