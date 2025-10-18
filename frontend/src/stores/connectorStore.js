import { defineStore } from 'pinia'
import { ref } from 'vue'
import { connectorsAPI } from '@/api'

export const useConnectorStore = defineStore('connector', () => {
  const connectors = ref([])
  const loading = ref(false)
  const error = ref(null)

  const fetchConnectors = async (type = null) => {
    loading.value = true
    error.value = null
    try {
      const response = await connectorsAPI.list(type)
      connectors.value = response.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const createConnector = async (data) => {
    loading.value = true
    error.value = null
    try {
      const response = await connectorsAPI.create(data)
      connectors.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const updateConnector = async (id, data) => {
    loading.value = true
    error.value = null
    try {
      const response = await connectorsAPI.update(id, data)
      const index = connectors.value.findIndex(c => c.id === id)
      if (index !== -1) {
        connectors.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const deleteConnector = async (id) => {
    loading.value = true
    error.value = null
    try {
      await connectorsAPI.delete(id)
      connectors.value = connectors.value.filter(c => c.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const testConnector = async (id) => {
    try {
      const response = await connectorsAPI.test(id)
      return response.data
    } catch (e) {
      throw e
    }
  }

  const listTables = async (id) => {
    try {
      const response = await connectorsAPI.listTables(id)
      return response.data
    } catch (e) {
      throw e
    }
  }

  const getSourceConnectors = () => {
    return connectors.value.filter(c => c.connector_type === 'source')
  }

  const getDestinationConnectors = () => {
    return connectors.value.filter(c => c.connector_type === 'destination')
  }

  return {
    connectors,
    loading,
    error,
    fetchConnectors,
    createConnector,
    updateConnector,
    deleteConnector,
    testConnector,
    listTables,
    getSourceConnectors,
    getDestinationConnectors
  }
})

