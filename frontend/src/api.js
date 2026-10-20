// Empty = same server as the UI. On Render the UI is a separate static site, so
// VITE_API_URL is set to the backend URL at build time.
const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

// The free server sleeps after 15 minutes idle. If a normally quick request takes
// a while, tell the app so it can show a "waking up" note.
const SLOW_MS = 5000;
function emitSlow(slow) {
  window.dispatchEvent(new CustomEvent("api-slow", { detail: slow }));
}

async function request(path, options = {}, { slowHint = true } = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const timer = slowHint ? setTimeout(() => emitSlow(true), SLOW_MS) : null;
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Can't reach the server. Check your internet, or try again in a minute.");
  } finally {
    if (timer) {
      clearTimeout(timer);
      emitSlow(false);
    }
  }
  const data = await res.json().catch(() => ({}));
  // Login expired or invalid: clear it and go back to the login page.
  if (res.status === 401 && token && !path.startsWith("/api/auth/")) {
    localStorage.removeItem("token");
    window.location.assign("/login");
    throw new Error("Your session expired. Please log in again.");
  }
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ---- auth ----
export function loginUser(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
}
export const registerUser = (email, password) =>
  request("/api/auth/register", json("POST", { email, password }));

// ---- user + index ----
export const getMe = () => request("/api/me");
export const getStatus = () => request("/api/status");
export const ingestRepo = (source) =>
  request("/api/ingest", json("POST", { source }), { slowHint: false });
export const listRepos = () => request("/api/repos");
export const forgetRepo = (source) => request("/api/repos/forget", json("POST", { source }));

// ---- chats ----
export const listChats = () => request("/api/chats");
export const getChat = (id) => request(`/api/chats/${id}`);
export const renameChat = (id, title) => request(`/api/chats/${id}`, json("PATCH", { title }));
export const deleteChat = (id) => request(`/api/chats/${id}`, { method: "DELETE" });
export const askQuestion = (question, agentic, conversationId) =>
  request(
    "/api/ask",
    json("POST", { question, agentic, conversation_id: conversationId || null }),
    { slowHint: false },
  );
