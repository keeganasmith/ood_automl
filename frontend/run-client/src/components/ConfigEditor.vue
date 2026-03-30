<!-- PrettyStartConfig.vue -->
<template>
  <n-card title="Start Config (JSON)" size="large" embedded>
    <n-space vertical size="large">
      <!-- Visual form editor -->
      <n-collapse :default-expanded-names="['form']">
        <n-collapse-item title="Form editor (all config options)" name="form">
          <!-- Tabs: Basic / Advanced -->
          <n-tabs type="line" animated>
            <!-- BASIC TAB -->
            <n-tab-pane name="basic" tab="Basic">
              <n-form :model="form" label-placement="top" size="small">
                <n-grid x-gap="12" y-gap="10" cols="1 s:2 m:2 l:3">
                  <n-gi>
                    <n-form-item label="job_id (optional)">
                      <n-input
                        v-model:value="form.job_id"
                        placeholder="Optional custom job id"
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="label" :rule="{ required: true, message: 'Required' }">
                      <n-input
                        v-model:value="form.label"
                        placeholder="e.g., Survived"
                        :input-props="{ 'data-testid': 'label-input' }"
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="train_path" :rule="{ required: true, message: 'Required' }">
                      <div class="path-picker-row">
                        <n-input
                          v-model:value="form.train_path"
                          placeholder="./sample_datasets/train.csv"
                          :input-props="{ 'data-testid': 'train-path-input' }"
                        />
                        <n-button secondary @click="openDatasetPicker">Choose File</n-button>
                      </div>
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="data_type">
                      <n-select
                        v-model:value="form.data_type"
                        :options="dataTypeOptions"
                        placeholder="tabular"
                        clearable
                        @update:value="onDataTypeChange"
                      />
                    </n-form-item>
                  </n-gi>

                  
                  <n-gi>
                    <n-form-item label="path (output dir)">
                      <n-input v-model:value="form.path" placeholder="./autogluon_runs/{run_id}" />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="presets">
                      <n-select
                        v-model:value="form.presets"
                        :options="presetOptions"
                        placeholder="medium"
                        clearable
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="time_limit (seconds)">
                      <n-input-number
                        v-model:value="form.time_limit"
                        :min="1"
                        :step="1"
                        placeholder="e.g., 120"
                        style="width: 100%;"
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="Enable GPU">
                      <n-checkbox
                        v-model:checked="form.enable_gpu"
                        data-testid="enable-gpu-checkbox"
                      >
                        Enable GPU
                      </n-checkbox>
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="problem_type">
                      <n-select
                        v-model:value="form.problem_type"
                        :options="problemTypeOptions"
                        placeholder="auto (omit)"
                        clearable
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="eval_metric">
                      <n-input
                        v-model:value="form.eval_metric"
                        placeholder="e.g., accuracy, roc_auc, rmse"
                      />
                      <n-text depth="3">Maps to AutoGluon predictor <code>eval_metric</code>. Leave blank for default inference.</n-text>
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="drop_columns (comma-separated)">
                      <n-input
                        v-model:value="form.dropColumnsText"
                        placeholder="e.g., PassengerId, Cabin"
                      />
                    </n-form-item>
                  </n-gi>

                  <!-- Time series–specific fields -->
                  <n-gi v-if="isSeries">
                    <n-form-item label="prediction_length" :rule="{ required: true, message: 'Required for series' }">
                      <n-input-number
                        v-model:value="form.prediction_length"
                        :min="1"
                        :step="1"
                        placeholder="e.g., 24"
                        style="width: 100%;"
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi v-if="isSeries">
                    <n-form-item label="id_column">
                      <n-input
                        v-model:value="form.id_column"
                        placeholder='e.g., "item_id"'
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi v-if="isSeries">
                    <n-form-item label="time_column">
                      <n-input
                        v-model:value="form.time_column"
                        placeholder='e.g., "timestamp"'
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi v-if="isSeries">
                    <n-form-item label="freq (pandas offset alias)">
                      <n-input
                        v-model:value="form.freq"
                        placeholder='e.g., "D", "H", "5min"'
                      />
                    </n-form-item>
                  </n-gi>
                </n-grid>
              </n-form>
            </n-tab-pane>

            <!-- ADVANCED TAB -->
            <n-tab-pane name="advanced" tab="Advanced">
              <n-form :model="form" label-placement="top" size="small">
                <n-grid x-gap="12" y-gap="10" cols="1 m:2">
                  <n-gi>
                    <n-form-item
                      label="hyperparameters (JSON object)"
                      :validation-status="hpValid ? 'success' : 'error'"
                      :feedback="hpValid ? 'valid JSON (or empty)' : 'invalid JSON'"
                    >
                      <n-input
                        v-model:value="form.hyperparametersText"
                        type="textarea"
                        :autosize="{ minRows: 6, maxRows: 16 }"
                        placeholder='e.g., { "GBM": {}, "CAT": {}, "XGB": {} }'
                      />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item
                      label="tuning_data (JSON; advanced)"
                      :validation-status="tdValid ? 'success' : 'error'"
                      :feedback="tdValid ? 'valid JSON (or empty)' : 'invalid JSON'"
                    >
                      <n-input
                        v-model:value="form.tuningDataText"
                        type="textarea"
                        :autosize="{ minRows: 6, maxRows: 16 }"
                        placeholder='Optional. Backend reads as Python-ish JSON (e.g., {"val_frac":0.1}). Usually leave blank.'
                      />
                    </n-form-item>
                  </n-gi>
                </n-grid>
              </n-form>
            </n-tab-pane>
          </n-tabs>
        </n-collapse-item>
      </n-collapse>

      <n-space align="center" wrap>
        <n-button
          id="startBtn"
          type="primary"
          :disabled="!isValid || !hasLabel"
          @click="clickStart()"
        >
          Start
        </n-button>
        <n-button id="statusBtn" :disabled="!connected" @click="$emit('status')">Status</n-button>
        <n-button id="cancelBtn" tertiary :disabled="!connected" @click="$emit('cancel')">Cancel</n-button>
        <n-button id="clearBtn" quaternary @click="$emit('clear')">Clear Log</n-button>

        <n-text depth="3">
          Run ID: <code>{{ currentRunId ?? '(none)' }}</code>
        </n-text>
      </n-space>


      <ServerFilePicker
        :open="pickerOpen"
        :start-path="pickerStartPath"
        title="Dataset Picker"
        @select="selectDataset"
        @close="closeDatasetPicker"
      />
    </n-space>
  </n-card>
</template>

<script setup>
import { ref, watch, watchEffect, computed, reactive } from 'vue'
import ServerFilePicker from './ServerFilePicker.vue'
import {
  NCard, NInput, NButton, NTag, NSpace,
  NCollapse, NCollapseItem,
  NGrid, NGi, NForm, NFormItem, NSelect, NInputNumber, NCheckbox,
  NAlert, NText, NTabs, NTabPane
} from 'naive-ui'

const props = defineProps({
  modelValue: { type: String, default: '' }, // parent holds JSON text
  connected: { type: Boolean, default: false },
  currentRunId: { type: [String, Number, null], default: null },
})
const emit = defineEmits(['update:modelValue', 'start', 'status', 'cancel', 'clear'])
const isSeries = ref(false)
const form = reactive({
  label: '',
  train_path: '',
  job_id: '',
  path: '',
  presets: 'medium_quality',
  time_limit: null,
  problem_type: '',
  eval_metric: '',
  hyperparametersText: '',
  tuningDataText: '',
  data_type: 'tabular',
  enable_gpu: false,
  dropColumnsText: '',

  // time series only
  prediction_length: null,
  id_column: '',
  time_column: '',
  freq: '',
})
const onDataTypeChange = (value) => {
  console.log('data_type changed to', value)

  if (value !== 'series') {
    form.prediction_length = null
    form.id_column = ''
    form.time_column = ''
    form.freq = ''
  }
  else if(value === 'series'){
    isSeries.value = true
  }
}
const presetOptions = [
  { label: 'medium_quality', value: 'medium_quality' },
  { label: 'high_quality', value: 'high_quality' },
  { label: 'best_quality', value: 'best_quality' },
  { label: 'extreme_quality', value: 'extreme_quality'}
]

const dataTypeOptions = [
  { label: "tabular", value: "tabular"},
  { label: "multi-modal", value: "mm"},
  { label: "series", value: "series"}
]

const problemTypeOptions = [
  { label: 'auto (omit)', value: '' },
  { label: 'binary', value: 'binary' },
  { label: 'multiclass', value: 'multiclass' },
  { label: 'regression', value: 'regression' },
]

const pickerOpen = ref(false)
const pickerStartPath = ref('~')
function openDatasetPicker() {
  pickerStartPath.value = form.train_path || '~'
  pickerOpen.value = true
}

function closeDatasetPicker() {
  pickerOpen.value = false
}

function selectDataset(path) {
  form.train_path = path
  closeDatasetPicker()
}

// Helpers
function safeParse (jsonText) {
  if (!jsonText || !jsonText.trim()) return { ok: true, value: undefined }
  try { return { ok: true, value: JSON.parse(jsonText) } }
  catch { return { ok: false, value: undefined } }
}

const hpValid = computed(() => safeParse(form.hyperparametersText).ok)
const tdValid = computed(() => safeParse(form.tuningDataText).ok)
const isValid = computed(() => hpValid.value && tdValid.value) // used by Start button
const hasLabel = computed(() => !!form.label)


// Build cfg object from form (omit empty/undefined keys)
function buildCfgFromForm () {
  const cfg = {}
  const f = form

  if (f.label) cfg.label = f.label
  if (f.train_path) cfg.train_path = f.train_path
  if (f.job_id && f.job_id.trim()) cfg.job_id = f.job_id.trim()
  if (f.path) cfg.path = f.path
  if (f.data_type) cfg.data_type = f.data_type
  if (f.presets ?? '' ) { // treat null as ''
    if (f.presets !== '') cfg.presets = f.presets
  }
  if (Number.isFinite(f.time_limit) && f.time_limit > 0) cfg.time_limit = f.time_limit
  if (f.problem_type) cfg.problem_type = f.problem_type
  if (f.eval_metric && f.eval_metric.trim()) cfg.eval_metric = f.eval_metric.trim()
  cfg.enable_gpu = !!f.enable_gpu
  if (!f.enable_gpu) cfg.num_gpus = 0
  if (f.dropColumnsText && f.dropColumnsText.trim()) {
    const cols = f.dropColumnsText
      .split(',')
      .map((col) => col.trim())
      .filter(Boolean)
    if (cols.length) cfg.drop_columns = cols
  }

  const hp = safeParse(f.hyperparametersText)
  if (hp.ok && hp.value !== undefined) cfg.hyperparameters = hp.value

  const td = safeParse(f.tuningDataText)
  if (td.ok && td.value !== undefined) cfg.tuning_data = td.value

  // Time series–specific options
  if (f.data_type === 'series') {
    if (Number.isFinite(f.prediction_length) && f.prediction_length > 0) {
      cfg.prediction_length = f.prediction_length
    }
    if (f.id_column) cfg.id_column = f.id_column
    if (f.time_column) cfg.time_column = f.time_column
    if (f.freq) cfg.freq = f.freq
  }

  return cfg
}

function clickStart(){
  const cfg = buildCfgFromForm()
  const result = {"action_type": "start", "cfg": cfg}
  emit('update:modelValue', JSON.stringify(result))
  emit('start')
}
</script>


<style scoped>
.path-picker-row {
  display: flex;
  gap: 8px;
}
</style>
