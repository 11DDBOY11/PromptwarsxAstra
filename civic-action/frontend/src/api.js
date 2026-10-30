const TOKEN_KEY = "civic_officer_token";

async function parse(res) {
  if (res.ok) return res.json();
  const body = await res.json().catch(() => ({}));
  const d = body.detail;
  const err = new Error(Array.isArray(d) ? d.map((x) => x.msg).join("; ") : d || res.statusText);
  err.status = res.status;
  throw err;
}

function getAuthHeaders(extra = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = { ...extra };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

const send = (url, method, body) =>
  fetch(url, {
    method,
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  }).then(parse);

export const api = {
  health: () => fetch("/api/health").then(parse),
  submit: (formData) => fetch("/api/reports", { method: "POST", body: formData }).then(parse),
  list: () => fetch("/api/reports", { headers: getAuthHeaders() }).then(parse),
  detail: (id) => fetch(`/api/reports/${id}`, { headers: getAuthHeaders() }).then(parse),
  setStatus: (id, body) => send(`/api/reports/${id}/status`, "PATCH", body),
  unlink: (id) =>
    fetch(`/api/reports/${id}/unlink`, { method: "POST", headers: getAuthHeaders() }).then(parse),
  track: (code) => fetch(`/api/track/${encodeURIComponent(code.trim())}`).then(parse),
  bySession: (sessionId) =>
    fetch(`/api/reports/by-session?session_id=${encodeURIComponent(sessionId)}`).then(parse),
  clusters: () => fetch("/api/clusters", { headers: getAuthHeaders() }).then(parse),
  stats: () => fetch("/api/stats", { headers: getAuthHeaders() }).then(parse),
  reset: () => fetch("/api/demo/reset", { method: "POST", headers: getAuthHeaders() }).then(parse),

  // Officer Authentication
  officerLogin: async (email, password) => {
    const res = await send("/api/auth/officer-login", "POST", { email, password });
    if (res.token) {
      localStorage.setItem(TOKEN_KEY, res.token);
    }
    return res;
  },
  officerMe: () =>
    fetch("/api/auth/officer-me", { headers: getAuthHeaders() }).then(parse),
  officerLogout: () => {
    localStorage.removeItem(TOKEN_KEY);
  },
  getOfficerToken: () => localStorage.getItem(TOKEN_KEY),
};
