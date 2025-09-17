<template>
    <div style="padding:12px">
      <h1>Jobs</h1>
      <JobListView @select="goToLogs" />
    </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import JobListView from '../components/JobListView.vue'

const router = useRouter()
function goToLogs(id) {
    router.push({ name: 'job-logs', params: { id } })
}
</script>