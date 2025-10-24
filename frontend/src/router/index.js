import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Connectors from '@/views/Connectors.vue'
import Tasks from '@/views/Tasks.vue'
import TaskBuilder from '@/views/TaskBuilder.vue'
import TaskDetail from '@/views/TaskDetail.vue'
import GlobalVariables from '@/views/GlobalVariables.vue'

const routes = [
  {
    path: '/test',
    name: 'Test',
    component: () => import('@/views/Dashboard-test.vue')
  },
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
    path: '/variables',
    name: 'GlobalVariables',
    component: GlobalVariables
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: Tasks
  },
  {
    path: '/tasks/:id/detail',
    name: 'TaskDetail',
    component: TaskDetail
  },
  {
    path: '/task-builder/:id?',
    name: 'TaskBuilder',
    component: TaskBuilder
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

