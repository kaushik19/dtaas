import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Connectors from '@/views/Connectors.vue'
import Tasks from '@/views/Tasks.vue'
import TaskBuilder from '@/views/TaskBuilder.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/connectors',
    name: 'Connectors',
    component: Connectors
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: Tasks
  },
  {
    path: '/task-builder',
    name: 'TaskBuilder',
    component: TaskBuilder
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

