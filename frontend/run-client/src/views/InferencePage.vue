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
          <button type="button" class="btn" @click="openPicker('test')" :disabled="loading">Choose File</button>
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
          <button type="button" class="btn" @click="openPicker('output')" :disabled="loading">Choose File</button>
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

      <section v-if="previewError" class="card">
        <p class="error">Preview error: {{ previewError }}</p>
      </section>

      <section v-if="previewColumns.length" class="card">
        <h2 class="preview-title">Output preview</h2>
        <p class="preview-meta">Showing {{ previewRows.length }} row(s) from {{ result?.output_path }}</p>
        <div class="preview-table-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th v-for="column in previewColumns" :key="column">{{ column }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in previewRows" :key="idx">
                <td v-for="column in previewColumns" :key="`${idx}-${column}`">{{ row[column] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <ServerFilePicker
        :open="pickerOpen"
        :start-path="pickerStartPath"
        title="Server File Picker"
        @select="selectEntry"
        @close="closePicker"
      />

      <details v-if="result" class="card">
        <summary>Response details</summary>
        <pre class="pre">{{ pretty(result) }}</pre>
      </details>
    </div>
  </template>

  <script setup>
  import { ref, onMounted, computed } from 'vue'
  import { getBaseURL } from '../main.js'
  import ServerFilePicker from '../components/ServerFilePicker.vue'

  const jobIds = ref([])
  const jobId = ref('')
  const testPath = ref('')
  const outputPath = ref('')
  const proba = ref(false)

  const loading = ref(false)
  const error = ref('')
  const result = ref(null)
  const ok = ref(false)
  const inferenceStartMs = ref(null)
  const previewColumns = ref([])
  const previewRows = ref([])
  const previewError = ref('')

  const pickerOpen = ref(false)
  const pickerTarget = ref('test')
  const pickerStartPath = ref('~')

  const canSubmit = computed(() => !!jobId.value && !!testPath.value && !!outputPath.value)

  function api(path) {
    return getBaseURL(path)
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


  function openPicker(target) {
    pickerTarget.value = target
    pickerOpen.value = true
    const start = target === 'test' ? (testPath.value || '~') : (outputPath.value || '~')
    pickerStartPath.value = start
  }

  function closePicker() {
    pickerOpen.value = false
  }


  function selectEntry(path) {
    if (pickerTarget.value === 'test') {
      testPath.value = path
    } else {
      outputPath.value = path
    }
    closePicker()
  }

  function pretty(v) {
    try { return JSON.stringify(v, null, 2) } catch { return String(v) }
  }

  function clear() {
    error.value = ''
    ok.value = false
    result.value = null
    previewColumns.value = []
    previewRows.value = []
    previewError.value = ''
  }



  async function loadPreview(path) {
    previewColumns.value = []
    previewRows.value = []
    previewError.value = ''
    try {
      const query = new URLSearchParams({ path, max_rows: '20' }).toString()
      const res = await fetch(`${api('file_preview')}?${query}`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`)
      }
      previewColumns.value = Array.isArray(data.columns) ? data.columns : []
      previewRows.value = Array.isArray(data.rows) ? data.rows : []
    } catch (e) {
      previewError.value = e?.message || String(e)
    }
  }

  function logLatency(label, detail = {}) {
    const now = performance.now()
    const payload = { label, t: now, ...detail }
    console.log(`[LATENCY] ${JSON.stringify(payload)}`)
  }

  async function runInference() {
    clear()
    loading.value = true
    inferenceStartMs.value = performance.now()
    logLatency('inference_start_click')
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
      if (ok.value && data.output_path) {
        await loadPreview(data.output_path)
      }
      if (inferenceStartMs.value !== null) {
        logLatency('inference_finished', {
          delta_ms: performance.now() - inferenceStartMs.value,
          ok: !!data.ok,
        })
      }
    } catch (e) {
      error.value = e?.message || String(e)
      if (inferenceStartMs.value !== null) {
        logLatency('inference_failed', {
          delta_ms: performance.now() - inferenceStartMs.value,
        })
      }
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
  .actions { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
  .btn { padding: 8px 12px; border: 1px solid #ccc; background: #f8f8f8; border-radius: 6px; cursor: pointer; }
  .btn.primary { background: #2d6cdf; border-color: #2d6cdf; color: #fff; }
  .btn:disabled { opacity: 0.6; cursor: default; }
  .error { color: #b00020; margin-top: 8px; }
  .ok { color: #0b7a0b; margin-top: 8px; }
  .pre { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
  .preview-title { margin: 0 0 8px; }
  .preview-meta { margin: 0 0 8px; color: #555; }
  .preview-table-wrap { overflow: auto; }
  .preview-table { width: 100%; border-collapse: collapse; }
  .preview-table th, .preview-table td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; white-space: nowrap; }
  .preview-table th { background: #f4f6f8; }
  </style>
