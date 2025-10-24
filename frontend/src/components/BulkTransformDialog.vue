<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="Bulk Transformations"
    width="600px"
  >
    <div>
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <template #title>
          Add transformation to ALL selected tables
        </template>
        <div style="font-size: 13px; margin-top: 8px;">
          This transformation will be added to each table individually. You can later remove it from specific tables if needed.
        </div>
      </el-alert>

      <el-form :model="transform" label-width="120px">
        <el-form-item label="Transformation">
          <el-select v-model="transform.type" style="width: 100%;" disabled>
            <el-option label="Add Column" value="add_column" />
          </el-select>
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            More transformation types coming soon!
          </div>
        </el-form-item>

        <el-divider />

        <!-- Add Column Configuration -->
        <div v-if="transform.type === 'add_column'">
          <el-form-item label="Column Name" required>
            <el-input 
              v-model="transform.config.column_name" 
              placeholder="e.g., ETLCustomerId"
            />
          </el-form-item>

          <el-form-item label="Value" required>
            <el-input 
              v-model="transform.config.value" 
              placeholder="e.g., $ETLCustomerId or static value"
            />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              Use $VariableName for dynamic variables, or enter a static value
            </div>
          </el-form-item>

          <el-form-item label="Data Type">
            <el-select v-model="transform.config.data_type" style="width: 100%;">
              <el-option label="String" value="string" />
              <el-option label="Integer" value="int" />
              <el-option label="Float" value="float" />
              <el-option label="Boolean" value="bool" />
              <el-option label="Date" value="date" />
              <el-option label="DateTime" value="datetime" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="cancel">Cancel</el-button>
      <el-button type="primary" @click="save" :disabled="!isValid">
        Add Transformation
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'save'])

const transform = ref({
  type: 'add_column',
  config: {
    column_name: '',
    value: '',
    data_type: 'string'
  }
})

const isValid = computed(() => {
  if (transform.value.type === 'add_column') {
    return transform.value.config.column_name && transform.value.config.value
  }
  return false
})

const cancel = () => {
  emit('update:modelValue', false)
  resetForm()
}

const save = () => {
  if (!isValid.value) return
  
  // Create a clean copy of the transformation
  const transformCopy = JSON.parse(JSON.stringify(transform.value))
  emit('save', transformCopy)
  emit('update:modelValue', false)
  resetForm()
}

const resetForm = () => {
  transform.value = {
    type: 'add_column',
    config: {
      column_name: '',
      value: '',
      data_type: 'string'
    }
  }
}

// Reset form when dialog opens
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    resetForm()
  }
})
</script>

<style scoped>
.el-form-item {
  margin-bottom: 22px;
}
</style>

