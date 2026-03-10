<template>
  <teleport to="body">
    <div v-if="open" class="picker-overlay" @click.self="$emit('close')">
      <section class="picker-modal" role="dialog" aria-modal="true" :aria-label="title">
        <div class="picker-header">
          <h2 class="picker-title">{{ title }}</h2>
          <button class="icon-close" type="button" @click="$emit('close')" aria-label="Close picker">×</button>
        </div>

        <p class="picker-path">Current directory: <code>{{ currentPath }}</code></p>

        <div class="picker-actions">
          <button class="picker-btn" type="button" @click="goUp" :disabled="loading || currentPath === '/'">Up</button>
          <button class="picker-btn" type="button" @click="refresh" :disabled="loading">Refresh</button>
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
    </div>
  </teleport>
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
.picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1500;
  padding: 16px;
}
.picker-modal {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  width: min(780px, 100%);
  max-height: min(80vh, 760px);
  padding: 12px;
  display: flex;
  flex-direction: column;
}
.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.picker-title { margin: 0; font-size: 1.1rem; }
.icon-close {
  border: 1px solid #ccc;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  line-height: 1;
  width: 30px;
  height: 30px;
}
.picker-path { color: #666; margin: 8px 0; }
.picker-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.picker-btn { padding: 6px 10px; border: 1px solid #ccc; background: #f8f8f8; border-radius: 6px; cursor: pointer; }
.picker-btn:disabled { opacity: 0.6; cursor: default; }
.picker-error { color: #b00020; margin: 8px 0; }
.picker-list { list-style: none; margin: 8px 0 0; padding: 0; overflow: auto; }
.picker-row { border-bottom: 1px solid #efefef; padding: 4px 0; }
.picker-link { border: 0; background: transparent; cursor: pointer; padding: 4px 0; text-align: left; width: 100%; }
</style>
