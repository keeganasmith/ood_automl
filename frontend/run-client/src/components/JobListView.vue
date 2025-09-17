<!-- src/components/JobListView.vue -->
<template>
    <div class="job-list">
      <div class="toolbar">
        <input
          v-model="query"
          type="search"
          placeholder="Filter job IDs…"
          class="search"
          aria-label="Filter job IDs"
        />
        <button @click="refresh" :disabled="loading" class="btn">
          {{ loading ? 'Loading…' : 'Refresh' }}
        </button>
      </div>
  
      <div v-if="error" class="error">Error: {{ error }}</div>
  
      <ul class="list" v-if="filteredJobs.length">
        <li v-for="id in filteredJobs" :key="id" class="item">
          <span class="mono">{{ id }}</span>
          <div class="actions">
            <button class="btn" @click="$emit('select', id)">Select</button>
          </div>
        </li>
      </ul>
  
      <div v-else-if="!loading && !error" class="empty">No jobs found.</div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onBeforeUnmount, computed } from "vue";
  // Adjust the path below if your folder layout differs
  import { getBaseURL } from "../main.js";
  
  const emit = defineEmits(["select", "refresh"]);
  
  const jobs = ref([]);
  const loading = ref(false);
  const error = ref("");
  const query = ref("");
  
  let abortCtrl = null;
  
  function jobsUrl() {
    // Backend endpoint: GET <BASE_URL>/historic_jobs
    return getBaseURL("historic_jobs");
  }
  
  async function fetchJobs() {
    loading.value = true;
    error.value = "";
    if (abortCtrl) abortCtrl.abort();
    abortCtrl = new AbortController();
    try {
      const res = await fetch(jobsUrl(), { signal: abortCtrl.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!data.ok) throw new Error("Server returned ok=false");
      jobs.value = Array.isArray(data.job_ids) ? data.job_ids : [];
      emit("refresh", jobs.value);
    } catch (e) {
      if (e.name !== "AbortError") error.value = e?.message || String(e);
    } finally {
      loading.value = false;
    }
  }
  
  const filteredJobs = computed(() => {
    const q = query.value.trim().toLowerCase();
    if (!q) return jobs.value;
    return jobs.value.filter((id) => String(id).toLowerCase().includes(q));
  });
  
  function refresh() {
    fetchJobs();
  }
  
  onMounted(fetchJobs);
  onBeforeUnmount(() => {
    if (abortCtrl) abortCtrl.abort();
  });
  </script>
  
  <style scoped>
  .job-list { max-width: 720px; margin: 0 auto; padding: 12px; }
  .toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
  .search { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 6px; }
  .btn { padding: 8px 10px; border: 1px solid #ccc; background: #f7f7f7; border-radius: 6px; cursor: pointer; }
  .btn:disabled { opacity: 0.6; cursor: default; }
  .error { color: #b00020; margin: 8px 0; }
  .empty { color: #666; margin-top: 12px; }
  .list { list-style: none; padding: 0; margin: 0; }
  .item { display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
  .actions { display: flex; gap: 8px; }
  </style>
  