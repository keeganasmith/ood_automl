import { createRouter, createWebHistory } from 'vue-router'
import RunControllerView from './views/RunControllerView.vue'
import JobListPage from './views/JobListPage.vue'
import JobLogsPage from './views/JobLogsPage.vue'

const routes = [
  { path: '/', name: 'home', component: RunControllerView },
  { path: '/jobs', name: 'jobs', component: JobListPage },
  { path: '/jobs/:id', name: 'job-logs', component: JobLogsPage, props: true },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})