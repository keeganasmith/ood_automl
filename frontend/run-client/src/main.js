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
export function getBaseURL(path = ""){
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
  console.log(`${proto}//${location.host}${join(base, path)}`)
  return `${proto}//${location.host}${join(base, path)}`;
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

// Assumes your existing getBaseURL() and join() are available in scope.

/** Convert ws(s) -> http(s) while keeping host/base path from getBaseURL */
export function getHttpBase(path = "") {
  const raw = getBaseURL("");
  const url = new URL(raw, window.location.href);
  if (url.protocol === "ws:")  url.protocol = "http:";
  if (url.protocol === "wss:") url.protocol = "https:";
  return join(url.origin + url.pathname, path);
}

/** Append query params to a URL */
export function withQuery(u, query) {
  if (!query) return u;
  const url = new URL(u, window.location.href);
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  }
  return url.toString();
}

/** Generic fetch wrapper (GET/POST/etc.) using the same base-URL logic */
export async function apiRequest(
  path,
  opts = {}
) {
  const {
    method = "GET",
    json,
    body,
    headers = {},
    query,
    timeoutMs = 15000,
    credentials = "same-origin",
  } = opts;

  const url = withQuery(getHttpBase(path), query);

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  const init = {
    method,
    credentials,
    signal: controller.signal,
    headers: { ...headers },
  };

  if (json !== undefined) {
    init.headers = { "Content-Type": "application/json", ...init.headers };
    init.body = JSON.stringify(json);
  } else if (body !== undefined) {
    init.body = body; // FormData/Blob/ArrayBuffer/etc.
  }

  try {
    const res = await fetch(url, init);
    if (!res.ok) {
      let text = "";
      try { text = await res.text(); } catch {}
      throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` – ${text}` : ""}`);
    }
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  } finally {
    clearTimeout(t);
  }
}

/** Convenience helpers */
export function getJSON(path, opts = {}) {
  return apiRequest(path, { ...opts, method: "GET" });
}

export function postJSON(path, data, opts = {}) {
  return apiRequest(path, { ...opts, method: "POST", json: data });
}

export function postForm(path, formData, opts = {}) {
  return apiRequest(path, { ...opts, method: "POST", body: formData });
}
