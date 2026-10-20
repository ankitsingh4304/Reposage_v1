// Empty = same server as the UI. On Render the UI is a separate static site, so
// VITE_API_URL is set to the backend URL at build time.
const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

async function request(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
  
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  // Login expired or invalid: clear it and go back to the login page.
  if (res.status === 401 && token && !path.startsWith("/api/auth/")) {
    localStorage.removeItem("token");
    window.location.assign("/login");
    throw new Error("Your session expired. Please log in again.");
  }
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export function getStatus() {
  return request("/api/status");
}

export function ingestRepo(source) {
  return request("/api/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
}

export function askQuestion(question, agentic) {
  return request("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, agentic }),
  });
}

export function loginUser(username, password) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString()
  });
}

export function registerUser(email, password) {
  return request("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
}
