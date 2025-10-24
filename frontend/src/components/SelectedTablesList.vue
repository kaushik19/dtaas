<template>
  <div class="selected-tables-list">
    <div class="list-header">
      <h3>Selected Tables ({{ tables.length }})</h3>
      <div class="header-actions">
        <el-button 
          type="success" 
          size="small"
          @click="$emit('bulkTransform')"
          :disabled="tables.length === 0"
        >
          <el-icon><SetUp /></el-icon>
          Bulk Transform
        </el-button>
        <el-button 
          type="primary" 
          size="small"
          @click="$emit('openTableSelection')"
        >
          <el-icon><Edit /></el-icon>
          Modify Selection
        </el-button>
      </div>
    </div>

    <div v-if="tables.length === 0" class="empty-state">
      <el-empty description="No tables selected">
        <el-button type="primary" @click="$emit('openTableSelection')">
          Select Tables
        </el-button>
      </el-empty>
    </div>

    <el-table 
      v-else
      :data="tables" 
      style="width: 100%"
      :max-height="400"
    >
      <el-table-column type="index" width="50" label="#" />
      
      <el-table-column prop="name" label="Table Name" min-width="250">
        <template #default="{ row }">
          <div class="table-name-cell">
            <el-icon><Document /></el-icon>
            <span>{{ row }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="Status" width="100">
        <template #default="{ row }">
          <el-tag 
            :type="getTableStatus(row)" 
            size="small"
          >
            {{ tableConfigs[row]?.enabled === false ? 'Disabled' : 'Enabled' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="Transformations" width="140">
        <template #default="{ row }">
          <el-tag v-if="getTransformCount(row) > 0" type="info" size="small">
            {{ getTransformCount(row) }} transform(s)
          </el-tag>
          <span v-else style="color: #909399; font-size: 12px;">None</span>
        </template>
      </el-table-column>

      <el-table-column label="Actions" width="300" fixed="right">
        <template #default="{ row, $index }">
          <el-button 
            size="small" 
            type="primary"
            @click="$emit('configureTransform', row)"
          >
            <el-icon><Setting /></el-icon>
            Transform
          </el-button>
          <el-button 
            size="small"
            @click="$emit('toggleTable', row)"
          >
            <el-icon><Switch /></el-icon>
            {{ tableConfigs[row]?.enabled === false ? 'Enable' : 'Disable' }}
          </el-button>
          <el-button 
            size="small" 
            type="danger"
            @click="$emit('removeTable', row)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Edit, Document, Setting, Switch, Delete, SetUp } from '@element-plus/icons-vue'

const props = defineProps({
  tables: {
    type: Array,
    default: () => []
  },
  tableConfigs: {
    type: Object,
    default: () => ({})
  }
})

defineEmits(['openTableSelection', 'configureTransform', 'toggleTable', 'removeTable', 'bulkTransform'])

const getTableStatus = (tableName) => {
  const config = props.tableConfigs[tableName]
  if (!config || config.enabled === false) return 'info'
  return 'success'
}

const getTransformCount = (tableName) => {
  const config = props.tableConfigs[tableName]
  return config?.transformations?.length || 0
}
</script>

<style scoped>
.selected-tables-list {
  margin-top: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.empty-state {
  padding: 40px;
  text-align: center;
}

.table-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-name-cell .el-icon {
  color: #409eff;
}
</style>

