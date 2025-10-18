# DTaaS Frontend

Vue 3 frontend for Data Transfer as a Service

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **Pinia** - State management
- **Vue Router** - Routing
- **Element Plus** - UI component library
- **Vue Flow** - Drag-and-drop flow builder
- **Chart.js** - Data visualization
- **Axios** - HTTP client
- **Vite** - Build tool

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The app will be available at http://localhost:5173

3. Build for production:
```bash
npm run build
```

## Features

### Dashboard
- Real-time metrics and statistics
- Execution success rate charts
- Performance metrics
- Recent execution history

### Connectors
- Create and manage source/destination connectors
- Test connections
- View available tables from source databases
- Support for:
  - **Source**: SQL Server
  - **Destination**: Snowflake, S3 (Parquet/CSV/JSON)

### Tasks
- List all data transfer tasks
- Control task execution (start, stop, pause, resume)
- View execution history with detailed metrics
- Real-time progress tracking via WebSocket

### Task Builder
- Visual drag-and-drop interface
- Configure source and destination connectors
- Select tables to transfer
- Choose transfer mode (Full Load, CDC, or both)
- Add data transformations:
  - Add columns
  - Rename columns
  - Drop columns
  - Cast data types
  - Filter rows
  - Replace values
- Configure scheduling (on-demand, continuous, interval)
- Set batch size and performance options
- Enable schema drift handling

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client
│   ├── stores/           # Pinia stores
│   │   ├── connectorStore.js
│   │   ├── taskStore.js
│   │   ├── dashboardStore.js
│   │   └── websocketStore.js
│   ├── views/            # Page components
│   │   ├── Dashboard.vue
│   │   ├── Connectors.vue
│   │   ├── Tasks.vue
│   │   └── TaskBuilder.vue
│   ├── router/           # Vue Router config
│   ├── App.vue           # Root component
│   └── main.js           # App entry point
├── index.html
├── vite.config.js
└── package.json
```

## WebSocket Integration

The app connects to the backend WebSocket endpoint for real-time updates:
- Task status changes
- Progress updates
- Execution notifications

## API Integration

All API calls are proxied through Vite dev server:
- `/api/*` → `http://localhost:8000/api/*`
- `/ws` → `ws://localhost:8000/ws`

For production, configure your web server to proxy these endpoints to the backend.

## Development

### Add New Store

```javascript
// src/stores/myStore.js
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMyStore = defineStore('myStore', () => {
  const data = ref([])
  
  const fetchData = async () => {
    // Implementation
  }
  
  return { data, fetchData }
})
```

### Add New View

```vue
<!-- src/views/MyView.vue -->
<template>
  <div>
    <!-- Content -->
  </div>
</template>

<script setup>
// Logic
</script>

<style scoped>
/* Styles */
</style>
```

Then add route in `src/router/index.js`

## Deployment

### Build

```bash
npm run build
```

Output will be in `dist/` directory.

### Deploy

Deploy the `dist/` folder to any static hosting:
- Nginx
- Apache
- AWS S3 + CloudFront
- Netlify
- Vercel

### Environment Variables

For production, ensure the API endpoints are correctly configured in your reverse proxy or API gateway.

Example Nginx config:

```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;
}

location /ws {
    proxy_pass http://backend:8000/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

