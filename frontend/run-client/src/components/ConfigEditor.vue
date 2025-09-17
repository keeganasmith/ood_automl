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
                    <n-form-item label="label" :rule="{ required: true, message: 'Required' }">
                      <n-input v-model:value="form.label" placeholder="e.g., Survived" />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="train_path" :rule="{ required: true, message: 'Required' }">
                      <n-input v-model:value="form.train_path" placeholder="./sample_datasets/train.csv" />
                    </n-form-item>
                  </n-gi>

                  <n-gi>
                    <n-form-item label="data_type">
                      <n-select
                        v-model:value="form.data_type"
                        :options="dataTypeOptions"
                        placeholder="tabular"
                        clearable
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
                        placeholder="(omit)"
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
                    <n-form-item label="problem_type">
                      <n-select
                        v-model:value="form.problem_type"
                        :options="problemTypeOptions"
                        placeholder="auto (omit)"
                        clearable
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
    </n-space>
  </n-card>
</template>

<script setup>
import { ref, watch, watchEffect, computed } from 'vue'
import {
  NCard, NInput, NButton, NTag, NSpace,
  NCollapse, NCollapseItem,
  NGrid, NGi, NForm, NFormItem, NSelect, NInputNumber,
  NAlert, NText, NTabs, NTabPane
} from 'naive-ui'

const props = defineProps({
  modelValue: { type: String, default: '' }, // parent holds JSON text
  connected: { type: Boolean, default: false },
  currentRunId: { type: [String, Number, null], default: null },
})
const emit = defineEmits(['update:modelValue', 'start', 'status', 'cancel', 'clear'])

const form = ref({
  label: '',
  train_path: '',
  path: '',
  presets: 'medium_quality',
  time_limit: null,
  problem_type: '',
  hyperparametersText: '',
  tuningDataText: '',
  data_type: '',
})

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

// Helpers
function safeParse (jsonText) {
  if (!jsonText || !jsonText.trim()) return { ok: true, value: undefined }
  try { return { ok: true, value: JSON.parse(jsonText) } }
  catch { return { ok: false, value: undefined } }
}

const hpValid = computed(() => safeParse(form.value.hyperparametersText).ok)
const tdValid = computed(() => safeParse(form.value.tuningDataText).ok)
const isValid = computed(() => hpValid.value && tdValid.value) // used by Start button
const hasLabel = computed(() => !!form.value.label)

// Build cfg object from form (omit empty/undefined keys)
function buildCfgFromForm () {
  const cfg = {}
  const f = form.value

  if (f.label) cfg.label = f.label
  if (f.train_path) cfg.train_path = f.train_path
  if (f.path) cfg.path = f.path
  if (f.data_type) cfg.data_type = f.data_type
  if (f.presets ?? '' ) { // treat null as ''
    if (f.presets !== '') cfg.presets = f.presets
  }
  if (Number.isFinite(f.time_limit) && f.time_limit > 0) cfg.time_limit = f.time_limit
  if (f.problem_type) cfg.problem_type = f.problem_type

  const hp = safeParse(f.hyperparametersText)
  if (hp.ok && hp.value !== undefined) cfg.hyperparameters = hp.value

  const td = safeParse(f.tuningDataText)
  if (td.ok && td.value !== undefined) cfg.tuning_data = td.value

  return cfg
}

function clickStart(){
  const cfg = buildCfgFromForm()
  const result = {"action_type": "start", "cfg": cfg}
  emit('update:modelValue', JSON.stringify(result))
  emit('start')
}
</script>