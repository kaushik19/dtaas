<template>
  <el-dialog 
    v-model="visible" 
    title="Select Tables" 
    width="900px"
    @close="handleClose"
  >
    <div class="table-selection-container">
      <!-- Schema Filter -->
      <div class="filter-section">
        <el-select 
          v-model="selectedSchema" 
          placeholder="Filter by schema (optional)"
          clearable
          @change="onSchemaChange"
          style="width: 200px;"
        >
          <el-option
            v-for="schema in availableSchemas"
            :key="schema"
            :label="schema"
            :value="schema"
          />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="Search tables..."
          clearable
          style="width: 300px; margin-left: 10px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- Transfer Box -->
      <div class="transfer-box">
        <!-- Available Tables (Left) -->
        <div class="box-panel">
          <div class="panel-header">
            <span>Available Tables ({{ filteredAvailableTables.length }})</span>
            <el-button 
              text 
              size="small" 
              @click="selectAll"
              :disabled="filteredAvailableTables.length === 0"
            >
              Select All
            </el-button>
          </div>
          <div class="panel-body">
            <el-scrollbar height="400px">
              <div 
                v-for="table in filteredAvailableTables" 
                :key="`${table.schema_name}.${table.table_name}`"
                class="table-item"
                @click="moveToSelected(table)"
              >
                <span class="table-name">
                  {{ table.schema_name }}.{{ table.table_name }}
                </span>
                <div class="table-meta">
                  <el-tag v-if="table.cdc_enabled" type="success" size="small">CDC</el-tag>
                  <span class="row-count">{{ table.row_count }} rows</span>
                  <span class="column-count">{{ table.columns.length }} cols</span>
                </div>
              </div>
              <el-empty 
                v-if="filteredAvailableTables.length === 0" 
                description="No tables available"
                :image-size="80"
              />
            </el-scrollbar>
          </div>
        </div>

        <!-- Arrow Buttons -->
        <div class="arrow-buttons">
          <el-button 
            :icon="DArrowRight" 
            circle 
            @click="moveAllToSelected"
            :disabled="filteredAvailableTables.length === 0"
            title="Move all"
          />
          <el-button 
            :icon="ArrowLeft" 
            circle 
            @click="moveAllToAvailable"
            :disabled="localSelectedTables.length === 0"
            title="Move all back"
          />
        </div>

        <!-- Selected Tables (Right) -->
        <div class="box-panel">
          <div class="panel-header">
            <span>Selected Tables ({{ localSelectedTables.length }})</span>
            <el-button 
              text 
              size="small" 
              @click="clearSelected"
              :disabled="localSelectedTables.length === 0"
            >
              Clear All
            </el-button>
          </div>
          <div class="panel-body">
            <el-scrollbar height="400px">
              <div 
                v-for="table in localSelectedTables" 
                :key="`${table.schema_name}.${table.table_name}`"
                class="table-item selected"
                @click="moveToAvailable(table)"
              >
                <span class="table-name">
                  {{ table.schema_name }}.{{ table.table_name }}
                </span>
                <div class="table-meta">
                  <el-tag v-if="table.cdc_enabled" type="success" size="small">CDC</el-tag>
                  <span class="row-count">{{ table.row_count }} rows</span>
                  <span class="column-count">{{ table.columns.length }} cols</span>
                </div>
              </div>
              <el-empty 
                v-if="localSelectedTables.length === 0" 
                description="No tables selected"
                :image-size="80"
              />
            </el-scrollbar>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">Cancel</el-button>
      <el-button type="primary" @click="handleConfirm">
        Confirm ({{ localSelectedTables.length }} selected)
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { DArrowRight, ArrowLeft, Search } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean,
  tables: {
    type: Array,
    default: () => []
  },
  selectedTables: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const selectedSchema = ref('')
const searchText = ref('')
const localSelectedTables = ref([])

// Initialize selected tables when tables or selectedTables change
watch([() => props.tables, () => props.selectedTables], ([tables, selectedTables]) => {
  if (tables.length > 0 && selectedTables.length > 0) {
    localSelectedTables.value = tables.filter(t => 
      selectedTables.includes(`${t.schema_name}.${t.table_name}`)
    )
  } else if (selectedTables.length === 0) {
    localSelectedTables.value = []
  }
}, { immediate: true, deep: true })

// Get unique schemas
const availableSchemas = computed(() => {
  const schemas = new Set(props.tables.map(t => t.schema_name))
  return Array.from(schemas).sort()
})

// Filter available tables (not yet selected)
const availableTables = computed(() => {
  const selectedNames = new Set(
    localSelectedTables.value.map(t => `${t.schema_name}.${t.table_name}`)
  )
  return props.tables.filter(t => 
    !selectedNames.has(`${t.schema_name}.${t.table_name}`)
  )
})

// Filter by schema and search
const filteredAvailableTables = computed(() => {
  let filtered = availableTables.value

  // Filter by schema
  if (selectedSchema.value) {
    filtered = filtered.filter(t => t.schema_name === selectedSchema.value)
  }

  // Filter by search text
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    filtered = filtered.filter(t => 
      t.schema_name.toLowerCase().includes(search) ||
      t.table_name.toLowerCase().includes(search)
    )
  }

  return filtered
})

const moveToSelected = (table) => {
  localSelectedTables.value.push(table)
}

const moveToAvailable = (table) => {
  const index = localSelectedTables.value.findIndex(t => 
    t.schema_name === table.schema_name && t.table_name === table.table_name
  )
  if (index > -1) {
    localSelectedTables.value.splice(index, 1)
  }
}

const moveAllToSelected = () => {
  localSelectedTables.value.push(...filteredAvailableTables.value)
}

const moveAllToAvailable = () => {
  localSelectedTables.value = []
}

const selectAll = () => {
  localSelectedTables.value.push(...filteredAvailableTables.value)
}

const clearSelected = () => {
  localSelectedTables.value = []
}

const onSchemaChange = () => {
  // Schema filter changed
}

const handleClose = () => {
  visible.value = false
}

const handleConfirm = () => {
  const selectedTableNames = localSelectedTables.value.map(t => 
    `${t.schema_name}.${t.table_name}`
  )
  emit('confirm', selectedTableNames)
  visible.value = false
}
</script>

<style scoped>
.table-selection-container {
  padding: 10px 0;
}

.filter-section {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.transfer-box {
  display: flex;
  gap: 20px;
  align-items: center;
}

.box-panel {
  flex: 1;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.panel-header {
  padding: 10px 15px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}

.panel-body {
  background-color: #fff;
}

.table-item {
  padding: 12px 15px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.2s;
}

.table-item:hover {
  background-color: #f5f7fa;
}

.table-item:last-child {
  border-bottom: none;
}

.table-item.selected {
  background-color: #ecf5ff;
}

.table-item.selected:hover {
  background-color: #d9ecff;
}

.table-name {
  display: block;
  font-weight: 500;
  margin-bottom: 5px;
  color: #303133;
}

.table-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.row-count, .column-count {
  padding: 2px 8px;
  background-color: #f4f4f5;
  border-radius: 3px;
}

.arrow-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>

