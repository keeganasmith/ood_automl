<template>
  <div class="job-list">
    <div class="toolbar">
      <input
        v-model="query"
        type="search"
        placeholder="Filter by ID, train path, or quality…"
        class="search"
        aria-label="Filter jobs"
      />
      <button @click="refresh" :disabled="loading" class="btn">
        {{ loading ? 'Loading…' : 'Refresh' }}
      </button>
    </div>

    <div v-if="error" class="error">Error: {{ error }}</div>

    <div v-if="filteredJobs.length" class="sort-hint">
      Tip: Click the <strong>Start</strong> or <strong>End</strong> headers to sort.
    </div>

    <table v-if="filteredJobs.length" class="jobs-table">
      <thead>
        <tr>
          <th>Job ID</th>

          <!-- Start: clickable, with icon & aria -->
          <th
            :class="['sortable', { 'sortable-active': sortBy === 'start' }]"
            @click="setSort('start')"
            :aria-sort="
              sortBy === 'start'
                ? (sortDir === 'asc' ? 'ascending' : 'descending')
                : 'none'
            "
            title="Click to sort by start time"
          >
            Start
            <span class="sort-icon">
              <span v-if="sortBy !== 'start'">⇅</span>
              <span v-else>{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
            </span>
          </th>

          <!-- End: clickable, with icon & aria -->
          <th
            :class="['sortable', { 'sortable-active': sortBy === 'end' }]"
            @click="setSort('end')"
            :aria-sort="
              sortBy === 'end'
                ? (sortDir === 'asc' ? 'ascending' : 'descending')
                : 'none'
            "
            title="Click to sort by end time"
          >
            End
            <span class="sort-icon">
              <span v-if="sortBy !== 'end'">⇅</span>
              <span v-else>{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
            </span>
          </th>

          <th>Train Path</th>
          <th>Quality</th>
          <th>Data Type</th>
          <th>Actions</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="job in filteredJobs" :key="job.id">
          <td class="mono">{{ job.id }}</td>
          <td>{{ job.start || "—" }}</td>
          <td>{{ job.end || "—" }}</td>
          <td>{{ job.cfg?.train_path || "—" }}</td>
          <td>{{ job.cfg?.presets || "—" }}</td>
          <td>{{ job.cfg?.data_type || "-" }}</td>
          <td>
            <div class="actions">
              <button class="btn" @click="$emit('select', job.id)">
                Select
              </button>
              <button
                class="btn btn-danger"
                @click="deleteJob(job.id)"
                :disabled="isDeleting(job.id)"
              >
                {{ isDeleting(job.id) ? "Deleting…" : "Delete" }}
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else-if="!loading && !error" class="empty">No jobs found.</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import { getBaseURL } from "../main.js";

const emit = defineEmits(["select", "refresh"]);

const jobs = ref([]);      // array of { id, cfg, start, end, ... }
const loading = ref(false);
const error = ref("");
const query = ref("");

// sort state
const sortBy = ref(null);      // 'start' | 'end' | null
const sortDir = ref("desc");   // 'asc' | 'desc'

// track which jobs are being deleted
const deletingIds = ref([]);   // array of job ids currently deleting

let abortCtrl = null;

function jobsUrl() {
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

    // data.jobs is an object keyed by job id -> convert to array
    jobs.value = Object.entries(data.jobs).map(([id, info]) => ({
      id,
      ...info, // cfg, file_path, start, end, etc.
    }));

    console.log("jobs array:", jobs.value);
    emit("refresh", jobs.value);
  } catch (e) {
    if (e.name !== "AbortError") {
      error.value = e?.message || String(e);
    }
  } finally {
    loading.value = false;
  }
}

// helper: parse job date safely into a number
function parseJobDate(value) {
  if (!value) return 0;
  // your dates look like "2025-11-20 15:57:31.149791"
  // replace space with 'T' for better Date parsing
  const s = String(value).replace(" ", "T");
  const t = Date.parse(s);
  return Number.isNaN(t) ? 0 : t;
}

function setSort(column) {
  if (sortBy.value === column) {
    // toggle direction
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortBy.value = column;
    sortDir.value = "asc";
  }
}

const filteredJobs = computed(() => {
  const q = query.value.trim().toLowerCase();

  // 1. filter
  let list = jobs.value;
  if (q) {
    list = list.filter((job) => {
      const id = job.id?.toLowerCase() || "";
      const trainPath = job.cfg?.train_path?.toLowerCase() || "";
      const presets = job.cfg?.presets?.toLowerCase() || "";
      return id.includes(q) || trainPath.includes(q) || presets.includes(q);
    });
  }

  // 2. sort (by start/end)
  if (!sortBy.value) return list;

  const column = sortBy.value;
  const dir = sortDir.value;

  // copy so we don't mutate original
  return [...list].sort((a, b) => {
    const va = parseJobDate(a[column]);
    const vb = parseJobDate(b[column]);
    if (va === vb) return 0;
    return dir === "asc" ? va - vb : vb - va;
  });
});

// ---- delete job ----

function isDeleting(jobId) {
  return deletingIds.value.includes(jobId);
}

async function deleteJob(jobId) {
  const confirmed = window.confirm(
    `Delete job ${jobId}? This action cannot be undone.`
  );
  if (!confirmed) return;

  // mark as deleting
  deletingIds.value = [...deletingIds.value, jobId];
  error.value = "";

  try {
    const url = getBaseURL(`job/delete/${jobId}`);
    const res = await fetch(url, {
      method: "DELETE", // change to 'POST' here if your backend expects POST
    });

    if (!res.ok) {
      throw new Error(`Failed to delete job (HTTP ${res.status})`);
    }

    // if backend returns JSON with ok=false, handle that too
    let data = null;
    try {
      data = await res.json();
      if (data && data.ok === false) {
        throw new Error(data.message || "Server reported delete failure");
      }
    } catch {
      // response might be empty or not JSON; ignore
    }

    // remove from local list
    jobs.value = jobs.value.filter((job) => job.id !== jobId);
    emit("refresh", jobs.value);
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    // unmark
    deletingIds.value = deletingIds.value.filter((id) => id !== jobId);
  }
}

function refresh() {
  fetchJobs();
}

onMounted(fetchJobs);
onBeforeUnmount(() => {
  if (abortCtrl) abortCtrl.abort();
});
</script>

<style scoped>
.job-list { max-width: 960px; margin: 0 auto; padding: 12px; }

.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.search { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 6px; }

.btn {
  padding: 6px 10px;
  border: 1px solid #ccc;
  background: #f7f7f7;
  border-radius: 6px;
  cursor: pointer;
}
.btn:disabled { opacity: 0.6; cursor: default; }

/* danger button variant */
.btn-danger {
  border-color: #e55;
  background: #ffe9e9;
  color: #a00;
}

.actions {
  display: flex;
  gap: 6px;
}

.error { color: #b00020; margin: 8px 0; }
.empty { color: #666; margin-top: 12px; }

.sort-hint {
  font-size: 0.8rem;
  color: #555;
  margin-bottom: 4px;
}

.jobs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  background: #fff;
}

.jobs-table th,
.jobs-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #eee;
  text-align: left;
  vertical-align: top;
}

.jobs-table thead {
  background: #fafafa;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
  font-size: 0.8rem;
  word-break: break-all;
}

/* sorting UI */
.sortable {
  cursor: pointer;
  user-select: none;
}
.sortable span {
  margin-left: 4px;
  font-size: 0.75rem;
}
</style>
