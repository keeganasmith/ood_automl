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
  
export function getBaseURL(subpath = "") {
  // 1) Query param override (?base=https://host/custom/base/)
  const u = new URL(window.location.href);
  let base = u.searchParams.get("base");

  // 2) Runtime config
  if (!base && window.__APP_CONFIG__?.BASE_URL) {
    base = window.__APP_CONFIG__.BASE_URL;
  }

  // 3) Build-time env (Vite)
  if (!base && import.meta?.env?.VITE_BASE_URL) {
    base = import.meta.env.VITE_BASE_URL;
  }

  // 4) Auto-infer (OOD-safe)
  if (!base) {
    const proto = window.location.protocol;              // "http:" | "https:"
    const host = window.location.host;                   // "host:port"
    const prefix = inferBasePath(window.location.pathname);
    base = `${proto}//${host}${prefix}`;
  }

  // Normalize trailing slash
  if (!base.endsWith("/")) base += "/";

  // Optional subpath join
  return subpath ? join(base, subpath) : base;
}

// If you like, keep your existing WS helper but base it on getBaseURL:
export function getWsURL(path = "create_run") {
  const u = new URL(window.location.href);
  const qp = u.searchParams.get("ws");
  if (qp) return qp;

  if (window.__APP_CONFIG__?.WS_URL) return window.__APP_CONFIG__.WS_URL;
  if (import.meta?.env?.VITE_WS_URL) return import.meta.env.VITE_WS_URL;

  const wsProto = window.location.protocol === "https:" ? "wss" : "ws";
  const base = getBaseURL(); // already includes prefix + trailing slash
  const httpProto = window.location.protocol; // keep host consistent
  const host = window.location.host;
  // Replace http(s) with ws(s) and reuse prefix
  const prefix = base.replace(`${httpProto}//${host}`, ""); // e.g. "/node/..../"
  return `${wsProto}://${host}${join(prefix, path)}`;
}