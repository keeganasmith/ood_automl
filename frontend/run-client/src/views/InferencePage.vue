<!-- src/views/InferencePage.vue -->
<template>
    <div class="wrap">
      <h1>Run Inference</h1>
  
      <form class="card" @submit.prevent="runInference">
        <div class="row">
          <label for="job">Job ID</label>
          <select id="job" v-model="jobId" :disabled="loading">
            <option value="" disabled>Select a job…</option>
            <option v-for="id in jobIds" :key="id" :value="id">{{ id }}</option>
          </select>
          <button type="button" class="btn" @click="loadJobs" :disabled="loading">Reload jobs</button>
        </div>
  
        <div class="row">
          <label for="test">Test data path</label>
          <input
            id="test"
            v-model="testPath"
            type="text"
            placeholder="/path/to/test.csv (server path)"
            :disabled="loading"
          />
        </div>
  
        <div class="row">
          <label for="out">Output path</label>
          <input
            id="out"
            v-model="outputPath"
            type="text"
            placeholder="/path/to/preds.csv (server path)"
            :disabled="loading"
          />
        </div>
  
        <div class="row">
          <label class="chk">
            <input type="checkbox" v-model="proba" :disabled="loading" />
            Write predict_proba
          </label>
        </div>
  
        <div class="actions">
          <button class="btn primary" type="submit" :disabled="!canSubmit || loading">
            {{ loading ? 'Running…' : 'Run inference' }}
          </button>
          <button class="btn" type="button" @click="clear" :disabled="loading">Clear</button>
        </div>
  
        <p v-if="error" class="error">Error: {{ error }}</p>
        <p v-if="ok" class="ok">Success: wrote {{ result?.result?.rows ?? '?' }} rows to {{ result?.output_path }}</p>
      </form>
  
      <details v-if="result" class="card">
        <summary>Response details</summary>
        <pre class="pre">{{ pretty(result) }}</pre>
      </details>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, computed } from 'vue'
  import { getBaseURL } from '../main.js'
  
  const jobIds = ref([])
  const jobId = ref('')
  const testPath = ref('')
  const outputPath = ref('')
  const proba = ref(false)
  
  const loading = ref(false)
  const error = ref('')
  const result = ref(null)
  const ok = ref(false)
  
  const canSubmit = computed(() => !!jobId.value && !!testPath.value && !!outputPath.value)
  
  function api(path) {
    return getBaseURL(path) // respects /node/<host>/<port>/ prefix
  }
  
  async function loadJobs() {
    error.value = ''
    try {
      const res = await fetch(api('historic_jobs'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (!data.ok) throw new Error('Server returned ok=false')
      jobIds.value = Array.isArray(data.job_ids) ? data.job_ids : []
      if (!jobId.value && jobIds.value.length) jobId.value = jobIds.value[0]
    } catch (e) {
      error.value = e?.message || String(e)
    }
  }
  
  function pretty(v) {
    try { return JSON.stringify(v, null, 2) } catch { return String(v) }
  }
  
  function clear() {
    error.value = ''
    ok.value = false
    result.value = null
  }
  
  async function runInference() {
    clear()
    loading.value = true
    try {
      const payload = {
        test_path: testPath.value,
        job_id: jobId.value,
        output_path: outputPath.value,
        proba: !!proba.value,
      }
      const res = await fetch(api('inference'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`)
      }
      result.value = data
      ok.value = !!data.ok
    } catch (e) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
    }
  }
  
  onMounted(loadJobs)
  </script>
  
  <style scoped>
  .wrap { max-width: 760px; margin: 0 auto; padding: 16px; }
  .card { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; padding: 12px; margin: 12px 0; }
  .row { display: flex; gap: 10px; align-items: center; margin: 10px 0; }
  .row label { min-width: 140px; }
  .row input[type="text"], .row select { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 6px; }
  .chk { display: inline-flex; align-items: center; gap: 8px; }
  .actions { display: flex; gap: 8px; margin-top: 8px; }
  .btn { padding: 8px 12px; border: 1px solid #ccc; background: #f8f8f8; border-radius: 6px; cursor: pointer; }
  .btn.primary { background: #2d6cdf; border-color: #2d6cdf; color: #fff; }
  .btn:disabled { opacity: 0.6; cursor: default; }
  .error { color: #b00020; margin-top: 8px; }
  .ok { color: #0b7a0b; margin-top: 8px; }
  .pre { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
  </style>
  