<template>
    <div style="padding:12px">
      <h1>Logs for {{ id }}</h1>
      <div style="margin:8px 0">
        <button @click="connect" :disabled="connected">Connect</button>
        <button @click="disconnect" :disabled="!connected">Disconnect</button>
        <span style="margin-left:8px">{{ connected ? 'connected' : 'disconnected' }}</span>
      </div>
      <pre ref="logEl" style="height:60vh; overflow:auto; background:#111; color:#ddd; padding:12px; border-radius:6px">{{ log.join('') }}</pre>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
  import { useRoute } from 'vue-router'
  import { getBaseURL } from '../main' // if your helper lives in main.js
  
  const route = useRoute()
  const id = route.params.id
  
  const ws = ref(null)
  const connected = ref(false)
  const log = ref([])
  const logEl = ref(null)
  
  function getLogWsURL(jobId) {
    const httpProto = window.location.protocol
    const host = window.location.host
    const base = getBaseURL() // e.g. https://host/node/.../
    const prefix = base.replace(`${httpProto}//${host}`, '') // /node/.../
    const wsProto = httpProto === 'https:' ? 'wss' : 'ws'
    return `${wsProto}://${host}${prefix}ws?job_id=${encodeURIComponent(jobId)}`
  }
  
  function append(text) {
    log.value.push(text.endsWith('\n') ? text : text + '\n')
    nextTick(() => {
      if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
    })
  }
  
  function connect() {
    if (ws.value) return
    const url = getLogWsURL(id)
    try {
      ws.value = new WebSocket(url)
    } catch (e) {
      append(`[error] cannot open websocket: ${e}`)
      return
    }
    ws.value.onopen = () => { connected.value = true; append('[ok] connected') }
    ws.value.onclose = (ev) => { connected.value = false; append(`[close] code=${ev.code}`); ws.value = null }
    ws.value.onerror = (ev) => { append('[error] see console'); console.error(ev) }
    ws.value.onmessage = (ev) => { append(ev.data) } // server sends plain text lines
  }
  
  function disconnect() {
    if (ws.value) { try { ws.value.close() } catch {} }
  }
  
  onMounted(connect)
  onBeforeUnmount(disconnect)
  </script>
  