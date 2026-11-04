export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const error = new Error(errorMessage(data, res.status));
    error.status = res.status;
    throw error;
  }
  return data;
}

// FastAPI devuelve `detail` como texto o, en errores de validación (422), como lista.
function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => String(item.msg || "").replace(/^Value error, /, "")).join(" · ");
  }
  return `Error ${status}`;
}

export function requireAuthOrRedirect() {
  if (!getToken()) {
    window.location.href = "/index.html";
    return false;
  }
  return true;
}
