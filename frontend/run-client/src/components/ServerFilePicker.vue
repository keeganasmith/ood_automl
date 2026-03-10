<template>
  <section v-if="open" class="picker-card">
    <h2 class="picker-title">{{ title }}</h2>
    <p class="picker-path">Current directory: <code>{{ currentPath }}</code></p>

    <div class="picker-actions">
      <button class="picker-btn" type="button" @click="goUp" :disabled="loading || currentPath === '/'">Up</button>
      <button class="picker-btn" type="button" @click="refresh" :disabled="loading">Refresh</button>
      <button class="picker-btn" type="button" @click="$emit('close')">Close</button>
    </div>

    <p v-if="error" class="picker-error">{{ error }}</p>

    <ul class="picker-list">
      <li v-for="entry in entries" :key="entry.path" class="picker-row">
        <button
          v-if="entry.is_dir"
          type="button"
          class="picker-link"
          @click="openDir(entry.path)"
        >
          📁 {{ entry.name }}
        </button>
        <button
          v-else
          type="button"
          class="picker-link"
          @click="$emit('select', entry.path)"
        >
          📄 {{ entry.name }}
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getBaseURL } from '../main.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  startPath: { type: String, default: '~' },
  title: { type: String, default: 'Server File Picker' },
})

const emit = defineEmits(['select', 'close'])

const currentPath = ref('~')
const entries = ref([])
const loading = ref(false)
const error = ref('')

function api(path) {
  return getBaseURL(path)
}

async function load(path) {
  loading.value = true
  error.value = ''
  try {
    const query = new URLSearchParams({ path }).toString()
    const res = await fetch(`${api('server_files')}?${query}`)
    const data = await res.json()
    if (!res.ok || !data.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
    currentPath.value = data.path
    entries.value = Array.isArray(data.entries) ? data.entries : []
  } catch (e) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

function refresh() {
  load(currentPath.value)
}

function openDir(path) {
  load(path)
}

function goUp() {
  const parts = currentPath.value.split('/').filter(Boolean)
  const parent = parts.length ? `/${parts.slice(0, -1).join('/')}` || '/' : '/'
  load(parent)
}

watch(
  () => [props.open, props.startPath],
  ([open]) => {
    if (!open) return
    load(props.startPath || '~')
  },
  { immediate: true }
)
</script>

<style scoped>
.picker-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; padding: 12px; margin: 12px 0; }
.picker-title { margin: 0 0 6px; font-size: 1.1rem; }
.picker-path { color: #666; margin: 0 0 8px; }
.picker-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.picker-btn { padding: 6px 10px; border: 1px solid #ccc; background: #f8f8f8; border-radius: 6px; cursor: pointer; }
.picker-btn:disabled { opacity: 0.6; cursor: default; }
.picker-error { color: #b00020; margin: 8px 0; }
.picker-list { list-style: none; margin: 8px 0 0; padding: 0; max-height: 280px; overflow: auto; }
.picker-row { border-bottom: 1px solid #efefef; padding: 4px 0; }
.picker-link { border: 0; background: transparent; cursor: pointer; padding: 4px 0; text-align: left; width: 100%; }
</style>
