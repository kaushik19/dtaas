import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useWebSocketStore = defineStore('websocket', () => {
  const ws = ref(null)
  const connected = ref(false)
  const messages = ref([])

  const connect = () => {
    if (ws.value) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        messages.value.push(data)
        
        // Emit event for other stores to listen
        window.dispatchEvent(new CustomEvent('ws-message', { detail: data }))
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onclose = () => {
      connected.value = false
      
      // Reconnect after 3 seconds
      setTimeout(() => {
        if (!connected.value) {
          connect()
        }
      }, 3000)
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      connected.value = false
    }
  }

  const send = (data) => {
    if (ws.value && connected.value) {
      ws.value.send(JSON.stringify(data))
    }
  }

  return {
    connected,
    messages,
    connect,
    disconnect,
    send
  }
})

