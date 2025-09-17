import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { router } from './router'

createApp(App).use(router).mount('#app')
  
function inferBasePath(pathname) {
// Detect OOD prefix like /node/<host>/<port>/
    const m = pathname.match(/^\/node\/[^/]+\/\d+\/?/);
    return m ? (m[0].endsWith("/") ? m[0] : m[0] + "/") : "/";
}
  
function join(a, b) {
    if (!a.endsWith("/")) a += "/";
    return a + (b.startsWith("/") ? b.slice(1) : b);
}
export function getBaseURL(){
  const u = new URL(window.location.href);
  const qp = u.searchParams.get("ws");
  if (qp) return qp;

  // 2) Runtime config (set by loadRuntimeConfig or inline script)
  if (window.__APP_CONFIG__ && window.__APP_CONFIG__.WS_URL) {
    return window.__APP_CONFIG__.WS_URL;
  }

  // 3) Build-time env (Vite). Safe in JS too.
  if (import.meta && import.meta.env && import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  // 4) Auto-infer (OOD-safe)
  const proto = location.protocol
  const base = inferBasePath(location.pathname);   // e.g. "/node/lc05/42801/"
  return `${proto}://${location.host}${base}`;
}

export function getWsURL(path = "create_run") {
    // 1) Query param override (?ws=wss://host/path)
    const u = new URL(window.location.href);
    const qp = u.searchParams.get("ws");
    if (qp) return qp;
  
    // 2) Runtime config (set by loadRuntimeConfig or inline script)
    if (window.__APP_CONFIG__ && window.__APP_CONFIG__.WS_URL) {
      return window.__APP_CONFIG__.WS_URL;
    }
  
    // 3) Build-time env (Vite). Safe in JS too.
    if (import.meta && import.meta.env && import.meta.env.VITE_WS_URL) {
      return import.meta.env.VITE_WS_URL;
    }
  
    // 4) Auto-infer (OOD-safe)
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const base = inferBasePath(location.pathname);   // e.g. "/node/lc05/42801/"
    return `${proto}://${location.host}${join(base, path)}`;
}