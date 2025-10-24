<template>
  <el-dialog 
    v-model="visible" 
    :title="`Transform: ${tableName}`"
    width="800px"
    @close="handleClose"
  >
    <div class="transform-config">
      <div class="current-transforms">
        <h4>Current Transformations ({{ localTransformations.length }})</h4>
        
        <el-empty 
          v-if="localTransformations.length === 0" 
          description="No transformations configured"
          :image-size="60"
        />
        
        <div v-else class="transforms-list">
          <el-card 
            v-for="(transform, index) in localTransformations" 
            :key="index"
            class="transform-card"
            shadow="hover"
          >
            <div class="transform-header">
              <el-tag size="small" type="primary">{{ transform.type }}</el-tag>
              <el-button 
                size="small" 
                type="danger" 
                link
                @click="removeTransformation(index)"
              >
                <el-icon><Delete /></el-icon>
                Remove
              </el-button>
            </div>
            <div class="transform-config-display">
              <pre>{{ JSON.stringify(transform.config, null, 2) }}</pre>
            </div>
          </el-card>
        </div>
      </div>

      <el-divider />

      <div class="add-transform">
        <h4>Add New Transformation</h4>
        
        <el-form :model="newTransform" label-width="120px" size="default">
          <el-form-item label="Type">
            <el-select 
              v-model="newTransform.type" 
              placeholder="Select transformation type"
              @change="onTransformTypeChange"
            >
              <el-option label="Add Column" value="add_column" />
              <el-option label="Rename Column" value="rename_column" />
              <el-option label="Drop Column" value="drop_column" />
              <el-option label="Cast Type" value="cast_type" />
              <el-option label="Filter Rows" value="filter_rows" />
              <el-option label="Replace Value" value="replace_value" />
              <el-option label="Concatenate Columns" value="concatenate_columns" />
              <el-option label="Split Column" value="split_column" />
              <el-option label="Apply Function" value="apply_function" />
            </el-select>
          </el-form-item>

          <!-- Dynamic config based on transform type -->
          <template v-if="newTransform.type === 'add_column'">
            <el-form-item label="Column Name">
              <el-input v-model="newTransform.config.column_name" placeholder="new_column" />
            </el-form-item>
            <el-form-item label="Value">
              <el-input v-model="newTransform.config.value" placeholder="constant value" />
            </el-form-item>
          </template>

          <template v-else-if="newTransform.type === 'rename_column'">
            <el-form-item label="Old Name">
              <el-select 
                v-model="newTransform.config.old_name" 
                placeholder="Select column"
                filterable
                :loading="loadingColumns"
              >
                <el-option 
                  v-for="col in tableColumns" 
                  :key="col" 
                  :label="col" 
                  :value="col"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="New Name">
              <el-input v-model="newTransform.config.new_name" placeholder="new_column" />
            </el-form-item>
          </template>

          <template v-else-if="newTransform.type === 'drop_column'">
            <el-form-item label="Column Name">
              <el-select 
                v-model="newTransform.config.column_name" 
                placeholder="Select column to drop"
                filterable
                :loading="loadingColumns"
              >
                <el-option 
                  v-for="col in tableColumns" 
                  :key="col" 
                  :label="col" 
                  :value="col"
                />
              </el-select>
            </el-form-item>
          </template>

          <template v-else-if="newTransform.type === 'cast_type'">
            <el-form-item label="Column Name">
              <el-select 
                v-model="newTransform.config.column_name" 
                placeholder="Select column"
                filterable
                :loading="loadingColumns"
              >
                <el-option 
                  v-for="col in tableColumns" 
                  :key="col" 
                  :label="col" 
                  :value="col"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="Target Type">
              <el-select v-model="newTransform.config.target_type">
                <el-option label="String" value="string" />
                <el-option label="Integer" value="int" />
                <el-option label="Float" value="float" />
                <el-option label="Boolean" value="bool" />
                <el-option label="Date" value="date" />
              </el-select>
            </el-form-item>
          </template>

          <template v-else-if="newTransform.type === 'filter_rows'">
            <el-form-item label="Column Name">
              <el-select 
                v-model="newTransform.config.column_name" 
                placeholder="Select column"
                filterable
                :loading="loadingColumns"
              >
                <el-option 
                  v-for="col in tableColumns" 
                  :key="col" 
                  :label="col" 
                  :value="col"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="Operator">
              <el-select v-model="newTransform.config.operator">
                <el-option label="Equals" value="==" />
                <el-option label="Not Equals" value="!=" />
                <el-option label="Greater Than" value=">" />
                <el-option label="Less Than" value="<" />
              </el-select>
            </el-form-item>
            <el-form-item label="Value">
              <el-input v-model="newTransform.config.value" placeholder="value" />
            </el-form-item>
          </template>

          <template v-else-if="newTransform.type === 'apply_function'">
            <el-form-item label="Column Name">
              <el-select 
                v-model="newTransform.config.column_name" 
                placeholder="Select column"
                filterable
                :loading="loadingColumns"
              >
                <el-option 
                  v-for="col in tableColumns" 
                  :key="col" 
                  :label="col" 
                  :value="col"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="Function">
              <el-select v-model="newTransform.config.function">
                <el-option label="Upper Case" value="upper" />
                <el-option label="Lower Case" value="lower" />
                <el-option label="Trim" value="trim" />
                <el-option label="Length" value="len" />
              </el-select>
            </el-form-item>
          </template>

          <el-form-item>
            <el-button type="primary" @click="addTransformation">
              <el-icon><Plus /></el-icon>
              Add Transformation
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">Cancel</el-button>
      <el-button type="primary" @click="handleSave">
        Save Transformations
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean,
  tableName: String,
  sourceConnectorId: Number,
  transformations: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'save'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const localTransformations = ref([])
const tableColumns = ref([])
const loadingColumns = ref(false)
const newTransform = ref({
  type: 'add_column',
  config: {}
})

// Initialize local transformations when dialog opens
watch(() => props.transformations, (newVal) => {
  localTransformations.value = JSON.parse(JSON.stringify(newVal || []))
}, { immediate: true, deep: true })

// Fetch table columns when dialog opens
const fetchTableColumns = async () => {
  if (!props.sourceConnectorId || !props.tableName) {
    return
  }
  
  // Parse schema.table format (e.g., "dbo.Customers")
  const tableParts = props.tableName.split('.')
  const schema = tableParts.length > 1 ? tableParts[0] : 'dbo'
  const table = tableParts.length > 1 ? tableParts[1] : props.tableName
  
  loadingColumns.value = true
  try {
    const axios = (await import('axios')).default
    const response = await axios.get(`/api/connectors/${props.sourceConnectorId}/tables/${encodeURIComponent(table)}/columns`, {
      params: { schema }
    })
    // Backend returns array directly, not wrapped in object
    tableColumns.value = response.data || []
  } catch (error) {
    console.error('Failed to load columns:', error)
  } finally {
    loadingColumns.value = false
  }
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    fetchTableColumns()
  }
})

const onTransformTypeChange = () => {
  newTransform.value.config = {}
}

const addTransformation = () => {
  localTransformations.value.push({
    type: newTransform.value.type,
    config: { ...newTransform.value.config }
  })
  newTransform.value = {
    type: 'add_column',
    config: {}
  }
}

const removeTransformation = (index) => {
  localTransformations.value.splice(index, 1)
}

const handleClose = () => {
  visible.value = false
}

const handleSave = () => {
  emit('save', props.tableName, localTransformations.value)
  visible.value = false
}
</script>

<style scoped>
.transform-config {
  max-height: 600px;
  overflow-y: auto;
}

.current-transforms h4,
.add-transform h4 {
  margin-top: 0;
  color: #303133;
  font-size: 14px;
}

.transforms-list {
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

.transform-config-display {
  font-size: 12px;
  background-color: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
}

.transform-config-display pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
}
</style>

