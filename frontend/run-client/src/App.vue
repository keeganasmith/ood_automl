<template>
  <div>
    <h1>Run Controller Client</h1>

    <!-- <fieldset>
      <legend>Connection</legend>
      <label>WebSocket URL</label>
      <input id="wsUrl" type="text" v-model="wsUrl" />
      <div class="row" style="margin-top:.5rem;">
        <button id="connectBtn" @click="connect" :disabled="connected">Connect</button>
        <button id="disconnectBtn" @click="disconnect" :disabled="!connected">Disconnect</button>
        <span id="status" class="muted">{{ connected ? 'connected' : 'disconnected' }}</span>
      </div>
    </fieldset> -->

    <!-- NEW: Config editor component -->
    <ConfigEditor
      v-model="cfgText"
      :connected="connected"
      :current-run-id="currentRunId"
      @start="sendStart"
      @status="sendStatus"
      @cancel="sendCancel"
      @clear="clearLog"
    />

    <fieldset>
      <legend>Events</legend>
      <div id="log" ref="logEl">
        <div v-for="(line, i) in log" :key="i" :class="line.cls">[{{ line.ts }}] {{ line.text }}</div>
      </div>
    </fieldset>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { getWsURL } from './main'
import ConfigEditor from './components/ConfigEditor.vue'

const ws = ref(null)
const connected = ref(false)
const wsUrl = ref('')
const cfgText = ref('')
const currentRunId = ref(null)
const log = ref([])
const logEl = ref(null)



onMounted(() => {
  wsUrl.value = getWsURL()
  cfgText.value = JSON.stringify({
    action_type: 'start',
    cfg: {
      label: 'Survived',
      train_path: './sample_datasets/train.csv',
      presets: 'medium_quality_faster_train',
    },
  }, null, 2)
})

function setConnected(yes) {
  connected.value = yes
}

function appendLine(text, cls = '') {
  const ts = new Date().toLocaleTimeString()
  log.value.push({ ts, text, cls })
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  })
}

function appendEvent(obj) {
  if (obj.type === 'event') {
    const subtype = obj.subtype || obj.type
    if (subtype === 'log') {
      console.log(obj.msg)
      appendLine(`[log] ${(obj.logger || '')} ${(obj.level || '')} — ${(obj.msg || '')}`)
    } else if (subtype === 'milestone') {
      appendLine(`[milestone] ${obj.stage || ''}`, 'ok')
    } else if (subtype === 'finished') {
      appendLine(`[finished] artifacts at ${obj.result_path || '(unknown path)'}`, 'ok')
    } else if (subtype === 'error') {
      appendLine(`[error] ${obj.error || '(no detail)'}`, 'err')
    } else {
      appendLine(`[${subtype}] ${JSON.stringify(obj)}`)
    }
    if (obj.run_id) currentRunId.value = obj.run_id
    return
  }

  if (obj.type === 'error') {
    appendLine(`[protocol error] ${obj.detail || JSON.stringify(obj)}`, 'err')
    return
  }

  if (obj.status) {
    appendLine(
      (obj.status === 'success' ? '[ok] ' : '[fail] ') + JSON.stringify(obj),
      obj.status === 'success' ? 'ok' : 'err'
    )
    if (obj.run_id) currentRunId.value = obj.run_id
    return
  }

  appendLine(`[other] ${JSON.stringify(obj)}`)
}


function connect() {
  try {
    ws.value = new WebSocket(wsUrl.value)
  } catch (e) {
    appendLine(`Failed to open WebSocket: ${e}`, 'err')
    return
  }
  ws.value.onopen = () => {
    setConnected(true)
    appendLine('WebSocket connected', 'ok')
  }
  ws.value.onclose = (ev) => {
    setConnected(false)
    appendLine(`WebSocket closed (code=${ev.code})`)
    ws.value = null
  }
  ws.value.onerror = (ev) => {
    appendLine('WebSocket error (see console)', 'err')
    console.error(ev)
  }
  ws.value.onmessage = (ev) => {
    try {
      const obj = JSON.parse(ev.data)
      appendEvent(obj)
    } catch (e) {
      appendLine(`bad JSON from server: ${e}`, 'err')
    }
  }
}

function disconnect() {
  if (ws.value) ws.value.close()
}

function clearLog() {
  log.value = []
}
function waitForClose(sock, timeout = 5000) {
  if(!ws.value) return Promise.resolve();
  if (sock.readyState === WebSocket.CLOSED) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const tid = setTimeout(() => {
      cleanup();
      reject(new Error('WebSocket open timeout'));
    }, timeout);

    function cleanup() {
      clearTimeout(tid);
      sock.removeEventListener('open', onOpen);
      sock.removeEventListener('error', onError);
      sock.removeEventListener('close', onClose);
    }
    function onOpen() { cleanup(); reject(); }
    function onError(e) { cleanup(); reject(e); }
    function onClose() { cleanup(); resolve(); }

    sock.addEventListener('open', onOpen, { once: true });
    sock.addEventListener('error', onError, { once: true });
    sock.addEventListener('close', onClose, { once: true });
  });
}
function waitForOpen(sock, timeout = 5000) {
  if (sock.readyState === WebSocket.OPEN) return Promise.resolve();
  if (sock.readyState === WebSocket.CLOSED) return Promise.reject(new Error('Socket is closed'));

  return new Promise((resolve, reject) => {
    const tid = setTimeout(() => {
      cleanup();
      reject(new Error('WebSocket open timeout'));
    }, timeout);

    function cleanup() {
      clearTimeout(tid);
      sock.removeEventListener('open', onOpen);
      sock.removeEventListener('error', onError);
      sock.removeEventListener('close', onClose);
    }
    function onOpen() { cleanup(); resolve(); }
    function onError(e) { cleanup(); reject(e); }
    function onClose() { cleanup(); reject(new Error('Closed before open')); }

    sock.addEventListener('open', onOpen, { once: true });
    sock.addEventListener('error', onError, { once: true });
    sock.addEventListener('close', onClose, { once: true });
  });
}

async function sendStart() {
  disconnect();
  await waitForClose(ws.value, 5000);
  connect();
  try { await waitForOpen(ws.value, 5000); }
  catch (e) { appendLine(`Cannot send: ${e.message}`, 'err'); return; }
  console.log("ws ready state: ", ws.value.readyState)
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
  let payload
  try {
    payload = JSON.parse(cfgText.value)
    console.log(payload)
  } catch (e) {
    appendLine(`Config JSON error: ${e}`, 'err')
    return
  }
  if (!payload || payload.action_type !== 'start') {
    appendLine(`Config must be an object like {"action_type":"start","cfg":{...}}`, 'err')
    return
  }
  ws.value.send(JSON.stringify(payload))
  appendLine('→ sent start')
}

function sendStatus() {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
  const msg = currentRunId.value
    ? { action_type: 'status', run_id: currentRunId.value }
    : { action_type: 'status' }
  ws.value.send(JSON.stringify(msg))
  appendLine('→ sent status')
}

function sendCancel() {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
  const msg = currentRunId.value
    ? { action_type: 'cancel', run_id: currentRunId.value }
    : { action_type: 'cancel' }
  ws.value.send(JSON.stringify(msg))
  appendLine('→ sent cancel')
}
</script>
