import { createRouter, createWebHistory } from 'vue-router'
import RunControllerView from './views/RunControllerView.vue'
import JobListPage from './views/JobListPage.vue'
import JobLogsPage from './views/JobLogsPage.vue'
import InferencePage from './views/InferencePage.vue'

function inferOODBase(pathname) {
  const m = pathname.match(/^\/(r?node)\/[^/]+\/\d+\/?/);
  return m ? (m[0].endsWith('/') ? m[0] : m[0] + '/') : '/';
}

export const router = createRouter({
  history: createWebHistory(inferOODBase(window.location.pathname)),
  routes: [
    { path: '/', name: 'home', component: RunControllerView },
    { path: '/jobs', name: 'jobs', component: JobListPage },
    { path: '/jobs/:id', name: 'job-logs', component: JobLogsPage, props: true },
    { path: '/inference', name: 'inference', component: InferencePage },
  ],
});
